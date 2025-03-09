import datetime
import logging
import random
import string
from typing import Dict, Optional, Union

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import Account
from app.core.utils.fields import AppCharField
from app.core.utils.models import AppModel
from app.verify.delivery_channels import DELIVERY_CHANNELS

logger = logging.getLogger(__name__)

User = get_user_model()


class OTPManager(models.Manager):
    def get_active_otp(self, identifier: str) -> Optional["OTP"]:
        return (
            self.filter(
                identifier=identifier,
                is_used=False,
                is_expired=False,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_on")
            .first()
        )

    def get_latest_otp(self, identifier: str) -> Optional["OTP"]:
        return self.filter(identifier=identifier).order_by("-created_on").first()

    def create_otp(
        self, identifier: str, channel: str = "sms", length: int = 6
    ) -> "OTP":
        latest_otp = self.get_latest_otp(identifier)

        if (
            latest_otp
            and latest_otp.next_otp_allowed_at
            and latest_otp.next_otp_allowed_at > timezone.now()
        ):
            waiting_seconds = (
                latest_otp.next_otp_allowed_at - timezone.now()
            ).total_seconds()
            raise OTPWaitingPeriodError(
                f"Please wait {int(waiting_seconds)} seconds before requesting a new OTP.",
                waiting_seconds=waiting_seconds,
                next_allowed_at=latest_otp.next_otp_allowed_at,
            )

        self.filter(identifier=identifier, is_used=False, is_expired=False).update(
            is_expired=True
        )

        code = "".join(random.choices(string.digits, k=length))

        expires_at = timezone.now() + datetime.timedelta(
            minutes=getattr(settings, "OTP_EXPIRY_MINUTES", 10)
        )

        next_otp_allowed_at = None
        if latest_otp:
            request_count = self.filter(
                identifier=identifier,
                created_on__gte=timezone.now() - datetime.timedelta(hours=24),
            ).count()

            waiting_periods = getattr(
                settings, "OTP_WAITING_PERIODS", [0, 5, 30, 300, 1800, 3600]
            )

            if request_count < len(waiting_periods):
                wait_seconds = waiting_periods[request_count]
            else:
                wait_seconds = waiting_periods[-1]

            if wait_seconds > 0:
                next_otp_allowed_at = timezone.now() + datetime.timedelta(
                    seconds=wait_seconds
                )

        return self.create(
            identifier=identifier,
            code=code,
            channel=channel,
            expires_at=expires_at,
            next_otp_allowed_at=next_otp_allowed_at,
        )


class OTPWaitingPeriodError(Exception):
    def __init__(self, message, waiting_seconds=0, next_allowed_at=None):
        self.message = message
        self.waiting_seconds = waiting_seconds
        self.next_allowed_at = next_allowed_at
        super().__init__(self.message)


class OTP(AppModel):
    CHANNEL_CHOICES = (
        ("sms", "SMS"),
        ("email", "Email"),
        ("whatsapp", "WhatsApp"),
    )

    identifier = AppCharField(
        max_length=100,
        db_index=True,
        help_text="Phone number or email to identify the user",
    )
    code = AppCharField(max_length=10)
    channel = AppCharField(max_length=20, choices=CHANNEL_CHOICES, default="sms")
    is_used = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    next_otp_allowed_at = models.DateTimeField(
        null=True, blank=True, help_text="When the next OTP can be generated"
    )

    objects = OTPManager()

    class Meta:
        verbose_name = "OTP"
        verbose_name_plural = "OTPs"
        indexes = [
            models.Index(fields=["identifier"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"OTP for {self.identifier} ({self.channel})"

    @property
    def is_valid(self) -> bool:
        return (
            not self.is_used
            and not self.is_expired
            and timezone.now() < self.expires_at
        )

    def verify(self, code: str) -> bool:
        self.attempt_count += 1

        max_attempts = getattr(settings, "OTP_MAX_ATTEMPTS", 3)
        if self.attempt_count > max_attempts:
            self.is_expired = True
            self.save()
            return False

        if not self.is_valid:
            self.save()
            return False

        if self.code != code:
            self.save()
            return False

        self.is_used = True
        self.used_at = timezone.now()
        self.save()

        return True

    def mark_as_expired(self):
        self.is_expired = True
        self.save()

    @classmethod
    def generate(
        cls, identifier: str, channel: str = "sms", length: int = 6
    ) -> Dict[str, Union[bool, str, "OTP", timezone.datetime]]:
        try:
            if channel not in DELIVERY_CHANNELS:
                logger.error(f"Unsupported OTP delivery channel: {channel}")
                return {
                    "success": False,
                    "message": f"Unsupported delivery channel: {channel}",
                }

            try:
                otp = cls.objects.create_otp(identifier, channel, length)

                delivery_channel = DELIVERY_CHANNELS[channel]
                if delivery_channel.send(identifier, otp.code):
                    logger.info(f"OTP sent to {identifier} via {channel}")
                    return {
                        "success": True,
                        "message": f"Verification code sent to {identifier} via {channel}.",
                        "otp": otp,
                        "expires_at": otp.expires_at,
                    }
                else:
                    otp.mark_as_expired()
                    logger.error(f"Failed to send OTP to {identifier} via {channel}")
                    return {
                        "success": False,
                        "message": f"Failed to send verification code to {identifier}.",
                    }
            except OTPWaitingPeriodError as e:
                logger.info(
                    f"OTP waiting period not over for {identifier}: {e.message}"
                )
                return {
                    "success": False,
                    "message": e.message,
                    "waiting_seconds": e.waiting_seconds,
                    "next_allowed_at": e.next_allowed_at,
                }
        except Exception as e:
            logger.error(f"Error generating OTP for {identifier}: {str(e)}")
            return {
                "success": False,
                "message": f"An error occurred while generating the verification code: {str(e)}",
            }
