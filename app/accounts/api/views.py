from accounts.api.serializers import ConfirmCodeSerializer, RegisterSerializer
from accounts.models import AvailableCountry, PhoneNumber
from accounts.models import PhoneNumberConfirmationCode as Code
from accounts.models import User as UserModel
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

User: UserModel = get_user_model()


class GenerateCodeCreateAPIView(CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        int_phone_number = data.get("int_phone_number")

        code: Code = Code.objects.get_last_created_code(int_phone_number)

        if code and not code.can_create_next_code():
            return Response(
                data,
                status=status.HTTP_401_UNAUTHORIZED,
            )

        waiting_time = 0

        if not code or (code.can_create_next_code() and code.verified):
            waiting_time = 30

        else:
            waiting_time = code.waiting_time + 30

        code: Code = Code.create(int_phone_number, waiting_time)
        code.waiting_time = waiting_time

        code.send_key()

        data["waiting_time"] = waiting_time

        return Response(
            data,
            status=status.HTTP_201_CREATED,
        )


class ConfirmCodeCreateAPIView(CreateAPIView):
    serializer_class = ConfirmCodeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        phone_number: str = data.get("phone_number")
        country_iso_code: str = data.get("country_iso_code")

        User.get_or_create(phone_number=phone_number, country_iso_code=country_iso_code)

        return Response(data={}, status=status.HTTP_200_OK)
