from django.conf import settings
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from app.accounts.api.serializers import (
    CountrySerializer,
    ProfilePictureConfirmationSerializer,
    ProfilePicturePresignedUrlSerializer,
    UserFullNameUpdateSerializer,
    UserPINSetupSerializer,
    UserPreferencesSerializer,
    UserProfilePictureSerializer,
)
from app.accounts.authentication import AppJWTAuthentication
from app.accounts.cache import (
    COUNTRY_IDS_CACHE_KEY,
    COUNTRY_IDS_CACHE_TIMEOUT,
    get_cache_stats,
)
from app.accounts.models import AvailableCountry, User
from app.core.utils import ProfilePictureStorage


class UserFullNameRateThrottle(UserRateThrottle):
    rate = "3/minute"


@extend_schema(
    tags=["Accounts"],
    operation_id="update_user_full_name",
    description="Update the user's full name",
    responses={
        200: OpenApiResponse(
            description="Full name updated successfully",
            response={
                "type": "object",
                "properties": {
                    "full_name": {
                        "type": "string",
                        "description": "User full name",
                    },
                    "email": {"type": "string", "description": "User email"},
                    "phone_number": {
                        "type": "string",
                        "description": "User phone number",
                        "nullable": True,
                    },
                    "country": {
                        "type": "string",
                        "description": "User country",
                        "nullable": True,
                    },
                    "profile_picture": {
                        "type": "string",
                        "description": "User profile picture",
                        "nullable": True,
                    },
                },
            },
        ),
        400: OpenApiResponse(description="Validation error"),
    },
    request=UserFullNameUpdateSerializer,
)
class UserFullNameUpdateView(generics.UpdateAPIView):
    serializer_class = UserFullNameUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserFullNameRateThrottle] if not settings.DEBUG else []

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
    operation_id="get_profile_picture_presigned_url",
    description="Get a presigned URL for direct upload of a profile picture",
    responses={
        200: OpenApiResponse(
            description="Presigned URL generated successfully",
            response={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "fields": {"type": "object"},
                    "file_key": {"type": "string"},
                    "method": {"type": "string", "example": "POST"},
                },
            },
        ),
        400: OpenApiResponse(description="Invalid file type or extension"),
        503: OpenApiResponse(description="Storage service unavailable"),
    },
    request=ProfilePicturePresignedUrlSerializer,
)
class ProfilePicturePresignedUrlView(generics.GenericAPIView):
    serializer_class = ProfilePicturePresignedUrlSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_extension = serializer.validated_data["file_extension"]
        content_type = serializer.validated_data["content_type"]

        storage = ProfilePictureStorage()

        presigned_data = storage.generate_presigned_url(
            file_extension=file_extension, content_type=content_type
        )

        if not presigned_data:
            return Response(
                {"detail": "Failed to generate presigned URL"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(presigned_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Accounts"],
    operation_id="confirm_profile_picture_upload",
    description="Confirm the upload of a profile picture and update the user's profile",
    responses={
        200: OpenApiResponse(
            description="Profile picture updated successfully",
            response={
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "example": "Profile picture updated successfully",
                    },
                    "profile_picture_url": {"type": "string"},
                },
            },
        ),
        400: OpenApiResponse(description="Invalid file key or file not found"),
    },
    request=ProfilePictureConfirmationSerializer,
)
class ProfilePictureConfirmationView(generics.GenericAPIView):
    serializer_class = ProfilePictureConfirmationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        serializer.update(user, serializer.validated_data)

        profile_picture_url = user.profile_picture.url if user.profile_picture else None

        return Response(
            {
                "detail": "Profile picture updated successfully",
                "profile_picture_url": profile_picture_url,
            },
            status=status.HTTP_200_OK,
        )


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


