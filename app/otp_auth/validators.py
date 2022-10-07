from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def digits_validator(value):
    if not value.isdigit():
        raise ValidationError(_("Phone number should be numeric only"))
    return value
