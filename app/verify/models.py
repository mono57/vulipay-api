import datetime
import random
import string
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone

from app.core.utils.fields import AppCharField
from app.core.utils.models import AppModel

# Create your models here.


class OTPManager(models.Manager):
    def get_active_otp(self, identifier: str) -> Optional["OTP"]:
        """
        Get the most recent active OTP for a given identifier.
        """
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
        """
        Get the most recent OTP for a given identifier, regardless of status.
        """
        return self.filter(identifier=identifier).order_by("-created_on").first()

    def create_otp(
        self, identifier: str, channel: str = "sms", length: int = 6
    ) -> "OTP":
        """
        Create a new OTP for the given identifier.
        """
        # Check if we need to enforce a waiting period
        latest_otp = self.get_latest_otp(identifier)

        if (
            latest_otp
            and latest_otp.next_otp_allowed_at
            and latest_otp.next_otp_allowed_at > timezone.now()
        ):
            # Return None or raise an exception if waiting period is not over
            waiting_seconds = (
                latest_otp.next_otp_allowed_at - timezone.now()
            ).total_seconds()
            raise OTPWaitingPeriodError(
                f"Please wait {int(waiting_seconds)} seconds before requesting a new OTP.",
                waiting_seconds=waiting_seconds,
                next_allowed_at=latest_otp.next_otp_allowed_at,
            )

        # Expire any existing active OTPs for this identifier
        self.filter(identifier=identifier, is_used=False, is_expired=False).update(
            is_expired=True
        )

        # Generate a new OTP code
        code = "".join(random.choices(string.digits, k=length))

        # Calculate expiration time (default: 10 minutes)
        expires_at = timezone.now() + datetime.timedelta(
            minutes=getattr(settings, "OTP_EXPIRY_MINUTES", 10)
        )

        # Calculate next allowed OTP time based on request count
        next_otp_allowed_at = None
        if latest_otp:
            # Get the request count for this identifier in the last 24 hours
            request_count = self.filter(
                identifier=identifier,
                created_on__gte=timezone.now() - datetime.timedelta(hours=24),
            ).count()

            # Progressive waiting periods
            waiting_periods = getattr(
                settings, "OTP_WAITING_PERIODS", [0, 5, 30, 300, 1800, 3600]
            )

            if request_count < len(waiting_periods):
                wait_seconds = waiting_periods[request_count]
            else:
                # Use the last (maximum) waiting period for any additional requests
                wait_seconds = waiting_periods[-1]

            if wait_seconds > 0:
                next_otp_allowed_at = timezone.now() + datetime.timedelta(
                    seconds=wait_seconds
                )

        # Create and return the new OTP
        return self.create(
            identifier=identifier,
            code=code,
            channel=channel,
            expires_at=expires_at,
            next_otp_allowed_at=next_otp_allowed_at,
        )


class OTPWaitingPeriodError(Exception):
    """Exception raised when a new OTP is requested before the waiting period is over."""

    def __init__(self, message, waiting_seconds=0, next_allowed_at=None):
        self.message = message
        self.waiting_seconds = waiting_seconds
        self.next_allowed_at = next_allowed_at
        super().__init__(self.message)


class OTP(AppModel):
    """
    Model to store one-time passwords for user verification.
    """

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
        """Check if the OTP is still valid."""
        return (
            not self.is_used
            and not self.is_expired
            and timezone.now() < self.expires_at
        )

    def verify(self, code: str) -> bool:
        """
        Verify the provided code against this OTP.

        Returns:
            bool: True if verification is successful, False otherwise.
        """
        # Increment attempt counter
        self.attempt_count += 1

        # Check if max attempts reached
        max_attempts = getattr(settings, "OTP_MAX_ATTEMPTS", 3)
        if self.attempt_count > max_attempts:
            self.is_expired = True
            self.save()
            return False

        # Check if OTP is valid
        if not self.is_valid:
            self.save()
            return False

        # Check if code matches
        if self.code != code:
            self.save()
            return False

        # Mark as used
        self.is_used = True
        self.used_at = timezone.now()
        self.save()

        return True

    def mark_as_expired(self):
        """Mark this OTP as expired."""
        self.is_expired = True
        self.save()
