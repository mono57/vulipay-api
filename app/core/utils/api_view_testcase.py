import logging

from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


def client_action_wrapper(action):
    def wrapper_method(self, *args, **kwargs) -> Response:
        if self.view_name is None:
            raise ValueError("Must give value for `view_name` property")

        reverse_args = kwargs.pop("reverse_args", tuple())
        reverse_kwargs = kwargs.pop("reverse_kwargs", dict())

        url = reverse(self.view_name, args=reverse_args, kwargs=reverse_kwargs)

        return getattr(self.client, action)(url, *args, **kwargs)

    return wrapper_method


class APIViewTestCase(TransactionTestCase):
    client_class: APIClient = APIClient
    logger = logging.getLogger("django.request")

    view_name = None

    view_post = client_action_wrapper("post")
    view_get = client_action_wrapper("get")
    view_put = client_action_wrapper("put")

    def authenticate_with_jwttoken(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def authenticate_with_account(self, account):
        token = str(RefreshToken.for_user(account).access_token)
        self.authenticate_with_jwttoken(token=token)

    def setUp(self):
        super().setUp()
        self.previous_level = self.logger.getEffectiveLevel()
        self.logger.setLevel(logging.ERROR)

    def tearDown(self):
        super().tearDown()
        self.logger.setLevel(self.previous_level)
