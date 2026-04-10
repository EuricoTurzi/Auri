from django.urls import path

from apps.reports import views

app_name = "reports"

urlpatterns = [
    path("reports/", views.DashboardView.as_view(), name="dashboard"),
    path("reports/export/<str:format>/", views.ExportView.as_view(), name="export"),
    path("reports/scheduled/", views.ScheduledReportListView.as_view(), name="scheduled_list"),
    path("reports/scheduled/create/", views.ScheduledReportCreateView.as_view(), name="scheduled_create"),
    path("reports/scheduled/<uuid:pk>/delete/", views.ScheduledReportDeleteView.as_view(), name="scheduled_delete"),
]
