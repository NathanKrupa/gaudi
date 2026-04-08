"""Fixture for DJ-ARCH-001: thin serializer that delegates to super().create()."""

from rest_framework import serializers


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = object
        fields = "__all__"

    def create(self, validated_data):
        return super().create(validated_data)
