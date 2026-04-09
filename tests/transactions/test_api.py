"""
Testes de integração para a API REST do app transactions.
"""
import pytest
from datetime import date
from decimal import Decimal

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.cards.models import Card
from apps.categories.models import Category
from apps.transactions.models import Installment, Transaction
from apps.transactions.services import create_recurring_transaction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
def category(user):
    return Category.objects.create(
        user=user,
        name='Alimentação',
        is_active=True,
    )


@pytest.fixture
def other_category(other_user):
    return Category.objects.create(
        user=other_user,
        name='Other',
        is_active=True,
    )


@pytest.fixture
def card(user):
    return Card.objects.create(
        user=user,
        name='Nubank',
        brand='Mastercard',
        last_four_digits='1234',
        card_type='credito',
        credit_limit=Decimal('5000.00'),
    )


@pytest.fixture
def transaction(user, category):
    return Transaction.objects.create(
        user=user,
        name='Aluguel',
        amount=Decimal('1500.00'),
        type='saida',
        status='pendente',
        category=category,
        date=date(2024, 1, 10),
    )


# ---------------------------------------------------------------------------
# TestTransactionListCreateAPI
# ---------------------------------------------------------------------------

class TestTransactionListCreateAPI:
    def test_sem_jwt_retorna_401(self, api_client):
        """GET /api/v1/transactions/ sem JWT retorna 401."""
        response = api_client.get('/api/v1/transactions/')
        assert response.status_code == 401

    def test_lista_vazia_com_jwt(self, auth_client):
        """GET /api/v1/transactions/ com JWT e sem transações retorna lista vazia."""
        response = auth_client.get('/api/v1/transactions/')
        assert response.status_code == 200
        assert response.data == []

    def test_cria_transacao_simples(self, auth_client, user, category):
        """POST /api/v1/transactions/ com dados válidos cria transação e retorna 201."""
        response = auth_client.post('/api/v1/transactions/', {
            'name': 'Mercado',
            'amount': '150.00',
            'type': 'saida',
            'status': 'pendente',
            'category_id': str(category.id),
            'date': '2024-01-15',
        })
        assert response.status_code == 201
        assert Transaction.objects.filter(user=user, name='Mercado').exists()
        assert response.data['name'] == 'Mercado'

    def test_filtro_por_tipo(self, auth_client, user, category):
        """GET com filtro type=entrada retorna apenas transações de entrada."""
        Transaction.objects.create(
            user=user, name='Salário', amount=Decimal('3000.00'),
            type='entrada', category=category, date=date(2024, 1, 1),
        )
        Transaction.objects.create(
            user=user, name='Aluguel', amount=Decimal('1000.00'),
            type='saida', category=category, date=date(2024, 1, 2),
        )
        response = auth_client.get('/api/v1/transactions/?type=entrada')
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['type'] == 'entrada'

    def test_filtro_por_status(self, auth_client, user, category):
        """GET com filtro status=pago retorna apenas transações pagas."""
        Transaction.objects.create(
            user=user, name='Pendente', amount=Decimal('100.00'),
            type='saida', status='pendente', category=category, date=date(2024, 1, 1),
        )
        Transaction.objects.create(
            user=user, name='Pago', amount=Decimal('200.00'),
            type='saida', status='pago', category=category, date=date(2024, 1, 2),
        )
        response = auth_client.get('/api/v1/transactions/?status=pago')
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['status'] == 'pago'


# ---------------------------------------------------------------------------
# TestTransactionDetailAPI
# ---------------------------------------------------------------------------

class TestTransactionDetailAPI:
    def test_get_retorna_transacao(self, auth_client, transaction):
        """GET /api/v1/transactions/<pk>/ retorna dados da transação."""
        response = auth_client.get(f'/api/v1/transactions/{transaction.pk}/')
        assert response.status_code == 200
        assert response.data['name'] == 'Aluguel'

    def test_put_atualiza_transacao(self, auth_client, transaction, category):
        """PUT /api/v1/transactions/<pk>/ atualiza a transação e retorna 200."""
        response = auth_client.put(f'/api/v1/transactions/{transaction.pk}/', {
            'name': 'Aluguel Atualizado',
            'amount': '1600.00',
            'type': 'saida',
            'status': 'pago',
            'category_id': str(category.id),
            'date': '2024-01-10',
        })
        assert response.status_code == 200
        assert response.data['name'] == 'Aluguel Atualizado'

    def test_delete_soft_delete_retorna_204(self, auth_client, transaction):
        """DELETE /api/v1/transactions/<pk>/ realiza soft-delete e retorna 204."""
        response = auth_client.delete(f'/api/v1/transactions/{transaction.pk}/')
        assert response.status_code == 204
        transaction.refresh_from_db()
        assert transaction.is_active is False

    def test_tenant_isolation(self, auth_client, other_user, other_category):
        """GET transação de outro usuário retorna 404."""
        other_transaction = Transaction.objects.create(
            user=other_user,
            name='Transação Alheia',
            amount=Decimal('500.00'),
            type='entrada',
            category=other_category,
            date=date(2024, 1, 1),
        )
        response = auth_client.get(f'/api/v1/transactions/{other_transaction.pk}/')
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestRecurringAPI
# ---------------------------------------------------------------------------

