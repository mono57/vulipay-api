from rest_framework.exceptions import APIException
from rest_framework import status

class UnprocessableEntityError(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = 'unprocessable_entity'