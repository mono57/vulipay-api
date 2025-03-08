import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Union

from django.conf import settings
from django.utils import timezone

from app.verify.models import OTP, OTPWaitingPeriodError

logger = logging.getLogger(__name__)


class OTPDeliveryChannel(ABC):
    """Abstract base class for OTP delivery channels."""

    @abstractmethod
    def send(self, recipient: str, code: str) -> bool:
        """
        Send the OTP code to the recipient.

        Args:
            recipient: The recipient identifier (phone number, email, etc.)
            code: The OTP code to send

        Returns:
            bool: True if sending was successful, False otherwise
        """
        pass


class SMSDeliveryChannel(OTPDeliveryChannel):
    """SMS delivery channel for OTP codes."""

    def send(self, recipient: str, code: str) -> bool:
        """
        Send the OTP code via SMS.

        Args:
            recipient: The phone number to send to
            code: The OTP code to send

        Returns:
            bool: True if sending was successful, False otherwise
        """
        try:
            # Here you would integrate with your SMS provider
            # For example, using Twilio:
            if hasattr(settings, "TWILIO_ENABLED") and settings.TWILIO_ENABLED:
                from twilio.rest import Client

                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                message = client.messages.create(
                    body=f"Your verification code is: {code}",
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=recipient,
                )
                logger.info(f"SMS sent to {recipient}, SID: {message.sid}")
                return True
            else:
                # For development, just log the code
                logger.info(f"[DEVELOPMENT] SMS OTP for {recipient}: {code}")
                return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {recipient}: {str(e)}")
            return False


class EmailDeliveryChannel(OTPDeliveryChannel):
    """Email delivery channel for OTP codes."""

    def send(self, recipient: str, code: str) -> bool:
        """
        Send the OTP code via email.

        Args:
            recipient: The email address to send to
            code: The OTP code to send

        Returns:
            bool: True if sending was successful, False otherwise
        """
        try:
            from django.core.mail import send_mail

            subject = "Your Verification Code"
            message = f"Your verification code is: {code}"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [recipient]

            send_mail(subject, message, from_email, recipient_list)
            logger.info(f"Email sent to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False


class WhatsAppDeliveryChannel(OTPDeliveryChannel):
    """WhatsApp delivery channel for OTP codes."""

    def send(self, recipient: str, code: str) -> bool:
        """
        Send the OTP code via WhatsApp.

        Args:
            recipient: The phone number to send to
            code: The OTP code to send

        Returns:
            bool: True if sending was successful, False otherwise
        """
        try:
            # Here you would integrate with WhatsApp Business API
            # For development, just log the code
            logger.info(f"[DEVELOPMENT] WhatsApp OTP for {recipient}: {code}")
            return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {recipient}: {str(e)}")
            return False


# Factory for delivery channels
DELIVERY_CHANNELS = {
    "sms": SMSDeliveryChannel(),
    "email": EmailDeliveryChannel(),
    "whatsapp": WhatsAppDeliveryChannel(),
}


class OTPService:
    """Service for generating and verifying OTPs."""

    @staticmethod
    def generate_otp(
        identifier: str, channel: str = "sms", length: int = 6
    ) -> Dict[str, Union[bool, str, OTP, int, timezone.datetime]]:
        """
        Generate a new OTP for the given identifier.

        Args:
            identifier: The user identifier (phone number, email, etc.)
            channel: The delivery channel to use
            length: The length of the OTP code

        Returns:
            Dict: A dictionary with the generation result, message, and OTP object if successful
        """
        try:
            # Check if the channel is supported
            if channel not in DELIVERY_CHANNELS:
                logger.error(f"Unsupported OTP delivery channel: {channel}")
                return {
                    "success": False,
                    "message": f"Unsupported delivery channel: {channel}",
                }

            try:
                # Create the OTP
                otp = OTP.objects.create_otp(identifier, channel, length)

                # Send the OTP
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
                    # If sending fails, mark the OTP as expired
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

    @staticmethod
    def verify_otp(identifier: str, code: str) -> Dict[str, Union[bool, str]]:
        """
        Verify an OTP code for the given identifier.

        Args:
            identifier: The user identifier (phone number, email, etc.)
            code: The OTP code to verify

        Returns:
            Dict: A dictionary with the verification result and a message
        """
        try:
            # Get the active OTP for this identifier
            otp = OTP.objects.get_active_otp(identifier)

            if not otp:
                return {
                    "success": False,
                    "message": "No active OTP found. Please request a new code.",
                }

            # Verify the code
            if otp.verify(code):
                return {"success": True, "message": "OTP verified successfully."}
            else:
                # Check if max attempts reached
                max_attempts = getattr(settings, "OTP_MAX_ATTEMPTS", 3)
                remaining_attempts = max_attempts - otp.attempt_count

                if remaining_attempts <= 0:
                    return {
                        "success": False,
                        "message": "Maximum verification attempts reached. Please request a new code.",
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Invalid code. {remaining_attempts} attempts remaining.",
                    }
        except Exception as e:
            logger.error(f"Error verifying OTP for {identifier}: {str(e)}")
            return {
                "success": False,
                "message": "An error occurred during verification.",
            }
