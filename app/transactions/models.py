from django.db import models
from django.utils.translation import gettext_lazy as _

from app.accounts.models import Account
from app.core.utils import AppCharField, AppModel, make_payment_code, make_transaction_ref

class TransactionStatus(models.TextChoices):
    INITIATED = 'INITIATED', _('Initiated')
    PENDING = 'PENDING', _('Pending')
    SUCCEED = 'SUCCEED', _('Succeed')
    FAILED = 'FAILED', _('Failed')

class TransactionType(models.TextChoices):
    P2P = 'P2P', _('Peer to Peer')
    MP = 'MP', _('Merchant payment')
    CI = 'CI', _('Cash In')
    CO = 'CO', _('Cash Out')

class Transaction(AppModel):
    reference = AppCharField(_('Reference'), max_length=30)
    payment_code = AppCharField(_('Payment code'), max_length=255)
    amount = models.FloatField(_('Amount'))
    status = AppCharField(
        _('Status'),
        max_length=10,
        choices=TransactionStatus.choices)
    type = AppCharField(
        _('Type'),
        max_length=4,
        choices=TransactionType.choices)
    payer_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True, related_name='debit_transactions')
    receiver_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True, related_name='credit_transactions')
    notes = models.TextField(_('Notes'), null=True)

    def __str__(self):
        return self.reference

    @classmethod
    def create_P2P_transaction(cls, amount: float, receiver_account: Account, notes: str = None):
        klass = __class__
        # P2P.DF2422.1683740925
        transaction_ref = make_transaction_ref(TransactionType.P2P)
        # vulipay$P2P$SDFG34GE3G4234G42345G4F3ERF34G543FD3F4G54F
        t_payment_code = make_payment_code(transaction_ref, TransactionType.P2P)

        transaction = klass.objects.create(
            reference=transaction_ref,
            payment_code=t_payment_code,
            amount=amount,
            receiver_account=receiver_account,
            status=TransactionStatus.INITIATED,
            type=TransactionType.P2P,
            notes=notes)

        return transaction