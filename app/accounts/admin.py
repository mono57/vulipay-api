from django.contrib import admin
from accounts.models import *

class UserModelAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'email')