# cache this view
@extend_schema(
    tags=["Accounts"],
    operation_id="list_countries",
    description="List all available countries with their details",
    responses={
        200: OpenApiResponse(
            description="Countries fetched successfully",
            response={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Country name"},
                    "dial_code": {
                        "type": "string",
                        "description": "Country dial code",
                    },
                    "iso_code": {
                        "type": "string",
                        "description": "Country ISO code",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Country currency",
                    },
                    "flag": {
                        "type": "string",
                        "description": "Country flag",
                        "nullable": True,
                    },
                },
            },
        ),
    },
)
class CountryListView(generics.ListAPIView):
    queryset = AvailableCountry.objects.all().order_by("name")
    serializer_class = CountrySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    @method_decorator(cache_page(COUNTRY_IDS_CACHE_TIMEOUT))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset().order_by("name")
        countries_ids = qs.values_list("id", flat=True)
        cache.set(COUNTRY_IDS_CACHE_KEY, countries_ids, COUNTRY_IDS_CACHE_TIMEOUT)
        return qs


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


@extend_schema(
    tags=["Accounts"],
    operation_id="update_user_preferences",
    description="Update the user's preferences",
    responses={
        200: UserPreferencesSerializer,
        400: OpenApiResponse(description="Invalid preferences format"),
    },
    request=UserPreferencesSerializer,
)
class UserPreferencesUpdateView(generics.UpdateAPIView):
    serializer_class = UserPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=["Accounts"],
    operation_id="generate_token_for_user",
    description="Generate a JWT token for a user (admin only)",
    responses={
        200: OpenApiResponse(description="JWT token generated successfully"),
    },
)
@api_view(["GET"])
@authentication_classes([SessionAuthentication, AppJWTAuthentication])
@permission_classes([IsAdminUser])
def generate_token_for_user(request, user_id):
    """Generate a JWT token for a user (admin only)"""
    try:
        user = User.objects.get(id=user_id)
        refresh = RefreshToken.for_user(user)
        return Response(
            {"access_token": str(refresh.access_token), "refresh_token": str(refresh)}
        )
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)


@extend_schema(
    tags=["Accounts"],
    operation_id="check_hashed_phone_numbers",
    description="Check if hashed phone numbers exist in the database and return user details for each existing hashed phone number",
    responses={
        200: OpenApiResponse(
            description="User details for existing hashed phone numbers returned successfully",
            response={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "full_name": {
                            "type": "string",
                            "example": "John Doe",
                            "description": "User's full name",
                        },
                        "profile_url": {
                            "type": "string",
                            "example": "https://example.com/profile_pictures/user123.jpg",
                            "description": "URL to the user's profile picture",
                        },
                        "hashed_phone_number": {
                            "type": "string",
                            "example": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
                            "description": "SHA-256 hashed phone number",
                        },
                        "username": {
                            "type": "string",
                            "example": "johndoe",
                            "description": "Username derived from email",
                            "nullable": True,
                        },
                    },
                },
            },
        ),
        400: OpenApiResponse(description="Validation error"),
    },
)
class CheckHashedPhoneNumbersView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    class InputSerializer(serializers.Serializer):
        hashed_phone_numbers = serializers.ListField(
            child=serializers.CharField(max_length=64),
            min_length=1,
            required=False,
            help_text="List of SHA-256 hashed phone numbers to check",
        )

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "message": "Validation failed",
                    "data": None,
                    "error_code": "VALIDATION_ERROR",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        hashed_phone_numbers = serializer.validated_data["hashed_phone_numbers"]

        matching_users = User.objects.filter(
            hashed_phone_number__in=hashed_phone_numbers
        ).values("full_name", "profile_picture", "hashed_phone_number", "email")

        user_details = []
        for user in matching_users:
            user_details.append(
                {
                    "full_name": user.full_name,
                    "profile_url": (
                        user.profile_picture.url
                        if user.profile_picture
                        else "https://via.placeholder.com/150"
                    ),
                    "hashed_phone_number": user.hashed_phone_number,
                    "username": user.email.split("@")[0] if user.email else None,
                }
            )

        return Response(
            user_details,
            status=status.HTTP_200_OK,
        )
