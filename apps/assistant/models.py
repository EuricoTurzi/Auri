from django.db import models

from core.models import BaseModel


class AssistantInteraction(BaseModel):
    INPUT_TYPE_CHOICES = [("texto", "Texto"), ("audio", "Áudio")]
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("confirmado", "Confirmado"),
        ("cancelado", "Cancelado"),
    ]

    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="assistant_interactions",
    )
    input_type = models.CharField(max_length=10, choices=INPUT_TYPE_CHOICES)
    input_content = models.TextField(
        help_text="Texto digitado pelo usuário ou transcrição do áudio"
    )
    llm_response = models.JSONField(
        default=dict,
        help_text="Dados extraídos pela LLM: {name, amount, type, category, date, description, card}",
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="pendente"
    )
    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assistant_interactions",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Interação do Assistente"
        verbose_name_plural = "Interações do Assistente"

    def __str__(self):
        return f"{self.user.email} - {self.input_type} - {self.status}"
