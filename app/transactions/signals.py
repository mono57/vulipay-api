from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from app.accounts.models import User
from app.transactions.models import Wallet, WalletType


@receiver(post_save, sender=User)
def create_main_wallet(sender, instance, created, **kwargs):
    if (
        created
        and not Wallet.objects.filter(
            user=instance, wallet_type=WalletType.MAIN
        ).exists()
    ):
        Wallet.objects.create(
            user=instance, wallet_type=WalletType.MAIN, balance=0, is_active=True
        )
