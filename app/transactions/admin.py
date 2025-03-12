from django.contrib import admin

from app.transactions.models import PaymentMethod, Transaction, TransactionFee, Wallet

# Register your models here.
admin.site.register(Transaction)
admin.site.register(TransactionFee)
admin.site.register(PaymentMethod)
admin.site.register(Wallet)
