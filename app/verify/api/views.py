from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

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
                        "success": {"type": "boolean", "description": "Success status"},
                        "message": {"type": "string", "description": "Success message"},
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
            result = serializer.generate_otp()

            if result["success"]:
                response_data = {
                    "success": True,
                    "message": result["message"],
                    "expires_at": result["expires_at"],
                }

                if "otp" in result and result["otp"].next_otp_allowed_at:
                    response_data["next_allowed_at"] = result["otp"].next_otp_allowed_at

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                if "waiting_seconds" in result:
                    return Response(
                        {
                            "success": False,
                            "message": result["message"],
                            "waiting_seconds": result["waiting_seconds"],
                            "next_allowed_at": result["next_allowed_at"],
                        },
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                    )
                else:
                    return Response(
                        {"success": False, "message": result["message"]},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

        return Response(
            {
                "success": False,
                "message": "Invalid request data.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
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
                        "success": {"type": "boolean", "description": "Success status"},
                        "message": {"type": "string", "description": "Success message"},
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
            ),
            400: OpenApiResponse(description="Invalid request data or invalid OTP"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = VerifyOTPSerializer(data=request.data)

        if serializer.is_valid():
            response = serializer.verify_otp()

            if response["success"]:
                return Response(response, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"success": False, "message": response["message"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {
                "success": False,
                "message": "Invalid request data.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
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
                        "success": {"type": "boolean", "description": "Success status"},
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
                    return Response(result, status=status.HTTP_200_OK)
                else:
                    if "waiting_seconds" in result:
                        return Response(
                            {
                                "success": False,
                                "message": result["message"],
                                "waiting_seconds": result["waiting_seconds"],
                                "next_allowed_at": result["next_allowed_at"],
                            },
                            status=status.HTTP_429_TOO_MANY_REQUESTS,
                        )
                    else:
                        return Response(
                            {"success": False, "message": result["message"]},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            else:
                return Response(
                    {
                        "success": False,
                        "message": next(iter(serializer.errors.values()))[0],
                        "errors": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except serializers.ValidationError as e:
            return Response(
                {
                    "success": False,
                    "message": str(e.detail[0]),
                    "errors": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
