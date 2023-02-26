from django.test import TestCase

from accounts.tests.factories import *


class UserTestCase(TestCase):
    def setUp(self):
        self.user: User = UserFactory.create()
        return super().setUp()

    def test_should_create_user(self):
        self.assertTrue(self.user.first_name is not None)
        self.assertTrue(self.user.last_name is not None)
        self.assertTrue(self.user.email is not None)