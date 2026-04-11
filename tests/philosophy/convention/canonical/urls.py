"""
URL configuration for the Convention reference exemplar.

Empty by design — the canonical-task.md out-of-scope list excludes
an HTTP layer for every exemplar except Convention, and even here
the exemplar's tests exercise the models and manager methods
directly. A production Convention application would register the
admin and any DRF viewsets here via ``path("admin/", admin.site.urls)``
and ``router.urls``; we omit the URL surface because no test drives it.
"""

from django.urls import path

urlpatterns: list[path] = []
