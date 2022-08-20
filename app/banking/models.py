# from typing import

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import (
    make_password as make_pin,
    check_password as check_pin)

from accounts.models import PhoneNumber, User as UserModel, AvailableCountry
from banking.managers import AccountPinCodeManager
from app.utils.constants import TransactionType, TransactionStatus
from app.utils.generate_code import generate_code
from app.utils.timestamp import TimestampModel
from app.utils.models import CommonCode

User: UserModel = settings.AUTH_USER_MODEL

class Currency(TimestampModel):
    iso_code = models.CharField(max_length=8)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=5)
    country = models.ForeignKey(
        AvailableCountry,
        null=True,
        on_delete=models.SET_NULL)

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.iso_code, self.symbol)

class AccountPermissionMixin(models.Model):
    restricted = models.BooleanField(default=False)
    user: UserModel = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='account')
    class Meta:
        abstract = True

    def check_user_permission(self, perm):
        if self.restricted:
            return False
        return self.user.has_perm(perm)

    def can_perform_payment(self):
        return self.check_user_permission('can_perform_payment')

    def can_receive_payment(self):
        return self.check_user_permission('can_receive_payment')

    def can_cash_out_money(self):
        return self.check_user_permission('can_cash_out_money')

    def can_cach_in_money(self):
        return self.check_user_permission('can_cash_in_money')

class Account(TimestampModel, AccountPermissionMixin):
    number = models.CharField(max_length=255)
    balance = models.FloatField(default=0)
    last_balance_update = models.DateTimeField()

    def __str__(self):
        return self.number

    def save(self):
        self.number = generate_code(
            Model=self.__class__,
            lookup_field='number',
            length=settings.ACCOUNT_NUMBER_LENGTH
        )
        super().save()

    @property
    def pin_code(self):
        instance = self
        return AccountPinCode.objects.get_current_pin(instance)

class AccountPinCode(TimestampModel):
    pin = models.CharField(max_length=10)
    is_current = models.BooleanField(default=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='pin_code')

    objects: AccountPinCodeManager = AccountPinCodeManager()

    def __str__(self):
        return self.code

    def set_pin(self, raw_pin):
        self.pin = make_pin(raw_pin)

    def set_current(self):
        qs = self.objects.filter(Q(account=self.account) & Q(is_current=True))
        qs.update({'is_current': False})
        self.is_current = True
        self.save()

    def check_pin(self, raw_pin):
        return check_pin(raw_pin, self.pin)


class Transaction(TimestampModel):
    # Withdraw(Cash Out): from_account, to_phone_number
    # Topup (Cash In): from_phone_number, to_account
    # Payment (Customer Payment): from_account, to_account
    reference = models.CharField(max_length=255, verbose_name=_('Reference'))
    amount = models.FloatField(default=1.0, verbose_name=_('Amount'))
    from_account = models.ForeignKey(
        Account,
        null=True,
        on_delete=models.SET_NULL,
        related_name='performed_transactions')
    to_account = models.ForeignKey(
        Account,
        null=True,
        on_delete=models.SET_NULL,
        related_name='received_transactions')
    from_phone_number = models.ForeignKey(
        PhoneNumber,
        null=True,
        on_delete=models.SET_NULL,
        related_name='cash_in_transactions')
    to_phone_number = models.ForeignKey(
        PhoneNumber,
        null=True,
        on_delete=models.SET_NULL,
        related_name='cash_out_transactions')
    type = models.ForeignKey(
        CommonCode,
        null=True,
        related_name='from_type_transactions',
        on_delete=models.SET_NULL)
    status = models.ForeignKey(
        CommonCode,
        null=True,
        related_name='from_status_transactions',
        on_delete=models.SET_NULL)

    def __str__(self):
        return self.reference

