"""Included app URLConf -- correctly has no health endpoint, must NOT be flagged."""

from django.http import JsonResponse
from django.urls import path


def post_list(request):
    return JsonResponse([], safe=False)


def post_detail(request, pk):
    return JsonResponse({})


urlpatterns = [
    path("posts/", post_list),
    path("posts/<int:pk>/", post_detail),
]