class TestRecurringAPI:
    def test_post_cria_recorrente_com_ocorrencias(self, auth_client, user, category):
        """POST /api/v1/transactions/recurring/ cria transação recorrente e ocorrências."""
        response = auth_client.post('/api/v1/transactions/recurring/', {
            'name': 'Aluguel',
            'amount': '1500.00',
            'type': 'saida',
            'status': 'pendente',
            'category_id': str(category.id),
            'date': '2024-01-01',
            'frequency': 'mensal',
        })
        assert response.status_code == 201
        assert response.data['is_recurring'] is True
        pai_id = response.data['id']
        filhos = Transaction.objects.filter(recurring_parent_id=pai_id)
        assert filhos.count() == 12

    def test_delete_recorrente_cascade(self, auth_client, user, category):
        """DELETE /api/v1/transactions/recurring/<pk>/ soft-deleta pai e filhos."""
        pai = create_recurring_transaction(
            user=user,
            transaction_data={
                'name': 'Netflix',
                'amount': Decimal('39.90'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            frequency='mensal',
        )
        filhos_ids = list(
            Transaction.objects.filter(recurring_parent=pai).values_list('id', flat=True)
        )

        response = auth_client.delete(f'/api/v1/transactions/recurring/{pai.pk}/')
        assert response.status_code == 204

        pai.refresh_from_db()
        assert pai.is_active is False
        for filho_id in filhos_ids:
            filho = Transaction.objects.get(id=filho_id)
            assert filho.is_active is False


# ---------------------------------------------------------------------------
# TestInstallmentAPI
# ---------------------------------------------------------------------------

class TestInstallmentAPI:
    def test_post_cria_parcelada(self, auth_client, user, category):
        """POST /api/v1/transactions/installment/ cria transação parcelada com parcelas."""
        response = auth_client.post('/api/v1/transactions/installment/', {
            'name': 'TV',
            'amount': '900.00',
            'type': 'saida',
            'status': 'pendente',
            'category_id': str(category.id),
            'date': '2024-01-01',
            'total_installments': 3,
        })
        assert response.status_code == 201
        assert response.data['is_installment'] is True
        pai_id = response.data['id']
        parcelas = Installment.objects.filter(parent_transaction_id=pai_id)
        assert parcelas.count() == 3

    def test_get_installments_lista_parcelas(self, auth_client, user, category):
        """GET /api/v1/transactions/<pk>/installments/ lista parcelas da transação."""
        from apps.transactions.services import create_installment_transaction
        pai = create_installment_transaction(
            user=user,
            transaction_data={
                'name': 'Geladeira',
                'amount': Decimal('600.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            total_installments=3,
        )
        response = auth_client.get(f'/api/v1/transactions/{pai.pk}/installments/')
        assert response.status_code == 200
        assert len(response.data) == 3

    def test_post_parcelada_entrada_retorna_400(self, auth_client, category):
        """POST transação parcelada do tipo entrada deve retornar 400."""
        response = auth_client.post('/api/v1/transactions/installment/', {
            'name': 'Salário',
            'amount': '3000.00',
            'type': 'entrada',
            'status': 'pendente',
            'category_id': str(category.id),
            'date': '2024-01-01',
            'total_installments': 3,
        })
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# TestStatusUpdateAPI
# ---------------------------------------------------------------------------

class TestStatusUpdateAPI:
    def test_patch_altera_status_para_pago(self, auth_client, transaction):
        """PATCH /api/v1/transactions/<pk>/status/ altera status para 'pago'."""
        response = auth_client.patch(
            f'/api/v1/transactions/{transaction.pk}/status/',
            {'status': 'pago'},
        )
        assert response.status_code == 200
        assert response.data['status'] == 'pago'
        transaction.refresh_from_db()
        assert transaction.status == 'pago'

    def test_sem_jwt_retorna_401(self, api_client, transaction):
        """PATCH sem JWT retorna 401."""
        response = api_client.patch(
            f'/api/v1/transactions/{transaction.pk}/status/',
            {'status': 'pago'},
        )
        assert response.status_code == 401
