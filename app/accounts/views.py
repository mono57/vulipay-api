from accounts.api.serializers import (ConfirmCodeSerializer,
                                      CreateCodeNotAllowSerializer,
                                      RegisterSerializer)
from accounts.models import AvailableCountry, PhoneNumber
from accounts.models import PhoneNumberConfirmationCode as Code
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()


class RegisterCreateAPIView(CreateAPIView):
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        data = serializer.data
        int_phone_number = data.get("phone_number")

        code: Code = Code.objects.get_last_created_code(int_phone_number)

        if code and not code.can_create_next_code():
            serializer = CreateCodeNotAllowSerializer(data={})

            return Response(
                serializer.data,
                status=status.HTTP_401_UNAUTHORIZED,
            )

        waiting_time = 0

        if not code or (code.can_create_next_code() and code.verified):
            waiting_time = 30

        else:
            code.waiting_time += 30

        code: Code = Code.create(int_phone_number, waiting_time)
        code.waiting_time = waiting_time

        code.send_key()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ResendConfirmationCodeAPIView(APIView):
    def post(self, request, *args, **kwargs):
        print(request.data)
        # PhoneNumberConfirmationCode =
        return Response(request.data, status=status.HTTP_200_OK)


class ConfirmCodeCreateAPIView(CreateAPIView):
    serializer_class = ConfirmCodeSerializer

    def perform_create(self, serializer):
        data = serializer.data

        phone_number: str = data.get("phone_number")

        user = User.objects.create_user(phone_number)

        country = AvailableCountry.objects.get(
            country_iso_code=data.get("country_iso_code")
        )

        phone_number_obj: PhoneNumber = PhoneNumber.objects.create(
            phone_number=phone_number
        )

        phone_number_obj.user = user
        phone_number_obj.country = country
        phone_number_obj.save()

        headers = self.get_success_headers(data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
