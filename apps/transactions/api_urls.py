"""
URLs da API REST para o app transactions.
"""
from django.urls import path

from apps.transactions import api_views

urlpatterns = [
    path("", api_views.TransactionListCreateAPIView.as_view(), name="api_transactions_list"),
    path("recurring/", api_views.RecurringTransactionCreateAPIView.as_view(), name="api_transactions_recurring_create"),
    path("recurring/<uuid:pk>/", api_views.RecurringTransactionDeleteAPIView.as_view(), name="api_transactions_recurring_delete"),
    path("installment/", api_views.InstallmentTransactionCreateAPIView.as_view(), name="api_transactions_installment_create"),
    path("<uuid:pk>/", api_views.TransactionDetailAPIView.as_view(), name="api_transactions_detail"),
    path("<uuid:pk>/installments/", api_views.InstallmentListAPIView.as_view(), name="api_transactions_installments"),
    path("<uuid:pk>/status/", api_views.TransactionStatusUpdateAPIView.as_view(), name="api_transactions_status"),
]
