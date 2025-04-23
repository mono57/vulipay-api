from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.accounts"

    def ready(self):
        super().ready()
        import app.accounts.signals
        from app.accounts.cache import refresh_country_ids_cache

        try:
            refresh_country_ids_cache()
        except Exception:
            pass
