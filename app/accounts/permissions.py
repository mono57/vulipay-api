from rest_framework.permissions import BasePermission

from app.accounts.models import Account
from app.core.constants import AppPermissions
from app.transactions.models import Transaction


class IsAuthenticatedAccount(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user is not None and isinstance(request.user, Account))


class CanPerformPaymentPermission(BasePermission):
    perm = AppPermissions.can_perform_payment

    def has_permission(self, request, view):
        return request.user.has_perm(self.perm)


class CanReceivePaymentPermission(BasePermission):
    perm = AppPermissions.can_receive_payment

    def has_object_permission(self, request, view, obj: Transaction):
        return obj.receiver_account.has_perm(self.perm)
