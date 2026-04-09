"""
Serializers DRF para o app cards.
"""
from rest_framework import serializers

from .models import Card
from .selectors import get_available_limit


class CardSerializer(serializers.ModelSerializer):
    """Serializer de leitura completa para dados do cartão."""

    available_limit = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = [
            "id",
            "name",
            "brand",
            "last_four_digits",
            "card_type",
            "credit_limit",
            "billing_close_day",
            "billing_due_day",
            "available_limit",
            "created_at",
        ]
        read_only_fields = fields

    def get_available_limit(self, obj):
        """Retorna o limite disponível calculado via selector."""
        return get_available_limit(obj)


class CardCreateUpdateSerializer(serializers.Serializer):
    """Serializer para criação e atualização de cartão com validação de entrada."""

    CARD_TYPE_CHOICES = [choice[0] for choice in Card.CARD_TYPE_CHOICES]

    name = serializers.CharField(max_length=100)
    brand = serializers.CharField(max_length=50)
    last_four_digits = serializers.CharField(max_length=4)
    card_type = serializers.CharField(max_length=10)
    credit_limit = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    billing_close_day = serializers.IntegerField(required=False, allow_null=True)
    billing_due_day = serializers.IntegerField(required=False, allow_null=True)

    def validate_last_four_digits(self, value):
        """Valida que o campo contém exatamente 4 dígitos numéricos."""
        if not value.isdigit() or len(value) != 4:
            raise serializers.ValidationError(
                "Deve conter exatamente 4 dígitos numéricos."
            )
        return value

    def validate_card_type(self, value):
        """Valida que o tipo de cartão é 'credito' ou 'debito'."""
        if value not in self.CARD_TYPE_CHOICES:
            raise serializers.ValidationError(
                f"Tipo de cartão inválido. Escolha entre: {', '.join(self.CARD_TYPE_CHOICES)}."
            )
        return value
