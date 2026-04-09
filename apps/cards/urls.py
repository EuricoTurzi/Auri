"""
URLs do app cards.
"""
from django.urls import path

from . import views

app_name = "cards"

urlpatterns = [
    path("cards/", views.CardListView.as_view(), name="list"),
    path("cards/create/", views.CardCreateView.as_view(), name="create"),
    path("cards/<uuid:pk>/", views.CardDetailView.as_view(), name="detail"),
    path("cards/<uuid:pk>/edit/", views.CardUpdateView.as_view(), name="edit"),
    path("cards/<uuid:pk>/delete/", views.CardDeleteView.as_view(), name="delete"),
]
