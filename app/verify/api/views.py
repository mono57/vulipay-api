from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.verify.api.serializers import GenerateOTPSerializer, VerifyOTPSerializer


class GenerateOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=GenerateOTPSerializer,
        operation_id="generate_otp",
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
        request=VerifyOTPSerializer,
        operation_id="verify_otp",
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
                            },
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
            result = serializer.verify_otp()

            if result["success"]:
                response_data = {"success": True, "message": result["message"]}

                if "user" in result:
                    response_data["user"] = result["user"]

                if "tokens" in result:
                    response_data["tokens"] = result["tokens"]

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"success": False, "message": result["message"]},
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
