from rest_framework import generics, permissions

from app.accounts.api.serializers import UserFullNameUpdateSerializer


class UserFullNameUpdateView(generics.UpdateAPIView):
    serializer_class = UserFullNameUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
