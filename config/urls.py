from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.generic.base import View
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework import permissions


class Index(View):
    response = {"api_version": "2.0.0", "project": "vulipay", "author": "Amono Aymar"}

    def get(self, request, *args, **kwargs):
        return JsonResponse(self.response)


urlpatterns = [
    path("", Index.as_view()),
    path("api/v1/", include("app.core.apiv1_urls", namespace="api")),
    path("admin/", admin.site.urls),
    # OpenAPI 3 documentation with drf-spectacular
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
