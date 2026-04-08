"""Fixture for API-003: Django URL pattern exposes auto-increment integer PK."""

from django.urls import path

from . import views

urlpatterns = [
    path("users/<int:pk>/", views.user_detail, name="user-detail"),
]
