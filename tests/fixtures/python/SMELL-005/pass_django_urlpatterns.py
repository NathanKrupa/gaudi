"""Fixture for SMELL-005: Django urlpatterns is a module-level list by design."""

from django.urls import path

urlpatterns = [
    path("home/", lambda r: None, name="home"),
    path("about/", lambda r: None, name="about"),
]
