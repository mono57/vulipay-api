import base64
import json
import os

from cryptography.fernet import Fernet
from django.conf import settings


def get_encryption_key():
    key = getattr(
        settings, "ENCRYPTION_KEY", base64.urlsafe_b64encode(os.urandom(32)).decode()
    )
    return key


def encrypt_data(data):
    json_data = json.dumps(data)

    key = get_encryption_key()

    fernet = Fernet(key.encode() if isinstance(key, str) else key)

    encrypted_data = fernet.encrypt(json_data.encode())

    return base64.urlsafe_b64encode(encrypted_data).decode()


def decrypt_data(encrypted_data):
    decoded_data = base64.urlsafe_b64decode(encrypted_data)

    key = get_encryption_key()

    fernet = Fernet(key.encode() if isinstance(key, str) else key)

    decrypted_data = fernet.decrypt(decoded_data).decode()

    return json.loads(decrypted_data)
