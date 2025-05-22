import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.cache import is_valid_country_id
from app.accounts.models import AvailableCountry
from app.transactions.models import Wallet, WalletType
from app.verify.models import OTP

User = get_user_model()

logger = logging.getLogger(__name__)


class GenerateOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        required=False, help_text="Phone number to send the OTP to"
    )
    email = serializers.EmailField(
        required=False, help_text="Email address to send the OTP to"
    )
    country_id = serializers.IntegerField(
        required=False,
        help_text="ID of the country (required when phone_number is provided)",
    )
    country_dial_code = serializers.CharField(
        required=False,
        help_text="Dial code of the country (required when phone_number is provided)",
    )
    channel = serializers.ChoiceField(
        choices=OTP.CHANNEL_CHOICES,
        default="sms",
        help_text="Channel to send the OTP through (sms, email, whatsapp)",
    )

    def validate(self, attrs):
        if not attrs.get("phone_number") and not attrs.get("email"):
            raise serializers.ValidationError(
                _("Either phone_number or email must be provided.")
            )

        if attrs.get("phone_number") and (
            not attrs.get("country_id") or not attrs.get("country_dial_code")
        ):
            raise serializers.ValidationError(
                _(
                    "country_id and country_dial_code are required when phone_number is provided."
                )
            )

        if (
            attrs.get("phone_number")
            and attrs.get("country_id")
            and attrs.get("country_dial_code")
        ):
            if not is_valid_country_id(attrs.get("country_id")):
                raise serializers.ValidationError(
                    _("Invalid country_id. Country does not exist.")
                )
            from phonenumber_field.phonenumber import PhoneNumber

            wrapped_phone_number = PhoneNumber.from_string(
                f"+{attrs['country_dial_code']}{attrs['phone_number']}"
            )
            if not wrapped_phone_number.is_valid():
                raise serializers.ValidationError(_("Invalid phone number."))
            attrs["identifier"] = wrapped_phone_number.as_e164

        if attrs.get("email"):  # prioritize email
            attrs["identifier"] = attrs["email"]

            if attrs.get("channel") == "sms" and not attrs.get("phone_number"):
                attrs["channel"] = "email"

        return attrs

    def generate_otp(self):
        identifier = self.validated_data["identifier"]
        channel = self.validated_data["channel"]

        return OTP.generate(identifier, channel)


class NotFoundException(APIException):
    status_code = 404
    default_detail = "Resource not found."
    default_code = "NOT_FOUND"


