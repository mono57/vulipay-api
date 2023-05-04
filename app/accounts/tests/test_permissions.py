from django.test import TestCase
from django.contrib.auth.models import AnonymousUser

from rest_framework.test import APIRequestFactory

from app.accounts.permissions import IsAuthenticatedAccount
from app.accounts.models import Account

class IsAuthenticatedAccountTestCase(TestCase):
    def setUp(self):
        self.request = APIRequestFactory().get('/1', format="json")
        self.permission = IsAuthenticatedAccount

    def test_it_should_return_false_on_has_perm(self):
        self.request.user = AnonymousUser()

        self.assertFalse(self.permission().has_permission(self.request, None))

    def test_should_return_true_on_has_perm(self):
        account = Account.objects.create()
        self.request.user = account
        self.assertTrue(self.permission().has_permission(self.request, None))
