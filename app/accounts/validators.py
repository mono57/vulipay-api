from django.conf import settings
from django.core import exceptions

def valid_vulipay_code(value):
    if not value.isdigit() or not len(value) == settings.PASSCODE_LENGTH:
        raise exceptions.ValidationError(_("Invalid code"))
