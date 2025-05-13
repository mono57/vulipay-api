from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.core.utils.responses import success_response, validation_error_response
from app.verify.api.serializers import (
    AccountRecoverySerializer,
    GenerateOTPSerializer,
    VerifyOTPSerializer,
)


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
                        "message": {"type": "string", "description": "Success message"},
                        "data": {
                            "type": "object",
                            "properties": {
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
                        "error_code": {"type": "null"},
                        "errors": {"type": "null"},
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
            try:
                result = serializer.generate_otp()

                if result:
                    data = {
                        "expires_at": result["expires_at"],
                    }

                    if "otp" in result and result["otp"].next_otp_allowed_at:
                        data["next_allowed_at"] = result["otp"].next_otp_allowed_at

                    return success_response(
                        message=_("Verification code sent to {identifier}.").format(
                            identifier=result["identifier"]
                        ),
                        data=result,
                        status_code=status.HTTP_200_OK,
                    )
                else:
                    if "waiting_seconds" in result:
                        return error_response(
                            message=result["message"],
                            errors={
                                "waiting_seconds": result["waiting_seconds"],
                                "next_allowed_at": result["next_allowed_at"],
                            },
                            error_code="RATE_LIMITED",
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        )
                    else:
                        return error_response(
                            message=result["message"],
                            error_code="SERVER_ERROR",
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
            except Exception as e:
                return error_response(
                    message=str(e),
                    error_code="SERVER_ERROR",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

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
                        "message": {"type": "string", "description": "Success message"},
                        "data": {
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
                        "error_code": {"type": "null"},
                        "errors": {"type": "null"},
                    },
                },
            ),
            400: OpenApiResponse(description="Invalid request data or invalid OTP"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = VerifyOTPSerializer(data=request.data)

        if serializer.is_valid():
            response = serializer.verify_otp()

            if response["success"]:
                # Extract user, wallet, and tokens from the response
                data = {}
                for key in ["user", "wallet", "tokens"]:
                    if key in response:
                        data[key] = response[key]

                return success_response(
                    message=response["message"],
                    data=data,
                    status_code=status.HTTP_200_OK,
                )
            else:
                return validation_error_response(
                    message=response["message"],
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
                        "message": {"type": "string", "description": "Success message"},
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
                result = serializer.recover_account()

                if result["success"]:
                    return Response(
                        {
                            "message": result["message"],
                            "masked_email": result["masked_email"],
                            "expires_at": result["expires_at"],
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    if "waiting_seconds" in result:
                        return Response(
                            {
                                "message": result["message"],
                                "error_code": "RATE_LIMITED",
                                "errors": {
                                    "waiting_seconds": result["waiting_seconds"],
                                    "next_allowed_at": result["next_allowed_at"],
                                },
                            },
                            status=status.HTTP_429_TOO_MANY_REQUESTS,
                        )
                    else:
                        return Response(
                            {
                                "message": result["message"],
                                "error_code": None,
                                "errors": None,
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            else:
                return Response(
                    {
                        "message": next(iter(serializer.errors.values()))[0],
                        "error_code": "VALIDATION_ERROR",
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except serializers.ValidationError as e:
            return Response(
                {
                    "message": str(e.detail[0]),
                    "error_code": "VALIDATION_ERROR",
                    "errors": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
