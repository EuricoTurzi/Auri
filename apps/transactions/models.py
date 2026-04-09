from django.db import models
from core.models import BaseModel


class Transaction(BaseModel):
    TYPE_CHOICES = [("entrada", "Entrada"), ("saida", "Saída")]
    STATUS_CHOICES = [("pendente", "Pendente"), ("pago", "Pago")]

    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="transactions")
    name = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    category = models.ForeignKey("categories.Category", on_delete=models.PROTECT, related_name="transactions")
    card = models.ForeignKey("cards.Card", on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    is_recurring = models.BooleanField(default=False)
    is_installment = models.BooleanField(default=False)
    recurring_parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_children",
    )

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Transação"
        verbose_name_plural = "Transações"

    def __str__(self):
        return f"{self.name} - R${self.amount}"


class RecurringConfig(BaseModel):
    FREQUENCY_CHOICES = [("semanal", "Semanal"), ("quinzenal", "Quinzenal"), ("mensal", "Mensal")]

    transaction = models.OneToOneField("Transaction", on_delete=models.CASCADE, related_name="recurring_config")
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)

    class Meta:
        verbose_name = "Configuração de Recorrência"
        verbose_name_plural = "Configurações de Recorrência"

    def __str__(self):
        return f"{self.transaction.name} - {self.frequency}"


class Installment(BaseModel):
    STATUS_CHOICES = [("pendente", "Pendente"), ("pago", "Pago")]

    parent_transaction = models.ForeignKey("Transaction", on_delete=models.CASCADE, related_name="installments")
    installment_number = models.IntegerField()
    total_installments = models.IntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    due_date = models.DateField()

    class Meta:
        ordering = ["installment_number"]
        unique_together = [("parent_transaction", "installment_number")]
        verbose_name = "Parcela"
        verbose_name_plural = "Parcelas"

    def __str__(self):
        return f"{self.parent_transaction.name} - {self.installment_number}/{self.total_installments}"
