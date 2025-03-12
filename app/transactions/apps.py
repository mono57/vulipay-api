from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.transactions"

    def ready(self):
        import app.transactions.signals  # noqa
