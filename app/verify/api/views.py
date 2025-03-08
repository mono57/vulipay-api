from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.verify.api.serializers import GenerateOTPSerializer, VerifyOTPSerializer


class GenerateOTPView(APIView):
    """
    API view for generating OTP.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = GenerateOTPSerializer(data=request.data)

        if serializer.is_valid():
            # Generate OTP using the serializer
            result = serializer.generate_otp()

            if result["success"]:
                response_data = {
                    "success": True,
                    "message": result["message"],
                    "expires_at": result["expires_at"],
                }

                # Include when the next OTP can be requested if available
                if "otp" in result and result["otp"].next_otp_allowed_at:
                    response_data["next_allowed_at"] = result["otp"].next_otp_allowed_at

                return Response(response_data, status=status.HTTP_200_OK)
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
    """
    API view for verifying OTP.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = VerifyOTPSerializer(data=request.data)

        if serializer.is_valid():
            # Verify OTP using the serializer
            result = serializer.verify_otp()

            if result["success"]:
                response_data = {"success": True, "message": result["message"]}

                # Include user details and tokens if available
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
