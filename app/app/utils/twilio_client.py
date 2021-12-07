from twilio.rest import Client

import os

class MessageClient:
    def __init__(self):
        account_ssid = os.environ.get('TWILIO_ACCOUNT_SSID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.sender = os.environ.get('TWILIO_SENDER')
        print('account_ssid', account_ssid)
        self.twilio_client = Client(account_ssid, auth_token)

    def send_message(self, body, to):
        self.twilio_client.messages.create(
            body=body,
            to=to,
            from_=self.sender,
        )
