from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView

from app.accounts.api.serializers import (
    UserFullNameUpdateSerializer,
    UserPINSetupSerializer,
)


@extend_schema(
    tags=["Accounts"],
    description="Update the user's full name",
    responses={
        200: UserFullNameUpdateSerializer,
        400: OpenApiResponse(description="Validation error"),
    },
    request=UserFullNameUpdateSerializer,
)
class UserFullNameUpdateView(generics.UpdateAPIView):
    serializer_class = UserFullNameUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=["Accounts"],
    description="Set up a 4-digit PIN for transaction authorization",
    responses={
        200: OpenApiResponse(
            description="PIN set successfully",
            response={
                "type": "object",
                "properties": {
                    "detail": {"type": "string", "example": "PIN set successfully"}
                },
            },
        ),
        400: OpenApiResponse(description="Invalid PIN format or PINs do not match"),
    },
    request=UserPINSetupSerializer,
)
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


class AppTokenRefreshView(TokenRefreshView):
    @extend_schema(
        tags=["Accounts"],
        description="Refresh a JWT token",
        responses={
            200: TokenRefreshSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
