from django.db.models import Manager
from django.db.models.base import Model
from django.utils.translation import gettext_lazy as _


class AvailableCountryManager(Manager):
    def get_code(self, iso_code: str):
        qs = self.filter(iso_code=iso_code).values("code")

        if qs.exists():
            return qs.first().get("code")

        return None
