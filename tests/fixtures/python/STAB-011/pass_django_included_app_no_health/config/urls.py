"""Root URLConf (no ROOT_URLCONF setting) -- identified as root because no
other URLConf includes it. Carries /ping, so STAB-011 is satisfied."""

from django.http import JsonResponse
from django.urls import include, path


def ping(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("ping/", ping),
    path("blog/", include("blog.urls")),
]
