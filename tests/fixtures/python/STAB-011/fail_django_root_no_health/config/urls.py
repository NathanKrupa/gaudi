"""Root URLConf with routes but no health endpoint -- STAB-011 must flag this."""

from django.http import JsonResponse
from django.urls import include, path


def admin_site(request):
    return JsonResponse({})


urlpatterns = [
    path("admin/", admin_site),
    path("blog/", include("blog.urls")),
]
