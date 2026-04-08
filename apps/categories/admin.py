from django.contrib import admin

from apps.categories.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin para Category."""
    list_display = ('name', 'user', 'color', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
