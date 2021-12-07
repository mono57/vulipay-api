from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from rest_framework import status

from accounts.models import AvailableCountry, PhoneNumber, PhoneNumberConfirmationCode
from accounts.api.serializers import ConfirmCodeSerializer, RegisterSerializer

User = get_user_model()

class RegisterCreateAPIView(CreateAPIView):
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        data = serializer.data

        code: PhoneNumberConfirmationCode = PhoneNumberConfirmationCode.create(
            data.get('phone_number')
        )
        code.send_key()

        headers = self.get_success_headers(data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers)

class ConfirmCodeCreateAPIView(CreateAPIView):
    serializer_class = ConfirmCodeSerializer

    def perform_create(self, serializer):
        data = serializer.data

        user = User.objects.create()
        country = AvailableCountry.objects.get(
            country_iso_code=data.get('country_iso_code')
        )

        phone_number_obj: PhoneNumber = PhoneNumber.objects.create(
            phone_number=data.get('phone_number')
        )

        phone_number_obj.user = user
        phone_number_obj.country = country
        phone_number_obj.save()

        headers = self.get_success_headers(data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers)