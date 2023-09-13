import re

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


def pin_validator(value):
    # change validation message in that case
    pattern = r"^(?!.*(\d)(?:-?\1){3})(?!1234|4321|5678|8765|2345|5432|3456|6543|4567|7654|5678|6789|7890|9876|0987)\d{4}$"
    if not bool(re.match(pattern, value)):
        raise serializers.ValidationError(_("Invalid PIN"), code="invalid_pin")
    return value
