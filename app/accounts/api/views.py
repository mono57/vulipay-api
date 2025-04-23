from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView

from app.accounts.api.serializers import (
    CountrySerializer,
    UserFullNameUpdateSerializer,
    UserPINSetupSerializer,
    UserProfilePictureSerializer,
)
from app.accounts.cache import get_cache_stats
from app.accounts.models import AvailableCountry


@extend_schema(
    tags=["Accounts"],
    operation_id="update_user_full_name",
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
    operation_id="update_user_profile_picture",
    description="Upload or update the user's profile picture",
    responses={
        200: UserProfilePictureSerializer,
        400: OpenApiResponse(description="Invalid image file"),
    },
    request=UserProfilePictureSerializer,
)
class UserProfilePictureUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfilePictureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=["Accounts"],
    operation_id="setup_user_pin",
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
        operation_id="refresh_jwt_token",
        description="Refresh a JWT token",
        responses={
            200: TokenRefreshSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(
    tags=["Accounts"],
    operation_id="list_countries",
    description="List all available countries with their details",
    responses={
        200: CountrySerializer(many=True),
    },
)
class CountryListView(generics.ListAPIView):
    queryset = AvailableCountry.objects.all().order_by("name")
    serializer_class = CountrySerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=["Accounts"],
    operation_id="cache_health_check",
    description="Check the health of the cache",
    responses={
        200: OpenApiResponse(description="Cache health check"),
    },
)
@api_view(["GET"])
@permission_classes([IsAdminUser])
def cache_health_check(request):
    stats = get_cache_stats()
    return Response(stats, status=status.HTTP_200_OK)
