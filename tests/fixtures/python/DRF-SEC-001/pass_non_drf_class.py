"""Fixture for DRF-SEC-001: a plain class in a DRF-aware module is out of scope."""

from rest_framework.viewsets import ModelViewSet


class OrderHelper:
    queryset = []


_ = ModelViewSet  # silence unused import
