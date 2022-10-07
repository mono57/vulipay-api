from importlib.resources import path

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include

urlpatterns = [] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
