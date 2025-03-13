from rest_framework import generics, permissions, status
from rest_framework.response import Response

from app.accounts.api.serializers import (
    UserFullNameUpdateSerializer,
    UserPINSetupSerializer,
)


class UserFullNameUpdateView(generics.UpdateAPIView):
    serializer_class = UserFullNameUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserPINSetupView(generics.UpdateAPIView):
    serializer_class = UserPINSetupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "PIN set successfully"}, status=status.HTTP_200_OK)
