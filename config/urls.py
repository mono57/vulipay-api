from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic.base import View
from django.http import JsonResponse

class Index(View):
    response = {
        'api_version': '2.0.0',
        'project': 'vulipay',
        'author': 'Amono Aymar'
    }
    def get(self, request, *args, **kwargs):
        return JsonResponse(self.response)

urlpatterns = [
    path('', Index.as_view()),
    path('api/', include('app.core.apiv1_urls', namespace='api')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
