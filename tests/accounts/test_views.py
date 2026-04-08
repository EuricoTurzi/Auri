import pytest
from unittest.mock import patch

from django.test import Client
from django.urls import reverse

from apps.accounts.models import CustomUser


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user_with_first_access():
    """Cria usuário com is_first_access=True."""
    user = CustomUser.objects.create_user(
        email='first@test.com',
        nickname='firstuser',
        password='temppass123',
    )
    return user


@pytest.fixture
def user_normal():
    """Cria usuário com is_first_access=False (já trocou senha)."""
    user = CustomUser.objects.create_user(
        email='normal@test.com',
        nickname='normaluser',
        password='normalpass123',
    )
    user.is_first_access = False
    user.save()
    return user


class TestLoginView:
    def test_get_login_page(self, client):
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 200

    def test_login_com_credenciais_validas(self, client, user_normal):
        response = client.post(reverse('accounts:login'), {
            'email': 'normal@test.com',
            'password': 'normalpass123',
        })
        assert response.status_code == 302

    def test_login_com_senha_errada(self, client, user_normal):
        response = client.post(reverse('accounts:login'), {
            'email': 'normal@test.com',
            'password': 'errada',
        })
        assert response.status_code == 200  # Fica na página com erro

    def test_login_usuario_desativado(self, client):
        user = CustomUser.objects.create_user(
            email='inactive@test.com',
            nickname='inactiveuser',
            password='pass12345',
        )
        user.is_active = False
        user.save()

        response = client.post(reverse('accounts:login'), {
            'email': 'inactive@test.com',
            'password': 'pass12345',
        })
        assert response.status_code == 200  # Login negado

    def test_usuario_autenticado_redireciona(self, client, user_normal):
        client.force_login(user_normal)
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 302


class TestRegisterView:
    def test_get_register_page(self, client):
        response = client.get(reverse('accounts:register'))
        assert response.status_code == 200

    @patch('apps.accounts.services.send_mail')
    def test_registro_com_dados_validos(self, mock_mail, client):
        response = client.post(reverse('accounts:register'), {
            'nickname': 'novousuario',
            'email': 'novo@test.com',
        })
        assert response.status_code == 302
        assert response.url == reverse('accounts:login')
        assert CustomUser.objects.filter(email='novo@test.com').exists()

    @patch('apps.accounts.services.send_mail')
    def test_registro_email_duplicado(self, mock_mail, client, user_normal):
        response = client.post(reverse('accounts:register'), {
            'nickname': 'outro',
            'email': 'normal@test.com',  # Já existe
        })
        assert response.status_code == 200  # Fica na página com erro

    def test_usuario_autenticado_redireciona(self, client, user_normal):
        client.force_login(user_normal)
        response = client.get(reverse('accounts:register'))
        assert response.status_code == 302


class TestChangePasswordView:
    def test_get_change_password_requer_login(self, client):
        response = client.get(reverse('accounts:change_password'))
        assert response.status_code == 302  # Redirect para login

    def test_get_change_password_autenticado(self, client, user_with_first_access):
        client.force_login(user_with_first_access)
        response = client.get(reverse('accounts:change_password'))
        assert response.status_code == 200

    def test_troca_senha_com_sucesso(self, client, user_with_first_access):
        client.force_login(user_with_first_access)
        response = client.post(reverse('accounts:change_password'), {
            'new_password': 'novasenha123',
            'confirm_password': 'novasenha123',
        })
        assert response.status_code == 302

        user_with_first_access.refresh_from_db()
        assert user_with_first_access.is_first_access is False

    def test_senhas_nao_coincidem(self, client, user_with_first_access):
        client.force_login(user_with_first_access)
        response = client.post(reverse('accounts:change_password'), {
            'new_password': 'novasenha123',
            'confirm_password': 'diferente123',
        })
        assert response.status_code == 200  # Fica na página com erro


class TestLogoutView:
    def test_logout(self, client, user_normal):
        client.force_login(user_normal)
        response = client.post(reverse('accounts:logout'))
        assert response.status_code == 302
        assert response.url == reverse('accounts:login')


class TestFirstAccessMiddleware:
    def test_redireciona_primeiro_acesso(self, client, user_with_first_access):
        client.force_login(user_with_first_access)
        response = client.get('/')
        assert response.status_code == 302
        assert reverse('accounts:change_password') in response.url

    def test_permite_change_password_no_primeiro_acesso(self, client, user_with_first_access):
        client.force_login(user_with_first_access)
        response = client.get(reverse('accounts:change_password'))
        assert response.status_code == 200

    def test_usuario_normal_nao_redireciona(self, client, user_normal):
        client.force_login(user_normal)
        response = client.get('/')
        assert response.status_code == 200  # Landing page, sem redirect
