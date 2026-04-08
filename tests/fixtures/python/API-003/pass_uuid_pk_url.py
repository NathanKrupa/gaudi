"""Fixture for API-003: Django URL pattern uses UUID identifier instead of int."""

from django.urls import path

from . import views

urlpatterns = [
    path("users/<uuid:pk>/", views.user_detail, name="user-detail"),
]
