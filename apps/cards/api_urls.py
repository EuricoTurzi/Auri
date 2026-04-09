"""
URLs da API REST para o app cards.
"""
from django.urls import path

from . import api_views

urlpatterns = [
    path("", api_views.CardListCreateAPIView.as_view(), name="api_cards_list"),
    path("<uuid:pk>/", api_views.CardDetailAPIView.as_view(), name="api_cards_detail"),
    path(
        "<uuid:pk>/transactions/",
        api_views.CardTransactionsAPIView.as_view(),
        name="api_cards_transactions",
    ),
]
