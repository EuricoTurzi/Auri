"""
Serializers DRF para o app transactions.
"""
from rest_framework import serializers

from .models import Installment, Transaction


class _CategoryNestedSerializer(serializers.Serializer):
    """Serializer inline de leitura para categoria aninhada."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class _CardNestedSerializer(serializers.Serializer):
    """Serializer inline de leitura para cartão aninhado."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer de leitura completa para transações."""

    category = _CategoryNestedSerializer(read_only=True)
    card = _CardNestedSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "name",
            "description",
            "amount",
            "type",
            "status",
            "category",
            "card",
            "date",
            "due_date",
            "is_recurring",
            "is_installment",
            "created_at",
        ]
        read_only_fields = fields


class TransactionCreateSerializer(serializers.Serializer):
    """Serializer de criação de transação com validação de entrada."""

    TYPE_CHOICES = ["entrada", "saida"]
    STATUS_CHOICES = ["pendente", "pago"]

    name = serializers.CharField(max_length=150)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    type = serializers.CharField(max_length=10)
    category_id = serializers.UUIDField(write_only=True)
    card_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    date = serializers.DateField()
    due_date = serializers.DateField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.CharField(max_length=10, default="pendente")

    def validate_type(self, value):
        """Valida que o tipo é 'entrada' ou 'saida'."""
        if value not in self.TYPE_CHOICES:
            raise serializers.ValidationError(
                f"Tipo inválido. Escolha entre: {', '.join(self.TYPE_CHOICES)}."
            )
        return value

    def validate_amount(self, value):
        """Valida que o valor é maior que zero."""
        if value <= 0:
            raise serializers.ValidationError("O valor deve ser maior que zero.")
        return value

    def validate_status(self, value):
        """Valida que o status é 'pendente' ou 'pago'."""
        if value not in self.STATUS_CHOICES:
            raise serializers.ValidationError(
                f"Status inválido. Escolha entre: {', '.join(self.STATUS_CHOICES)}."
            )
        return value


class RecurringTransactionCreateSerializer(TransactionCreateSerializer):
    """Serializer de criação de transação recorrente."""

    FREQUENCY_CHOICES = ["semanal", "quinzenal", "mensal"]

    frequency = serializers.CharField(max_length=10)

    def validate_frequency(self, value):
        """Valida que a frequência é uma das opções disponíveis."""
        if value not in self.FREQUENCY_CHOICES:
            raise serializers.ValidationError(
                f"Frequência inválida. Escolha entre: {', '.join(self.FREQUENCY_CHOICES)}."
            )
        return value


class InstallmentTransactionCreateSerializer(TransactionCreateSerializer):
    """Serializer de criação de transação parcelada."""

    total_installments = serializers.IntegerField(min_value=2)


class InstallmentSerializer(serializers.ModelSerializer):
    """Serializer de leitura para parcelas."""

    class Meta:
        model = Installment
        fields = [
            "id",
            "installment_number",
            "total_installments",
            "amount",
            "status",
            "due_date",
        ]
        read_only_fields = fields


class TransactionFilterSerializer(serializers.Serializer):
    """Serializer para validação de parâmetros de filtro em requisições GET."""

    type = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    card_id = serializers.UUIDField(required=False, allow_null=True)
    date_start = serializers.DateField(required=False, allow_null=True)
    date_end = serializers.DateField(required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_blank=True)
