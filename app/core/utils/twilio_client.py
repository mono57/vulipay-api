import os

from twilio.rest import Client

class MessageClient:
    _BODY_VIRIFICATION = "Your vefirification code is {0}"

    @classmethod
    def send_message(cls, body, to):
        account_ssid = os.environ.get("TWILIO_ACCOUNT_SSID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        sender = os.environ.get("TWILIO_SENDER")

        twilio_client = Client(account_ssid, auth_token)

        message = twilio_client.messages.create(
            body=body,
            to=to,
            from_=sender,
        )

        return message
