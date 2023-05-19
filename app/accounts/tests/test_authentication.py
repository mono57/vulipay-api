from django.test import TestCase
from django.conf import settings

from rest_framework_simplejwt.exceptions import AuthenticationFailed

from app.accounts.authentication import AppJWTAuthentication
from app.accounts.models import Account
from app.accounts.tests import factories as f

class AppJWTAuthenticationTestCase(TestCase):
    def setUp(self):
        self.backend = AppJWTAuthentication()

    def test_it_should_have_account_as_user_class(self):
        self.assertIsInstance(self.backend.user_model(), Account)

    def test_it_get_user(self):
        payload = { settings.SIMPLE_JWT['USER_ID_CLAIM']: 100 }

        with self.assertRaises(AuthenticationFailed) as ex:
            self.backend.get_user(payload)

        # self.assertEqual(ex.exception.default_code, "account_not_found")

        account = f.AccountFactory.create()
        payload[settings.SIMPLE_JWT['USER_ID_CLAIM']] = getattr(account, settings.SIMPLE_JWT['USER_ID_FIELD'])

        self.assertEqual(self.backend.get_user(payload).id, account.id)

        account.is_active = False
        account.save()

        payload[settings.SIMPLE_JWT['USER_ID_CLAIM']] = getattr(account, settings.SIMPLE_JWT['USER_ID_FIELD'])

        with self.assertRaises(AuthenticationFailed) as ex:
            self.backend.get_user(payload)

        # self.assertEqual(ex.exception.default_code, "account_inactive")
