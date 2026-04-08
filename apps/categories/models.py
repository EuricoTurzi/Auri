from django.db import models

from core.models import BaseModel


class Category(BaseModel):
    """Classificação configurável de transações por usuário."""
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='categories',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=7, null=True, blank=True)  # hex: #FF5733
    icon = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        unique_together = [('user', 'name')]
        ordering = ['name']
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return self.name
