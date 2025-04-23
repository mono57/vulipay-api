from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.accounts"

    def ready(self):
        super().ready()
        import app.accounts.signals
        from app.accounts.cache import refresh_country_ids_cache

        def refresh_country_ids_cache_wrapper(sender, **kwargs):
            refresh_country_ids_cache()

        post_migrate.connect(refresh_country_ids_cache_wrapper, sender=self)
