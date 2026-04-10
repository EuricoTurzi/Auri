from django.contrib import admin

from apps.reports.models import ScheduledReport


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    """Admin para ScheduledReport."""
    list_display = ("name", "user", "frequency", "export_format", "next_send_at", "last_sent_at", "is_active")
    list_filter = ("frequency", "export_format", "is_active")
    search_fields = ("name", "user__email")
    readonly_fields = ("id", "created_at", "updated_at", "last_sent_at")
