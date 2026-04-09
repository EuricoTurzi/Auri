from django.contrib import admin

from apps.cards.models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    """Admin para Card."""
    list_display = ('name', 'user', 'brand', 'last_four_digits', 'card_type', 'credit_limit', 'is_active')
    list_filter = ('card_type', 'is_active', 'brand')
    search_fields = ('name', 'user__email', 'last_four_digits')
    readonly_fields = ('id', 'created_at', 'updated_at')
