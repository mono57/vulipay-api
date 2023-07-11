from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.accounts"

    def ready(self):
        super().ready()
        import app.accounts.signals
