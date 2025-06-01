from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.core.utils.responses import validation_error_response
from app.verify.api.serializers import (
    AccountRecoverySerializer,
    GenerateOTPSerializer,
    NotFoundException,
    TooManyRequestsException,
    VerifyOTPSerializer,
)
from app.verify.models import OTPWaitingPeriodError


class GenerateOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Verify"],
        request=GenerateOTPSerializer,
        description="Generate a new OTP for a phone number or email address",
        responses={
            200: OpenApiResponse(
                description="OTP generated successfully",
                response={
                    "type": "object",
                    "properties": {
                        "identifier": {
                            "type": "string",
                            "description": "Identifier (phone number or email address)",
                        },
                        "channel": {
                            "type": "string",
                            "description": "Channel (sms or email)",
                        },
                        "expires_at": {
                            "type": "string",
                            "format": "date-time",
                            "description": "OTP expiration time",
                        },
                        "next_allowed_at": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Time when next OTP can be requested",
                            "nullable": True,
                        },
                    },
                },
            ),
            400: OpenApiResponse(description="Invalid request data"),
            429: OpenApiResponse(description="Too many OTP requests"),
            500: OpenApiResponse(description="Internal server error"),
        },
        examples=[
            OpenApiExample(
                name="Generate OTP via SMS",
                value={
                    "phone_number": "698765432",
                    "country_id": 1,
                    "country_dial_code": "237",
                    "channel": "sms",
                },
                request_only=True,
            ),
            OpenApiExample(
                name="Generate OTP via Email",
                value={"email": "user@example.com", "channel": "email"},
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = GenerateOTPSerializer(data=request.data)
        if serializer.is_valid():
            response = serializer.generate_otp()

            return Response(
                response,
                status=status.HTTP_200_OK,
            )
        print(serializer.errors)
        return validation_error_response(
            message="Invalid request data.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Verify"],
        request=VerifyOTPSerializer,
        description="Verify an OTP for a phone number or email address",
        responses={
            200: OpenApiResponse(
                description="OTP verified successfully",
                response={
                    "type": "object",
                    "properties": {
                        "user": {
                            "type": "object",
                            "properties": {
                                "full_name": {
                                    "type": "string",
                                    "description": "User full name",
                                },
                                "email": {
                                    "type": "string",
                                    "description": "User email",
                                },
                                "phone_number": {
                                    "type": "string",
                                    "description": "User phone number",
                                    "nullable": True,
                                },
                                "country": {
                                    "type": "string",
                                    "description": "User country name",
                                    "nullable": True,
                                },
                                "profile_picture": {
                                    "type": "string",
                                    "description": "URL to user's profile picture",
                                    "nullable": True,
                                },
                                "pin": {
                                    "type": "string",
                                    "description": "User's PIN for transaction authorization",
                                    "nullable": True,
                                },
                            },
                        },
                        "wallet": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "integer",
                                    "description": "Wallet ID",
                                },
                                "balance": {
                                    "type": "string",
                                    "description": "Current wallet balance",
                                },
                                "wallet_type": {
                                    "type": "string",
                                    "description": "Type of wallet (MAIN, BUSINESS)",
                                },
                                "currency": {
                                    "type": "string",
                                    "description": "Wallet currency",
                                    "nullable": True,
                                },
                                "is_active": {
                                    "type": "boolean",
                                    "description": "Whether the wallet is active",
                                },
                            },
                            "nullable": True,
                        },
                        "tokens": {
                            "type": "object",
                            "properties": {
                                "access": {
                                    "type": "string",
                                    "description": "JWT access token",
                                },
                                "refresh": {
                                    "type": "string",
                                    "description": "JWT refresh token",
                                },
                            },
                        },
                    },
                },
            ),
            400: OpenApiResponse(description="Invalid request data or invalid OTP"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = VerifyOTPSerializer(data=request.data)

        if serializer.is_valid():
            try:
                response = serializer.verify_otp()

                return Response(
                    response,
                    status=status.HTTP_200_OK,
                )
            except (
                NotFoundException,
                TooManyRequestsException,
                serializers.ValidationError,
            ) as e:
                if hasattr(e, "detail"):
                    return validation_error_response(
                        message=str(e.detail),
                        status_code=(
                            e.status_code
                            if hasattr(e, "status_code")
                            else status.HTTP_400_BAD_REQUEST
                        ),
                    )
                return validation_error_response(
                    message=str(e),
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        return validation_error_response(
            message="Invalid request data.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class AccountRecoveryView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Verify"],
        request=AccountRecoverySerializer,
        description="Initiate account recovery process",
        responses={
            200: OpenApiResponse(
                description="Recovery process initiated successfully",
                response={
                    "type": "object",
                    "properties": {
                        "masked_email": {
                            "type": "string",
                            "description": "Masked email address where the recovery code was sent",
                        },
                        "expires_at": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Recovery code expiration time",
                        },
                    },
                },
            ),
            400: OpenApiResponse(description="Invalid request data"),
            429: OpenApiResponse(description="Too many recovery attempts"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = AccountRecoverySerializer(data=request.data)

        try:
            if serializer.is_valid():
                response = serializer.recover_account()

                return Response(
                    response,
                    status=status.HTTP_200_OK,
                )
            else:
                return validation_error_response(
                    message=next(iter(serializer.errors.values()))[0],
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        except TooManyRequestsException as e:
            if hasattr(e, "detail") and "waiting_seconds" in e.detail:
                return Response(
                    {
                        "message": str(e.detail),
                        "error_code": "RATE_LIMITED",
                        "errors": {
                            "waiting_seconds": e.detail["waiting_seconds"],
                            "next_allowed_at": e.detail["next_allowed_at"],
                        },
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            else:
                return Response(
                    {
                        "message": (str(e.detail) if hasattr(e, "detail") else str(e)),
                        "error_code": "RATE_LIMITED",
                        "errors": None,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
        except (NotFoundException, serializers.ValidationError) as e:
            return validation_error_response(
                message=(str(e.detail) if hasattr(e, "detail") else str(e)),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except serializers.ValidationError as e:
            return validation_error_response(
                message=str(e.detail[0]),
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
