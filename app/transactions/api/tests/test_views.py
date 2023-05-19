import json

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status

from app.accounts.models import Account
from app.transactions.models import Transaction
from app.transactions.api.views import P2PTransactionCreateAPIView
from app.core.utils import APIViewTestCase
from app.accounts.tests import factories as f

class P2PTransactionCreateAPIViewTestCase(APIViewTestCase):
    view_name = 'api:transactions_p2p_transactions'

    def setUp(self):
        super().setUp()

        self.account: Account = f.AccountFactory.create()
        self.access_token = str(RefreshToken.for_user(self.account).access_token)

    def test_it_should_not_create_transation_for_unauthorized_user(self):
        response = self.view_post({})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_create_P2P_transaction(self):
        self.authenticate_with_jwttoken(self.access_token)

        payload = {'amount': 2000}

        response = self.view_post(payload)
        data = response.data

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('payment_code', data)
        self.assertIsNotNone(data.get('payment_code'))

        transaction = Transaction.objects.filter(payment_code=data.get('payment_code')).first()

        self.assertEqual(transaction.amount, float(payload.get('amount')))

    def test_it_should_not_create_transaction_for_wrong_amount(self):
        self.authenticate_with_jwttoken(self.access_token)

        payload = {'amount': -2000}
        response = self.view_post(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payload['amount'] = 0
        response = self.view_post(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TransactionDetailsRetrieveAPIView(APIViewTestCase):
    view_name = 'api:transactions_transaction_details'

    def setUp(self):
        super().setUp()
        self.receiver_account = f.AccountFactory.create()
        self.transaction = Transaction.create_P2P_transaction(2000, self.receiver_account)
        self.payment_code = self.transaction.payment_code
        self.access_token = str(RefreshToken.for_user(self.receiver_account).access_token)

    def test_it_should_not_get_details_for_unauthorized_account(self):
        response = self.view_get(reverse_kwargs={'payment_code': self.payment_code})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_it_should_raise_invalid_vulipay_payment_code(self):
        self.authenticate_with_jwttoken(self.access_token)

        response = self.view_get(reverse_kwargs={'payment_code': 'vulipay$SE2$SDFG34GE3G4234G42345G4F3ERF34G543FD3F4G54F'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_it_should_get_transaction_details(self):
        self.authenticate_with_jwttoken(self.access_token)

        response = self.view_get(reverse_kwargs={'payment_code': self.payment_code})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
