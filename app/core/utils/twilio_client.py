import os

from twilio.rest import Client


class MessageClient:
    _BODY_VIRIFICATION = "Your vefirification code is {0}"
    _TWILIO_PHONE_PREFIX = "whatsapp:"

    @classmethod
    def send_message(cls, body, to):
        account_ssid = os.environ.get("TWILIO_ACCOUNT_SSID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        sender = os.environ.get("TWILIO_SENDER")

        twilio_client = Client(account_ssid, auth_token)

        _to = f"{cls._TWILIO_PHONE_PREFIX}{to}"
        _from = f"{cls._TWILIO_PHONE_PREFIX}{sender}"

        message = twilio_client.messages.create(
            body=body,
            to=_to,
            from_=_from,
        )

        return message
