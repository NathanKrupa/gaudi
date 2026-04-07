"""Fixture for DRF-SCALE-001: API view without throttle_classes."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet


class OrderViewSet(ModelViewSet):
    queryset = []
    permission_classes = [IsAuthenticated]
