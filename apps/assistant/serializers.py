"""
Serializers DRF para o app assistant.
"""
from rest_framework import serializers

from .models import AssistantInteraction


class AssistantInteractionSerializer(serializers.ModelSerializer):
    """Serializer de leitura completa para interações do assistente."""

    transaction = serializers.UUIDField(source="transaction.id", read_only=True, allow_null=True)

    class Meta:
        model = AssistantInteraction
        fields = [
            "id",
            "input_type",
            "input_content",
            "llm_response",
            "status",
            "transaction",
            "created_at",
        ]
        read_only_fields = fields


class TextInputSerializer(serializers.Serializer):
    """Serializer para input de texto via API."""

    message = serializers.CharField()


class AudioInputSerializer(serializers.Serializer):
    """Serializer para upload de áudio via API."""

    audio = serializers.FileField()


class ConfirmSerializer(serializers.Serializer):
    """Serializer para confirmação de interação com ajustes opcionais."""

    adjusted_data = serializers.JSONField(required=False, allow_null=True)


class _CategoryPreviewSerializer(serializers.Serializer):
    """Serializer inline de leitura para categoria no preview."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class _CardPreviewSerializer(serializers.Serializer):
    """Serializer inline de leitura para cartão no preview (nullable)."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class TransactionPreviewSerializer(serializers.Serializer):
    """Serializer de leitura para exibir o preview dos dados extraídos pela LLM."""

    name = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    type = serializers.CharField(read_only=True)
    category = _CategoryPreviewSerializer(read_only=True)
    date = serializers.DateField(read_only=True)
    description = serializers.CharField(read_only=True, allow_null=True, required=False)
    card = _CardPreviewSerializer(read_only=True, allow_null=True, required=False)
    missing_fields = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
