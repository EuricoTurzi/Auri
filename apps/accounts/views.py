from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.accounts.forms import ChangePasswordForm, LoginForm, RegisterForm
from apps.accounts.services import change_first_access_password, register_user


def _google_enabled():
    return bool(getattr(settings, "GOOGLE_CLIENT_ID", ""))


class LoginView(View):
    """View de login com e-mail e senha."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('transactions:list')
        form = LoginForm()
        return render(request, 'accounts/login.html', {'form': form, 'google_enabled': _google_enabled()})

    def post(self, request):
        form = LoginForm(request.POST)
        ctx = {'form': form, 'google_enabled': _google_enabled()}
        if not form.is_valid():
            return render(request, 'accounts/login.html', ctx)

        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request, 'E-mail ou senha inválidos.')
            return render(request, 'accounts/login.html', ctx)

        if not user.is_active:
            messages.error(request, 'Conta desativada.')
            return render(request, 'accounts/login.html', ctx)

        login(request, user)
        return redirect('transactions:list')


class RegisterView(View):
    """View de registro de novo usuário."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('transactions:list')
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if not form.is_valid():
            return render(request, 'accounts/register.html', {'form': form})

        try:
            register_user(
                email=form.cleaned_data['email'],
                nickname=form.cleaned_data['nickname'],
            )
            messages.success(
                request,
                'Conta criada! Verifique seu e-mail para obter a senha temporária.',
            )
            return redirect('accounts:login')
        except Exception as e:
            messages.error(request, str(e))
            return render(request, 'accounts/register.html', {'form': form})


class ChangePasswordView(LoginRequiredMixin, View):
    """View de troca de senha obrigatória no primeiro acesso."""

    def get(self, request):
        form = ChangePasswordForm()
        return render(request, 'accounts/change_password.html', {'form': form})

    def post(self, request):
        form = ChangePasswordForm(request.POST)
        if not form.is_valid():
            return render(request, 'accounts/change_password.html', {'form': form})

        try:
            user = change_first_access_password(
                user=request.user,
                new_password=form.cleaned_data['new_password'],
            )
            update_session_auth_hash(request, user)
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('transactions:list')
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, 'accounts/change_password.html', {'form': form})


class LogoutView(View):
    """View de logout."""

    def post(self, request):
        logout(request)
        return redirect('accounts:login')
