import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from app.accounts.managers import *
from app.accounts.models import Account
from app.accounts.tests.factories import AccountFactory


class AccountManagerTestCase(TestCase):
    def setUp(self):
        pass

    def test_it_should_generate_account_number(self):
        number = AccountManager.generate_account_number()

        self.assertIsNotNone(number)
        self.assertIsInstance(number, str)
        self.assertTrue(number.isdigit())
        self.assertTrue(len(number), 16)

    def test_it_should_credit_master_account(self):
        AccountFactory.create_master_account()
        amount = 2000
        Account.objects.credit_master_account(amount)
        master_account = Account.objects.filter(
            is_master=True, intl_phone_number=settings.MASTER_INTL_PHONE_NUMBER
        ).first()

        self.assertEqual(master_account.balance, float(amount))

    @patch("app.accounts.managers.AccountManager.create")
    def test_it_should_create_master_account(self, mocked_create: MagicMock):
        AccountManager().create_master_account()
        mocked_create.assert_called_once_with(
            intl_phone_number=settings.MASTER_INTL_PHONE_NUMBER,
            phone_number=settings.MASTER_PHONE_NUMBER,
            is_master=True,
        )
