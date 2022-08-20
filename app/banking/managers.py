from django.db import models
from django.db.models import Q

class AccountPinCodeManager(models.Manager):
    def get_current_pin(self, account):
        queryset = self.get_queryset()
        return queryset.filter(Q(account=account) & Q(is_current=True))
