"""Fixture for DRF-SEC-001: ViewSet declares its permission policy."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet


class OrderViewSet(ModelViewSet):
    queryset = []
    permission_classes = [IsAuthenticated]
    throttle_classes = []
