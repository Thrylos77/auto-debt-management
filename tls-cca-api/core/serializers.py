"""Serializers for core-level API responses."""

from rest_framework import serializers


class GlobalSearchItemSerializer(serializers.Serializer):
    """Represent one item returned by the federated global search."""

    id = serializers.IntegerField()
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True, allow_null=True)
    type = serializers.CharField()
    status = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    url = serializers.CharField()


class GlobalSearchResponseSerializer(serializers.Serializer):
    """Represent the grouped result payload returned by global search."""

    sales = GlobalSearchItemSerializer(many=True)
    debts = GlobalSearchItemSerializer(many=True)
    customers = GlobalSearchItemSerializer(many=True)
