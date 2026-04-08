"""Fixture for DJ-ARCH-001: serializer create() carrying business logic."""

from rest_framework import serializers


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = object
        fields = "__all__"

    def create(self, validated_data):
        user = validated_data["user"]
        items = validated_data["items"]
        total = 0
        for item in items:
            price = item["price"] * item["qty"]
            total += price
        discount = total * 0.1 if user.is_premium else 0
        total -= discount
        order = object()
        order.user = user
        order.total = total
        order.save()
        return order
