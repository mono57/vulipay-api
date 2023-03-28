from django.contrib import admin
from django.http import HttpRequest


class AppModelAdmin(admin.ModelAdmin):
    def get_list_display(self, request: HttpRequest):
        list_display = self.model.get_list_display()
        return list_display
