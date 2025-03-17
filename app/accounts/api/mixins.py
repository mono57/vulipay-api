from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions


class AppAccessMixin:
    access_denied_message = ""
    access_denied_code = ""

    def get_access_denied_message(self):
        return self.access_denied_message

    def handle_no_permission(self):
        raise exceptions.PermissionDenied(
            self.get_access_denied_message(), code=self.access_denied_code
        )


class ValidPINRequiredMixin(AppAccessMixin):
    access_denied_code = "invalid_pin"
    access_denied_message = _("Invalid PIN")

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        pin = request.data.get("pin")
        if pin is None:
            raise exceptions.ValidationError(_("PIN is required"), code="required_pin")

        if not request.user.verify_pin(pin):
            self.handle_no_permission()
