import pytest
from unittest.mock import patch

from django.test import Client
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_first_access():
    user = CustomUser.objects.create_user(
        email='api@test.com',
        nickname='apiuser',
        password='temppass123',
    )
    return user


@pytest.fixture
def user_normal():
    user = CustomUser.objects.create_user(
        email='apinormal@test.com',
        nickname='apinormal',
        password='normalpass123',
    )
    user.is_first_access = False
    user.save()
    return user


class TestRegisterAPI:
    @patch('apps.accounts.services.send_mail')
    def test_registro_sucesso(self, mock_mail, api_client):
        response = api_client.post('/api/v1/accounts/register/', {
            'email': 'novo@api.com',
            'nickname': 'novoapi',
        })
        assert response.status_code == 201
        assert response.data['email'] == 'novo@api.com'
        assert 'password' not in response.data

    @patch('apps.accounts.services.send_mail')
    def test_registro_email_duplicado(self, mock_mail, api_client, user_normal):
        response = api_client.post('/api/v1/accounts/register/', {
            'email': 'apinormal@test.com',
            'nickname': 'outronick',
        })
        assert response.status_code == 400

    @patch('apps.accounts.services.send_mail')
    def test_registro_nickname_duplicado(self, mock_mail, api_client, user_normal):
        response = api_client.post('/api/v1/accounts/register/', {
            'email': 'outro@api.com',
            'nickname': 'apinormal',
        })
        assert response.status_code == 400


class TestLoginAPI:
    def test_login_sucesso(self, api_client, user_normal):
        response = api_client.post('/api/v1/accounts/login/', {
            'email': 'apinormal@test.com',
            'password': 'normalpass123',
        })
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['user']['email'] == 'apinormal@test.com'

    def test_login_senha_errada(self, api_client, user_normal):
        response = api_client.post('/api/v1/accounts/login/', {
            'email': 'apinormal@test.com',
            'password': 'errada',
        })
        assert response.status_code == 401

    def test_login_usuario_inexistente(self, api_client):
        response = api_client.post('/api/v1/accounts/login/', {
            'email': 'naoexiste@test.com',
            'password': 'qualquer',
        })
        assert response.status_code == 401


class TestChangePasswordAPI:
    def test_troca_senha_sucesso(self, api_client, user_first_access):
        api_client.force_authenticate(user=user_first_access)
        response = api_client.post('/api/v1/accounts/change-password/', {
            'new_password': 'novasenha123',
            'confirm_password': 'novasenha123',
        })
        assert response.status_code == 200

        user_first_access.refresh_from_db()
        assert user_first_access.is_first_access is False

    def test_senhas_nao_coincidem(self, api_client, user_first_access):
        api_client.force_authenticate(user=user_first_access)
        response = api_client.post('/api/v1/accounts/change-password/', {
            'new_password': 'novasenha123',
            'confirm_password': 'diferente123',
        })
        assert response.status_code == 400

    def test_senha_curta(self, api_client, user_first_access):
        api_client.force_authenticate(user=user_first_access)
        response = api_client.post('/api/v1/accounts/change-password/', {
            'new_password': '1234567',
            'confirm_password': '1234567',
        })
        assert response.status_code == 400

    def test_requer_autenticacao(self, api_client):
        response = api_client.post('/api/v1/accounts/change-password/', {
            'new_password': 'novasenha123',
            'confirm_password': 'novasenha123',
        })
        assert response.status_code == 401

    def test_erro_se_nao_primeiro_acesso(self, api_client, user_normal):
        api_client.force_authenticate(user=user_normal)
        response = api_client.post('/api/v1/accounts/change-password/', {
            'new_password': 'novasenha123',
            'confirm_password': 'novasenha123',
        })
        assert response.status_code == 400


class TestMeAPI:
    def test_me_autenticado(self, api_client, user_normal):
        api_client.force_authenticate(user=user_normal)
        response = api_client.get('/api/v1/accounts/me/')
        assert response.status_code == 200
        assert response.data['email'] == 'apinormal@test.com'
        assert response.data['nickname'] == 'apinormal'

    def test_me_nao_autenticado(self, api_client):
        response = api_client.get('/api/v1/accounts/me/')
        assert response.status_code == 401


class TestTokenRefresh:
    def test_refresh_token(self, api_client, user_normal):
        # Primeiro faz login para pegar tokens
        login_response = api_client.post('/api/v1/accounts/login/', {
            'email': 'apinormal@test.com',
            'password': 'normalpass123',
        })
        refresh_token = login_response.data['refresh']

        # Usa refresh para pegar novo access
        response = api_client.post('/api/v1/accounts/token/refresh/', {
            'refresh': refresh_token,
        })
        assert response.status_code == 200
        assert 'access' in response.data
