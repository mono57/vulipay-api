from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


class AppAPIRequestFactory(APIRequestFactory):
    default_format = "json"


class EmptyResponseView(APIView):
    def get(self, request, *args, **kwargs):
        return Response()

    def put(self, request, *args, **kwargs):
        return Response()
