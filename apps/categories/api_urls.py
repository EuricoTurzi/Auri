from django.urls import path

from apps.categories import api_views

urlpatterns = [
    path('', api_views.CategoryListCreateAPIView.as_view(), name='api_categories_list'),
    path('<uuid:pk>/', api_views.CategoryDetailAPIView.as_view(), name='api_categories_detail'),
]
