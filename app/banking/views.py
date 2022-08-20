from django.shortcuts import render

from rest_framework.generics import CreateAPIView

from banking.models import Transaction
from banking.api.serializers import PerformPaymentSerializer


class PerformPaymentAPIView(CreateAPIView):
    pass