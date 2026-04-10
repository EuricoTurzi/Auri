from django.db import models
from core.models import BaseModel


class ScheduledReport(BaseModel):
    FREQUENCY_CHOICES = [
        ("semanal", "Semanal"),
        ("quinzenal", "Quinzenal"),
        ("mensal", "Mensal"),
    ]
    FORMAT_CHOICES = [
        ("csv", "CSV"),
        ("xlsx", "Excel"),
        ("pdf", "PDF"),
    ]

    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="scheduled_reports",
    )
    name = models.CharField(max_length=150)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    export_format = models.CharField(max_length=5, choices=FORMAT_CHOICES)
    filters = models.JSONField(
        default=dict,
        help_text="Filtros configurados: {period_start, period_end, category_ids, type, card_ids}",
    )
    last_sent_at = models.DateTimeField(null=True, blank=True)
    next_send_at = models.DateTimeField()

    class Meta:
        ordering = ["next_send_at"]
        verbose_name = "Relatório Agendado"
        verbose_name_plural = "Relatórios Agendados"

    def __str__(self):
        return f"{self.name} - {self.frequency} ({self.export_format})"
