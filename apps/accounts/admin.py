from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin para CustomUser com campos customizados."""
    list_display = ('email', 'nickname', 'is_first_access', 'is_active', 'is_staff', 'created_at')
    list_filter = ('is_active', 'is_first_access', 'is_staff')
    search_fields = ('email', 'nickname')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'nickname', 'password')}),
        ('Informações pessoais', {'fields': ('phone_number',)}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_first_access', 'groups', 'user_permissions')}),
        ('Datas', {'fields': ('id', 'created_at', 'updated_at', 'last_login')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nickname', 'password1', 'password2'),
        }),
    )
