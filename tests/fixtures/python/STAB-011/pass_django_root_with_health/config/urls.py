"""Root URLConf with a /health endpoint -- STAB-011 is satisfied."""

from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check),
    path("blog/", include("blog.urls")),
]
