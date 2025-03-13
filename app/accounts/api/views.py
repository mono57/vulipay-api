from rest_framework import generics, permissions

from app.accounts.api.mixins import AccountOwnerActionMixin
from app.accounts.api.serializers import (
    PinCreationSerializer,
    UserFullNameUpdateSerializer,
)
from app.accounts.models import Account
from app.accounts.permissions import IsAuthenticatedAccount


class PinCreationUpdateAPIView(AccountOwnerActionMixin, generics.UpdateAPIView):
    permission_classes = [IsAuthenticatedAccount]
    serializer_class = PinCreationSerializer
    queryset = Account.objects.all()
    lookup_field = "number"


class UserFullNameUpdateView(generics.UpdateAPIView):
    serializer_class = UserFullNameUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
