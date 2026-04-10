"""
Serializers DRF para o app reports.
"""
from rest_framework import serializers

from .models import ScheduledReport


class DashboardSerializer(serializers.Serializer):
    """Serializer de leitura para dados agregados do dashboard."""
    total_entradas = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_saidas = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    saldo = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    gastos_por_categoria = serializers.ListField(read_only=True)
    evolucao_temporal = serializers.ListField(read_only=True)
    gastos_por_cartao = serializers.ListField(read_only=True)


class DashboardFilterSerializer(serializers.Serializer):
    """Serializer para validação de query params do dashboard."""
    period_start = serializers.DateField(required=False, allow_null=True)
    period_end = serializers.DateField(required=False, allow_null=True)
    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    type = serializers.CharField(required=False, allow_blank=True)
    card_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )

    def validate_type(self, value):
        if value and value not in ("entrada", "saida"):
            raise serializers.ValidationError("Tipo inválido.")
        return value


class ScheduledReportSerializer(serializers.ModelSerializer):
    """Serializer de leitura para relatórios agendados."""

    class Meta:
        model = ScheduledReport
        fields = [
            "id",
            "name",
            "frequency",
            "export_format",
            "filters",
            "next_send_at",
            "last_sent_at",
            "created_at",
        ]
        read_only_fields = fields


class ScheduledReportCreateUpdateSerializer(serializers.Serializer):
    """Serializer de escrita para criação/atualização de relatórios agendados."""
    name = serializers.CharField(max_length=150)
    frequency = serializers.ChoiceField(choices=ScheduledReport.FREQUENCY_CHOICES)
    export_format = serializers.ChoiceField(choices=ScheduledReport.FORMAT_CHOICES)
    filters = serializers.JSONField(default=dict, required=False)
