from django.contrib import admin

from apps.transactions.models import Installment, RecurringConfig, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin para Transaction."""
    list_display = ('name', 'user', 'amount', 'type', 'status', 'category', 'date')
    list_filter = ('type', 'status', 'is_recurring', 'is_installment')
    search_fields = ('name', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(RecurringConfig)
class RecurringConfigAdmin(admin.ModelAdmin):
    """Admin para RecurringConfig."""
    list_display = ('transaction', 'frequency', 'created_at')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    """Admin para Installment."""
    list_display = ('parent_transaction', 'installment_number', 'total_installments', 'amount', 'status', 'due_date')
    list_filter = ('status',)
    readonly_fields = ('id', 'created_at', 'updated_at')
