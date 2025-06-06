import logging
from abc import ABC, abstractmethod

from django.conf import settings

logger = logging.getLogger(__name__)


class OTPDeliveryChannel(ABC):
    @abstractmethod
    def send(self, recipient: str, code: str) -> bool:
        pass


class SMSDeliveryChannel(OTPDeliveryChannel):
    def send(self, recipient: str, code: str) -> bool:
        try:
            if hasattr(settings, "TWILIO_ENABLED") and settings.TWILIO_ENABLED:
                from twilio.base.exceptions import TwilioRestException
                from twilio.rest import Client

                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

                message = client.messages.create(
                    body=f"Your Vulipay verification code is: {code}",
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=recipient,
                )
                logger.info(f"SMS sent to {recipient}, SID: {message.sid}")
                return True
            else:
                # For development, just log the code when Twilio is not enabled
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
    _TWILIO_PHONE_PREFIX = "whatsapp:"

    def send(self, recipient: str, code: str) -> bool:
        try:
            if hasattr(settings, "TWILIO_ENABLED") and settings.TWILIO_ENABLED:
                from twilio.rest import Client

                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

                whatsapp_to = f"{self._TWILIO_PHONE_PREFIX}{recipient}"
                whatsapp_from = (
                    f"{self._TWILIO_PHONE_PREFIX}{settings.TWILIO_PHONE_NUMBER}"
                )

                message = client.messages.create(
                    body=f"Your Vulipay verification code is: {code}",
                    to=whatsapp_to,
                    from_=whatsapp_from,
                )
                logger.info(f"WhatsApp message sent to {recipient}, SID: {message.sid}")
                return True
            else:
                logger.info(f"[DEVELOPMENT] WhatsApp OTP for {recipient}: {code}")
                return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {recipient}: {str(e)}")
            return False


DELIVERY_CHANNELS = {
    "sms": WhatsAppDeliveryChannel(),
    "email": EmailDeliveryChannel(),
    "whatsapp": WhatsAppDeliveryChannel(),
}
