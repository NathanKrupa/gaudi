"""Fixture for DRF-SCALE-001: ViewSet declares its throttle policy."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework.viewsets import ModelViewSet


class OrderViewSet(ModelViewSet):
    queryset = []
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
