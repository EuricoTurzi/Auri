from django.db import models

from core.models import BaseModel


class Card(BaseModel):
    """Cartão de crédito ou débito do usuário."""

    CARD_TYPE_CHOICES = [("credito", "Crédito"), ("debito", "Débito")]

    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="cards",
    )
    name = models.CharField(max_length=100, verbose_name="Nome")
    brand = models.CharField(max_length=50, verbose_name="Bandeira")  # Visa, Mastercard, Elo, etc.
    last_four_digits = models.CharField(max_length=4, verbose_name="Últimos 4 dígitos")
    card_type = models.CharField(
        max_length=10,
        choices=CARD_TYPE_CHOICES,
        verbose_name="Tipo de cartão",
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Limite de crédito",
    )
    billing_close_day = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Dia de fechamento da fatura",
    )  # 1-31
    billing_due_day = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Dia de vencimento da fatura",
    )  # 1-31

    class Meta:
        ordering = ["name"]
        verbose_name = "Cartão"
        verbose_name_plural = "Cartões"

    def __str__(self):
        return f"{self.name} (****{self.last_four_digits})"
