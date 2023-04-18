from django.conf import settings

from rest_framework import generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import PassCode, Account as UserModel
from app.accounts.api.serializers import PassCodeSerializer, VerifyPassCodeSerializer

User: UserModel = settings.AUTH_USER_MODEL

class PassCodeCreateAPIView(generics.CreateAPIView):
    http_method_names = ['post']
    serializer_class = PassCodeSerializer

class VerifyPassCodeCreateAPIView(generics.CreateAPIView):
    http_method_names = ['post']
    serializer_class = VerifyPassCodeSerializer

