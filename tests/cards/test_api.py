import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.cards.models import Card


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        email='api@test.com',
        nickname='apiuser',
        password='pass12345',
    )


@pytest.fixture
def other_user(db):
    return CustomUser.objects.create_user(
        email='other@test.com',
        nickname='otheruser',
        password='pass12345',
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


@pytest.fixture
def card(user):
    return Card.objects.create(
        user=user,
        name='Nubank',
        brand='Mastercard',
        last_four_digits='1234',
        card_type='credito',
        credit_limit=5000,
    )


class TestCardListCreateAPI:
    def test_sem_jwt_retorna_401(self, api_client):
        """GET /api/v1/cards/ sem autenticação retorna 401."""
        response = api_client.get('/api/v1/cards/')
        assert response.status_code == 401

    def test_lista_cartoes_com_available_limit(self, auth_client, card):
        """GET /api/v1/cards/ retorna lista com campo available_limit e valor correto."""
        response = auth_client.get('/api/v1/cards/')
        assert response.status_code == 200
        assert len(response.data) == 1
        assert 'available_limit' in response.data[0]
        # Cartão de crédito com credit_limit=5000 e sem transações deve ter limite completo
        from decimal import Decimal
        assert Decimal(str(response.data[0]['available_limit'])) == Decimal('5000.00')

    def test_cria_cartao_credito(self, auth_client, user):
        """POST /api/v1/cards/ com dados válidos de crédito retorna 201."""
        response = auth_client.post('/api/v1/cards/', {
            'name': 'Nubank',
            'brand': 'Mastercard',
            'last_four_digits': '1234',
            'card_type': 'credito',
            'credit_limit': '5000.00',
        })
        assert response.status_code == 201
        assert Card.objects.filter(user=user, name='Nubank').exists()

    def test_cria_cartao_debito(self, auth_client, user):
        """POST /api/v1/cards/ com dados de débito retorna 201."""
        response = auth_client.post('/api/v1/cards/', {
            'name': 'Itaú Débito',
            'brand': 'Visa',
            'last_four_digits': '5678',
            'card_type': 'debito',
        })
        assert response.status_code == 201
        assert Card.objects.filter(user=user, name='Itaú Débito').exists()

    def test_tenant_isolation(self, auth_client, other_user):
        """GET /api/v1/cards/ retorna apenas cartões do usuário autenticado."""
        Card.objects.create(
            user=other_user,
            name='Outro Cartão',
            brand='Elo',
            last_four_digits='9999',
            card_type='debito',
        )
        response = auth_client.get('/api/v1/cards/')
        assert response.status_code == 200
        assert all(c['name'] != 'Outro Cartão' for c in response.data)


class TestCardDetailAPI:
    def test_sem_jwt_retorna_401(self, api_client, card):
        """GET /api/v1/cards/<pk>/ sem autenticação retorna 401."""
        response = api_client.get(f'/api/v1/cards/{card.pk}/')
        assert response.status_code == 401

    def test_get_retorna_cartao(self, auth_client, card):
        """GET /api/v1/cards/<pk>/ com JWT retorna dados do cartão."""
        response = auth_client.get(f'/api/v1/cards/{card.pk}/')
        assert response.status_code == 200
        assert response.data['name'] == 'Nubank'

    def test_put_atualiza_cartao(self, auth_client, card):
        """PUT /api/v1/cards/<pk>/ atualiza o cartão e retorna 200."""
        response = auth_client.put(f'/api/v1/cards/{card.pk}/', {
            'name': 'Nubank Atualizado',
            'brand': 'Mastercard',
            'last_four_digits': '1234',
            'card_type': 'credito',
        })
        assert response.status_code == 200
        assert response.data['name'] == 'Nubank Atualizado'

    def test_delete_soft_delete(self, auth_client, card):
        """DELETE /api/v1/cards/<pk>/ realiza soft-delete e retorna 204."""
        response = auth_client.delete(f'/api/v1/cards/{card.pk}/')
        assert response.status_code == 204
        card.refresh_from_db()
        assert card.is_active is False

    def test_acesso_cartao_outro_usuario_retorna_404(self, auth_client, other_user):
        """GET /api/v1/cards/<pk>/ de cartão de outro usuário retorna 404."""
        other_card = Card.objects.create(
            user=other_user,
            name='Outro',
            brand='Elo',
            last_four_digits='9999',
            card_type='debito',
        )
        response = auth_client.get(f'/api/v1/cards/{other_card.pk}/')
        assert response.status_code == 404


class TestCardTransactionsAPI:
    def test_sem_jwt_retorna_401(self, api_client, card):
        """GET /api/v1/cards/<pk>/transactions/ sem autenticação retorna 401."""
        response = api_client.get(f'/api/v1/cards/{card.pk}/transactions/')
        assert response.status_code == 401

    def test_retorna_200_para_cartao_valido(self, auth_client, card):
        """GET /api/v1/cards/<pk>/transactions/ com JWT retorna 200."""
        response = auth_client.get(f'/api/v1/cards/{card.pk}/transactions/')
        assert response.status_code == 200
