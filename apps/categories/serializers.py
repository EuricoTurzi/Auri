from rest_framework import serializers

from apps.categories.models import Category


class CategorySerializer(serializers.ModelSerializer):
    """Serializer read-only para dados da categoria."""

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'color', 'icon', 'created_at']
        read_only_fields = fields


class CategoryCreateUpdateSerializer(serializers.Serializer):
    """Serializer para criação e atualização de categoria."""
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    color = serializers.CharField(max_length=7, required=False, allow_blank=True, allow_null=True)
    icon = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)

    def validate_name(self, value):
        return value.strip()
