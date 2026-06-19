"""Included app URLConf with several routes and no health endpoint. It is
include()d by config/urls.py, so it is not the root and must NOT be flagged."""

from django.http import JsonResponse
from django.urls import path


def post_list(request):
    return JsonResponse([], safe=False)


def post_detail(request, pk):
    return JsonResponse({})


def comments(request, pk):
    return JsonResponse([], safe=False)


urlpatterns = [
    path("posts/", post_list),
    path("posts/<int:pk>/", post_detail),
    path("posts/<int:pk>/comments/", comments),
]
