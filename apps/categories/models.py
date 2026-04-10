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
        constraints = [
            # Unicidade de nome por usuário aplica-se apenas a categorias ativas,
            # permitindo recriar um nome após soft-delete.
            models.UniqueConstraint(
                fields=['user', 'name'],
                condition=models.Q(is_active=True),
                name='unique_category_name_per_user_active',
            ),
        ]
        ordering = ['name']
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return self.name
