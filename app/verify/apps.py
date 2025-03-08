from django.apps import AppConfig


class VerifyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.verify"
    verbose_name = "User Verification"

    def ready(self):
        try:
            import app.verify.signals  # noqa F401
        except ImportError:
            pass
