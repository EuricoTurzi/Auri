from django.urls import path

from apps.transactions import views

app_name = 'transactions'

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]
