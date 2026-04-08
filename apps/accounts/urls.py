from django.urls import path

from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    path('accounts/login/', views.LoginView.as_view(), name='login'),
    path('accounts/register/', views.RegisterView.as_view(), name='register'),
    path('accounts/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('accounts/logout/', views.LogoutView.as_view(), name='logout'),
]
