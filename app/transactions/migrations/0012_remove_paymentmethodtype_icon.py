# Generated by Django 5.1.6 on 2025-05-19 23:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0011_paymentmethodtype_icon_paymentmethodtype_logo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentmethodtype',
            name='icon',
        ),
    ]
