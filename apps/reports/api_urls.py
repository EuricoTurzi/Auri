from django.urls import path

from apps.reports import api_views

urlpatterns = [
    path("dashboard/", api_views.DashboardAPIView.as_view(), name="api_dashboard"),
    path("export/<str:export_format>/", api_views.ExportAPIView.as_view(), name="api_export"),
    path("scheduled/", api_views.ScheduledReportListCreateAPIView.as_view(), name="api_scheduled_list"),
    path("scheduled/<uuid:pk>/", api_views.ScheduledReportDetailAPIView.as_view(), name="api_scheduled_detail"),
]
