from django.contrib import admin

from .models import AssistantInteraction


@admin.register(AssistantInteraction)
class AssistantInteractionAdmin(admin.ModelAdmin):
    list_display = ["user", "input_type", "status", "transaction", "created_at"]
    list_filter = ["input_type", "status", "created_at"]
    search_fields = ["user__email", "input_content"]
    readonly_fields = ["id", "created_at", "updated_at", "llm_response"]
