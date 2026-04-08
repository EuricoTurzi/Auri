from django.urls import path

from apps.categories import views

app_name = 'categories'

urlpatterns = [
    path('categories/', views.CategoryListView.as_view(), name='list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='create'),
    path('categories/<uuid:pk>/edit/', views.CategoryUpdateView.as_view(), name='edit'),
    path('categories/<uuid:pk>/delete/', views.CategoryDeleteView.as_view(), name='delete'),
]
