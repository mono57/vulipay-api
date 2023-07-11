from django.apps import apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from app.accounts.models import create_master_account_after_migration


@receiver(post_migrate)
def run_script_after_first_migration(sender, **kwargs):
    # To be writed
    # app_name = apps.get_containing_app_config(sender.__module__).name
    if kwargs.get("plan", False) and kwargs["plan"][0][1] == "app.accounts":
        create_master_account_after_migration()
