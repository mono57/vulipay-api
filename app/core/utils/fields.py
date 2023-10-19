from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class AppCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.null:
            self.default = None


class AppAmountField(serializers.FloatField):
    def __init__(self, **kwargs):
        self.default_error_messages["min_value"] = _("Invalid transaction amount")
        kwargs.setdefault("min_value", 1)
        super().__init__(**kwargs)
