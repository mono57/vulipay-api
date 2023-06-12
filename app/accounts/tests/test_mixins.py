from django.test import TestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.mixins import ValidPINRequiredMixin
from app.accounts.permissions import IsAuthenticatedAccount
from app.accounts.tests.factories import AccountFactory
from app.core.tests import AppAPIRequestFactory, EmptyResponseView


class StackedPermissionsView(ValidPINRequiredMixin, EmptyResponseView):
    permission_classes = [IsAuthenticatedAccount]


class ValidPINRequiredMixinTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.account = AccountFactory.create()
        self.account.set_pin("3435")

        self.access_token = str(RefreshToken.for_user(self.account).access_token)

    def test_it_should_test_view_success(self):
        view = StackedPermissionsView.as_view()

        request = AppAPIRequestFactory().put("/1", {"pin": "3435"})
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.access_token}"

        response = view(request)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_it_should_raise_invalid_pin_error(self):
        view = StackedPermissionsView.as_view()

        request = AppAPIRequestFactory().put("/1", {"pin": "3242"})
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.access_token}"

        response = view(request)

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_it_should_raise_unauthorize_error(self):
        view = StackedPermissionsView.as_view()
        request = AppAPIRequestFactory().put("/1", {"pin": "3242"})

        response = view(request)

        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

    def test_it_should_raise_bad_request_error(self):
        view = StackedPermissionsView.as_view()

        request = AppAPIRequestFactory().put("/1")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.access_token}"

        response = view(request)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
