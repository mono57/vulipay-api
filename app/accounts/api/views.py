from django.conf import settings

from rest_framework import generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import PassCode, User as UserModel
from app.accounts.api.serializers import PassCodeSerializer

User: UserModel = settings.AUTH_USER_MODEL

class PassCodeCreateAPIView(generics.CreateAPIView):
    http_method_names = ['post']
    serializer_class = PassCodeSerializer

# class PassCodeCreateAPIView(generics.CreateAPIView):
#     serializer_class = ConfirmCodeSerializer

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         data = serializer.data

#         phone_number: str = data.get("phone_number")
#         country_iso_code: str = data.get("country_iso_code")

#         user = User.get_or_create(
#             phone_number=phone_number, country_iso_code=country_iso_code
#         )

#         refresh = RefreshToken.for_user(user)

#         data = {"refresh": str(refresh), "access": str(refresh.access_token)}

#         return Response(data, status=status.HTTP_200_OK)
