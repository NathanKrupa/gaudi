"""Fixture for DRF-SEC-001: ViewSet without explicit permission_classes."""

from rest_framework.viewsets import ModelViewSet


class OrderViewSet(ModelViewSet):
    queryset = []
    throttle_classes = []
