import datetime

from django.conf import settings
from django.db.models import Manager, Q
from django.db.models.base import Model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PassCodeManager(Manager):
    def expired_keys(self):
        return self.filter(self.expired_q())

    def get_last_created_code(self, int_phone_number):
        code = (
            self.filter(phone_number=int_phone_number)
            .values("code")
            .order_by("-created_at")
            .first()
        )

        return code

    def unexpired_keys(self):
        return self.exclude(self.expired_keys())

    def expired_q(self):
        sent_threshold = timezone.now() - datetime.timedelta(
            days=settings.PHONE_NUMBER_CONFIRMATION_DAYS
        )
        return Q(sent__lt=sent_threshold)

    def to_seconds_datetime(_datetime):
        return _datetime.timestamp()
