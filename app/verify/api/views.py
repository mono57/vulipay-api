from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.verify.api.serializers import GenerateOTPSerializer, VerifyOTPSerializer
from app.verify.services import OTPService


class GenerateOTPView(APIView):
    """
    API view for generating OTP.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = GenerateOTPSerializer(data=request.data)

        if serializer.is_valid():
            identifier = serializer.validated_data["identifier"]
            channel = serializer.validated_data["channel"]

            # Generate OTP
            result = OTPService.generate_otp(identifier, channel)

            if result["success"]:
                return Response(
                    {
                        "success": True,
                        "message": result["message"],
                        "expires_at": result["expires_at"],
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                # Check if this is a waiting period error
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
                        {
                            "success": False,
                            "message": result["message"],
                        },
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
    """
    API view for verifying OTP.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = VerifyOTPSerializer(data=request.data)

        if serializer.is_valid():
            identifier = serializer.validated_data["identifier"]
            code = serializer.validated_data["code"]

            # Verify OTP
            result = OTPService.verify_otp(identifier, code)

            if result["success"]:
                return Response(
                    {"success": True, "message": result["message"]},
                    status=status.HTTP_200_OK,
                )
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
