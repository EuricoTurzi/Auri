from django.urls import path

from apps.transactions import views

app_name = "transactions"

urlpatterns = [
    path("transactions/", views.TransactionListView.as_view(), name="list"),
    path("transactions/create/", views.TransactionCreateView.as_view(), name="create"),
    path("transactions/<uuid:pk>/", views.TransactionDetailView.as_view(), name="detail"),
    path("transactions/<uuid:pk>/edit/", views.TransactionUpdateView.as_view(), name="update"),
    path("transactions/<uuid:pk>/delete/", views.TransactionDeleteView.as_view(), name="delete"),
]
