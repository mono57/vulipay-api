from rest_framework.permissions import BasePermission

from app.accounts.models import Account

class IsAuthenticatedAccount(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user is not None and isinstance(request.user, Account))