class TooManyRequestsException(APIException):
    status_code = 429
    default_detail = "Too many requests."
    default_code = "TOO_MANY_REQUESTS"


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        required=False, help_text="Phone number the OTP was sent to"
    )
    email = serializers.EmailField(
        required=False, help_text="Email address the OTP was sent to"
    )
    country_id = serializers.IntegerField(
        required=True,
        help_text="ID of the country (required for all authentication methods)",
    )
    country_dial_code = serializers.CharField(
        required=True, help_text="Dial code of the country"
    )
    code = serializers.CharField(required=True, help_text="OTP code to verify")
    is_business = serializers.BooleanField(
        required=False, help_text="Whether the account is a business account"
    )

    def validate(self, attrs):
        if not attrs["code"].isdigit():
            raise serializers.ValidationError(
                code="INVALID_CODE",
                detail=_("Code must contain only digits."),
            )

        if not attrs.get("phone_number") and not attrs.get("email"):
            raise serializers.ValidationError(
                code="IDENTIFIER_REQUIRED",
                detail=_("Either phone_number or email must be provided."),
            )

        if not attrs.get("country_id"):
            raise serializers.ValidationError(
                code="COUNTRY_REQUIRED",
                detail=_("Country is required."),
            )

        if not isinstance(attrs.get("country_id"), int) or not is_valid_country_id(
            attrs.get("country_id")
        ):
            raise serializers.ValidationError(
                code="INVALID_COUNTRY",
                detail=_("Invalid country."),
            )

        if not attrs.get("country_dial_code"):
            raise serializers.ValidationError(
                code="COUNTRY_DIAL_CODE_REQUIRED",
                detail=_("country_dial_code is required."),
            )

        if attrs.get("phone_number"):
            attrs["identifier"] = (
                f"+{attrs['country_dial_code']}{attrs['phone_number']}"
            )
        else:
            attrs["identifier"] = attrs["email"]

        return attrs

    def verify_otp(self):
        identifier = self.validated_data["identifier"]
        code = self.validated_data["code"]
        country_id = self.validated_data.get("country_id")
        is_business = self.validated_data.get("is_business", None)

        otp = OTP.objects.get_active_otp(identifier)

        if not otp:
            raise NotFoundException(
                code="NO_ACTIVE_OTP",
                detail=_("No active OTP found. Please request a new code."),
            )

        if otp.verify(code):
            user, created = User.objects.get_or_create(phone_number=identifier)
            user.country_id = country_id
            if is_business is not None:
                user.is_business = is_business
            user.save()

            try:
                wallet, created_wallet = Wallet.objects.get_or_create(
                    user=user,
                    wallet_type=WalletType.MAIN,
                    defaults={
                        "balance": 0,
                        "is_active": True,
                    },
                )
                if created_wallet:
                    logger.info(f"Created main wallet for user {user.id}")

                refresh = RefreshToken.for_user(user)

                return {
                    "created": created,
                    "user": {
                        "full_name": user.full_name,
                        "email": user.email,
                        "phone_number": user.phone_number,
                        "country": user.country.name,
                        "profile_picture": (
                            user.profile_picture.url if user.profile_picture else None
                        ),
                        "is_business": user.is_business,
                    },
                    "wallet": {
                        "id": wallet.id,
                        "balance": str(wallet.balance),
                        "wallet_type": wallet.wallet_type,
                        "currency": wallet.currency,
                        "is_active": wallet.is_active,
                    },
                    "tokens": {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                    },
                }
            except Exception as e:
                logger.error(f"Failed to create wallet for user {user.id}: {str(e)}")
                raise serializers.ValidationError(
                    code="WALLET_CREATION_FAILED",
                    detail=_("Failed to create wallet for user."),
                )

        else:
            from django.conf import settings

            max_attempts = getattr(settings, "OTP_MAX_ATTEMPTS", 3)
            remaining_attempts = max_attempts - otp.attempt_count

            if remaining_attempts <= 0:
                raise TooManyRequestsException(
                    code="MAX_ATTEMPTS_REACHED",
                    detail=_(
                        "Maximum verification attempts reached. Please request a new code."
                    ),
                )
            else:
                raise serializers.ValidationError(
                    code="INVALID_CODE",
                    detail=_(
                        "Invalid code. {remaining_attempts} attempts remaining."
                    ).format(remaining_attempts=remaining_attempts),
                )


class AccountRecoverySerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        required=True, help_text="Phone number to recover the account"
    )
    country_dial_code = serializers.CharField(
        required=True, help_text="Dial code of the country"
    )

    def validate(self, attrs):
        try:
            identifier = f"+{attrs['country_dial_code']}{attrs['phone_number']}"
            user = User.objects.get(phone_number=identifier)

            if not user.email:
                raise NotFoundException(
                    code="NO_EMAIL_ASSOCIATED",
                    detail=_(
                        "No email address associated with this account. Please contact support."
                    ),
                )

            attrs["user_email"] = user.email
            return attrs

        except User.DoesNotExist:
            raise NotFoundException(
                code="NO_ACCOUNT_FOUND",
                detail=_("No account found with this phone number."),
            )

    def recover_account(self):
        result = OTP.generate(self.validated_data["user_email"], channel="email")

        email_parts = self.validated_data["user_email"].split("@")
        username = email_parts[0]
        domain = email_parts[1]

        masked_username = username[:2] + "*" * (len(username) - 2)
        masked_email = f"{masked_username}@{domain}"

        return {
            "masked_email": masked_email,
            "expires_at": result["expires_at"],
        }
