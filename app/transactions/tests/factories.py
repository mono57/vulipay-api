import random

import factory
from factory import Faker as faker
from factory import django

from app.accounts.tests.factories import (
    AccountFactory,
    AvailableCountryFactory,
    PhoneNumberFactory,
    UserFactory,
)
from app.core.utils import make_payment_code, make_transaction_ref
from app.transactions.models import (
    PaymentMethod,
    PaymentMethodType,
    Transaction,
    TransactionFee,
    TransactionStatus,
    TransactionType,
    Wallet,
    WalletType,
)


class TransactionFactory(django.DjangoModelFactory):
    class Meta:
        model = Transaction

    amount = 2000

    @classmethod
    def create(cls, **kwargs):
        transaction_ref = make_transaction_ref(kwargs.get("type"))
        t_payment_code = make_payment_code(transaction_ref, kwargs.get("type"))

        return super().create(
            reference=transaction_ref, payment_code=t_payment_code, **kwargs
        )

    @classmethod
    def create_p2p_transaction(cls, receiver_account, **kwargs):
        status = kwargs.pop("status", TransactionStatus.INITIATED)

        return cls.create(
            status=status,
            receiver_account=receiver_account,
            **kwargs,
            type=TransactionType.P2P,
        )

    @classmethod
    def create_pending_transaction(cls, receiver_account, payer_account, **kwargs):
        return cls.create(
            status=TransactionStatus.PENDING,
            type=TransactionType.P2P,
            receiver_account=receiver_account,
            payer_account=payer_account,
            amount=2000,
            calculated_fee=40,
            charged_amount=2040,
            **kwargs,
        )


class TransactionFeeFactory(django.DjangoModelFactory):
    class Meta:
        model = TransactionFee

    fee = 2
    country = factory.SubFactory(AvailableCountryFactory)

    @classmethod
    def create_p2p_transaction_fee(cls, **kwargs):
        return cls.create(**kwargs, transaction_type=TransactionType.P2P)

    @classmethod
    def create_co_transaction_fee(cls, **kwargs):
        return cls.create(**kwargs, transaction_type=TransactionType.CashOut)

    @classmethod
    def create_ci_transaction_fee(cls, **kwargs):
        return cls.create(**kwargs, transaction_type=TransactionType.CashIn)


class PaymentMethodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentMethod

    user = factory.SubFactory(UserFactory)
    type = "card"
    default_method = False

    cardholder_name = factory.Faker("name")
    masked_card_number = factory.LazyAttribute(
        lambda _: f"**** **** **** {random.randint(1000, 9999)}"
    )
    expiry_date = factory.LazyAttribute(
        lambda _: f"{random.randint(1, 12):02d}/{random.randint(2025, 2030)}"
    )
    cvv_hash = factory.Faker("sha256")
    billing_address = factory.Faker("address")

    @factory.post_generation
    def make_mobile_money(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.type = "mobile_money"
            self.cardholder_name = None
            self.masked_card_number = None
            self.expiry_date = None
            self.cvv_hash = None
            self.billing_address = None

            self.provider = "MTN Mobile Money"
            self.mobile_number = f"+{random.randint(10000000000, 99999999999)}"
            self.account_name = "Test User"


class WalletFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Wallet

    user = factory.SubFactory(UserFactory)
    balance = factory.LazyAttribute(lambda _: random.randint(1000, 10000))
    wallet_type = WalletType.MAIN
    is_active = True

    @classmethod
    def create_main_wallet(cls, **kwargs):
        return cls.create(wallet_type=WalletType.MAIN, **kwargs)

    @classmethod
    def create_business_wallet(cls, **kwargs):
        return cls.create(wallet_type=WalletType.BUSINESS, **kwargs)


class PaymentMethodTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentMethodType

    name = factory.Faker("word")
    code = factory.LazyAttribute(lambda o: o.name.upper())
    cash_in_transaction_fee = factory.LazyAttribute(
        lambda _: round(random.uniform(0.5, 5.0), 2)
    )
    cash_out_transaction_fee = factory.LazyAttribute(
        lambda _: round(random.uniform(0.5, 5.0), 2)
    )
    country = factory.SubFactory(AvailableCountryFactory)

    @classmethod
    def create_card_payment_method_type(cls, **kwargs):
        name = kwargs.pop("name", "Visa")
        code = kwargs.pop("code", f"CARD_{name.upper()}")
        return cls.create(name=name, code=code, **kwargs)

    @classmethod
    def create_mobile_money_payment_method_type(cls, **kwargs):
        name = kwargs.pop("name", "MTN Mobile Money")
        code = kwargs.pop("code", f'MOBILE_{name.upper().replace(" ", "_")}')
        return cls.create(name=name, code=code, **kwargs)
