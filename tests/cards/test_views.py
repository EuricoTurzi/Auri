import pytest
from django.test import Client

from apps.accounts.models import CustomUser
from apps.cards.models import Card


@pytest.fixture
def user(db):
    user = CustomUser.objects.create_user(
        email='view@test.com',
        nickname='viewuser',
        password='pass12345',
    )
    user.is_first_access = False
    user.save()
    return user


@pytest.fixture
def other_user(db):
    other = CustomUser.objects.create_user(
        email='other@test.com',
        nickname='otheruser',
        password='pass12345',
    )
    other.is_first_access = False
    other.save()
    return other


@pytest.fixture
def client_auth(user):
    client = Client()
    client.login(username='view@test.com', password='pass12345')
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


class TestCardListView:
    def test_autenticado_retorna_200(self, client_auth):
        """Usuário autenticado acessa /cards/ e recebe status 200."""
        response = client_auth.get('/cards/')
        assert response.status_code == 200

    def test_anonimo_redireciona(self, db):
        """Usuário não autenticado é redirecionado ao acessar /cards/."""
        client = Client()
        response = client.get('/cards/')
        assert response.status_code == 302


class TestCardCreateView:
    def test_get_retorna_200(self, client_auth):
        """GET /cards/create/ com usuário autenticado retorna status 200."""
        response = client_auth.get('/cards/create/')
        assert response.status_code == 200

    def test_post_cria_cartao_credito(self, client_auth, user):
        """POST com dados válidos de cartão de crédito cria o cartão e redireciona."""
        response = client_auth.post('/cards/create/', {
            'name': 'Nubank',
            'brand': 'Mastercard',
            'last_four_digits': '1234',
            'card_type': 'credito',
            'credit_limit': '5000.00',
            'billing_close_day': '3',
            'billing_due_day': '10',
        })
        assert response.status_code == 302
        assert Card.objects.filter(user=user, name='Nubank').exists()

    def test_post_cria_cartao_debito(self, client_auth, user):
        """POST com dados válidos de cartão de débito cria o cartão e redireciona."""
        response = client_auth.post('/cards/create/', {
            'name': 'Itaú Débito',
            'brand': 'Visa',
            'last_four_digits': '5678',
            'card_type': 'debito',
        })
        assert response.status_code == 302
        assert Card.objects.filter(user=user, name='Itaú Débito').exists()

    def test_post_digitos_invalidos(self, client_auth):
        """POST com últimos 4 dígitos inválidos re-exibe o formulário com erro (200)."""
        response = client_auth.post('/cards/create/', {
            'name': 'Test',
            'brand': 'Visa',
            'last_four_digits': '12AB',
            'card_type': 'debito',
        })
        assert response.status_code == 200

    def test_debito_ignora_campos_de_credito(self, client_auth, user):
        """POST com campos de crédito para cartão de débito cria o cartão como débito."""
        response = client_auth.post('/cards/create/', {
            'name': 'Débito Simples',
            'brand': 'Visa',
            'last_four_digits': '7777',
            'card_type': 'debito',
            'credit_limit': '9999',
            'billing_close_day': '5',
        })
        assert response.status_code == 302
        cartao = Card.objects.filter(user=user, name='Débito Simples').first()
        assert cartao is not None
        assert cartao.card_type == 'debito'


class TestCardDetailView:
    def test_retorna_200_para_dono(self, client_auth, card):
        """GET /cards/<pk>/ retorna 200 para o dono do cartão."""
        response = client_auth.get(f'/cards/{card.pk}/')
        assert response.status_code == 200

    def test_redireciona_para_card_de_outro_usuario(self, client_auth, other_user):
        """GET /cards/<pk>/ de cartão de outro usuário redireciona."""
        other_card = Card.objects.create(
            user=other_user,
            name='Outro',
            brand='Elo',
            last_four_digits='9999',
            card_type='debito',
        )
        response = client_auth.get(f'/cards/{other_card.pk}/')
        assert response.status_code == 302


class TestCardUpdateView:
    def test_get_retorna_200(self, client_auth, card):
        """GET /cards/<pk>/edit/ retorna 200 para o dono do cartão."""
        response = client_auth.get(f'/cards/{card.pk}/edit/')
        assert response.status_code == 200

    def test_post_atualiza(self, client_auth, card):
        """POST /cards/<pk>/edit/ com dados válidos atualiza o cartão e redireciona."""
        response = client_auth.post(f'/cards/{card.pk}/edit/', {
            'name': 'Nubank Atualizado',
            'brand': 'Mastercard',
            'last_four_digits': '1234',
            'card_type': 'credito',
        })
        assert response.status_code == 302
        card.refresh_from_db()
        assert card.name == 'Nubank Atualizado'


class TestCardDeleteView:
    def test_soft_delete(self, client_auth, card):
        """POST /cards/<pk>/delete/ realiza soft-delete (is_active=False)."""
        response = client_auth.post(f'/cards/{card.pk}/delete/')
        assert response.status_code == 302
        card.refresh_from_db()
        assert card.is_active is False

    def test_rejeita_outro_usuario(self, client_auth, other_user):
        """POST /cards/<pk>/delete/ de cartão de outro usuário não desativa o cartão."""
        other_card = Card.objects.create(
            user=other_user,
            name='Outro',
            brand='Elo',
            last_four_digits='9999',
            card_type='debito',
        )
        client_auth.post(f'/cards/{other_card.pk}/delete/')
        other_card.refresh_from_db()
        assert other_card.is_active is True
