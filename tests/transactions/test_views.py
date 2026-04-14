"""
Testes de integração para as views SSR do app transactions.
"""
import pytest
from datetime import date
from decimal import Decimal

from django.test import Client

from apps.accounts.models import CustomUser
from apps.cards.models import Card
from apps.categories.models import Category
from apps.transactions.models import RecurringConfig, Transaction
from apps.transactions.services import create_recurring_transaction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    u = CustomUser.objects.create_user(
        email='view@test.com',
        nickname='viewuser',
        password='pass12345',
    )
    u.is_first_access = False
    u.save()
    return u


@pytest.fixture
def other_user(db):
    u = CustomUser.objects.create_user(
        email='other@test.com',
        nickname='otheruser',
        password='pass12345',
    )
    u.is_first_access = False
    u.save()
    return u


@pytest.fixture
def category(user):
    return Category.objects.create(
        user=user,
        name='Alimentação',
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


@pytest.fixture
def client_auth(user):
    client = Client()
    client.login(username='view@test.com', password='pass12345')
    return client


# ---------------------------------------------------------------------------
# TestTransactionListView
# ---------------------------------------------------------------------------

class TestTransactionListView:
    def test_redireciona_sem_autenticacao(self, db):
        """Usuário não autenticado é redirecionado ao acessar /transactions/."""
        client = Client()
        response = client.get('/transactions/')
        assert response.status_code == 302

    def test_lista_vazia(self, client_auth):
        """Usuário autenticado sem transações recebe 200."""
        response = client_auth.get('/transactions/')
        assert response.status_code == 200

    def test_lista_com_transacao(self, client_auth, transaction):
        """Lista exibe a transação criada pelo usuário."""
        response = client_auth.get('/transactions/')
        assert response.status_code == 200
        assert transaction.name.encode() in response.content

    def test_contexto_inclui_resumo(self, client_auth, user, category):
        """GET deve expor resumo com entradas, saídas e saldo no contexto."""
        Transaction.objects.create(
            user=user, name='Salário', amount=Decimal('1000.00'), type='entrada',
            category=category, date=date(2024, 2, 5),
        )
        Transaction.objects.create(
            user=user, name='Mercado', amount=Decimal('250.00'), type='saida',
            category=category, date=date(2024, 2, 10),
        )
        response = client_auth.get(
            '/transactions/?date_start=2024-02-01&date_end=2024-02-28'
        )
        assert response.status_code == 200
        resumo = response.context['resumo']
        assert resumo['total_entradas'] == Decimal('1000.00')
        assert resumo['total_saidas'] == Decimal('250.00')
        assert resumo['saldo_liquido'] == Decimal('750.00')


# ---------------------------------------------------------------------------
# TestTransactionCreateView
# ---------------------------------------------------------------------------

class TestTransactionCreateView:
    def test_get_form(self, client_auth):
        """GET /transactions/create/ retorna formulário com status 200."""
        response = client_auth.get('/transactions/create/')
        assert response.status_code == 200

    def test_post_cria_transacao_simples(self, client_auth, user, category):
        """POST com dados válidos cria transação simples e redireciona."""
        response = client_auth.post('/transactions/create/', {
            'name': 'Supermercado',
            'amount': '250.00',
            'type': 'saida',
            'status': 'pendente',
            'category_id': str(category.id),
            'date': '2024-01-15',
        })
        assert response.status_code == 302
        assert Transaction.objects.filter(user=user, name='Supermercado').exists()

    def test_post_cria_recorrente(self, client_auth, user, category):
        """POST com is_recurring=on e frequency=mensal cria transação recorrente."""
        response = client_auth.post('/transactions/create/', {
            'name': 'Netflix',
            'amount': '39.90',
            'type': 'saida',
            'status': 'pendente',
            'category_id': str(category.id),
            'date': '2024-01-01',
            'is_recurring': 'on',
            'frequency': 'mensal',
        })
        assert response.status_code == 302
        t = Transaction.objects.filter(user=user, name='Netflix', is_recurring=True, recurring_parent__isnull=True).first()
        assert t is not None
        assert RecurringConfig.objects.filter(transaction=t).exists()

    def test_post_cria_parcelada(self, client_auth, user, category):
        """POST com is_installment=on e total_installments=3 cria transação parcelada."""
        response = client_auth.post('/transactions/create/', {
            'name': 'Notebook',
            'amount': '3000.00',
            'type': 'saida',
            'status': 'pendente',
            'category_id': str(category.id),
            'date': '2024-01-01',
            'is_installment': 'on',
            'total_installments': '3',
        })
        assert response.status_code == 302
        t = Transaction.objects.filter(user=user, name='Notebook', is_installment=True).first()
        assert t is not None
        assert t.installments.count() == 3

    def test_post_sem_categoria_retorna_erro(self, client_auth):
        """POST sem category_id re-exibe formulário com mensagem de erro."""
        response = client_auth.post('/transactions/create/', {
            'name': 'Teste',
            'amount': '100.00',
            'type': 'saida',
            'date': '2024-01-01',
        })
        assert response.status_code == 200
        assert b'Categoria' in response.content or b'error' in response.content.lower()


# ---------------------------------------------------------------------------
# TestTransactionDeleteView
# ---------------------------------------------------------------------------

class TestTransactionDeleteView:
    def test_delete_simples(self, client_auth, transaction):
        """POST para delete URL realiza soft-delete na transação simples."""
        response = client_auth.post(f'/transactions/{transaction.pk}/delete/')
        assert response.status_code == 302
        transaction.refresh_from_db()
        assert transaction.is_active is False

    def test_delete_recorrente(self, client_auth, user, category):
        """POST para delete URL chama delete_recurring_transaction em transação recorrente."""
        pai = create_recurring_transaction(
            user=user,
            transaction_data={
                'name': 'Recorrente',
                'amount': Decimal('100.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            frequency='mensal',
        )
        filhos_ids = list(
            Transaction.objects.filter(recurring_parent=pai).values_list('id', flat=True)
        )

        response = client_auth.post(f'/transactions/{pai.pk}/delete/')
        assert response.status_code == 302

        pai.refresh_from_db()
        assert pai.is_active is False

        for filho_id in filhos_ids:
            filho = Transaction.objects.get(id=filho_id)
            assert filho.is_active is False


# ---------------------------------------------------------------------------
# TestTransactionDetailView
# ---------------------------------------------------------------------------

class TestTransactionDetailView:
    def test_exibe_transacao(self, client_auth, transaction):
        """GET detalhe exibe informações da transação."""
        response = client_auth.get(f'/transactions/{transaction.pk}/')
        assert response.status_code == 200
        assert transaction.name.encode() in response.content

    def test_exibe_parcelas(self, client_auth, user, category):
        """Detail view exibe parcelas quando a transação é parcelada."""
        from apps.transactions.services import create_installment_transaction
        pai = create_installment_transaction(
            user=user,
            transaction_data={
                'name': 'TV Parcelada',
                'amount': Decimal('600.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            total_installments=3,
        )
        response = client_auth.get(f'/transactions/{pai.pk}/')
        assert response.status_code == 200
        # A página deve renderizar sem erros e conter o nome da transação
        assert b'TV Parcelada' in response.content


# ---------------------------------------------------------------------------
# TestTransactionUpdateView
# ---------------------------------------------------------------------------

class TestTransactionUpdateView:
    def test_redireciona_sem_autenticacao(self, db, transaction):
        """Usuário não autenticado é redirecionado ao tentar editar."""
        client = Client()
        response = client.post(f'/transactions/{transaction.pk}/edit/', {'name': 'Novo Nome'})
        assert response.status_code == 302

    def test_get_form_edicao(self, client_auth, transaction):
        """GET /transactions/<pk>/edit/ retorna formulário com 200."""
        response = client_auth.get(f'/transactions/{transaction.pk}/edit/')
        assert response.status_code == 200

    def test_get_form_edicao_renderiza_valor_e_data_em_formato_de_input(
        self, client_auth, transaction
    ):
        """O form de edição deve vir com Valor (dot decimal) e Data (ISO)
        preenchidos, compatíveis com <input type="number"> e type="date"."""
        response = client_auth.get(f'/transactions/{transaction.pk}/edit/')
        html = response.content.decode('utf-8')
        # Valor com ponto (não vírgula) — input type="number" exige dot decimal
        assert 'value="1500.00"' in html, 'amount precisa estar em formato dot decimal'
        # Data em ISO YYYY-MM-DD — input type="date" exige esse formato
        assert 'value="2024-01-10"' in html, 'date precisa estar em formato ISO'

    def test_post_atualiza_nome(self, client_auth, transaction):
        """POST para edit URL atualiza o nome da transação e redireciona."""
        response = client_auth.post(f'/transactions/{transaction.pk}/edit/', {
            'name': 'Nome Atualizado',
        })
        assert response.status_code == 302
        transaction.refresh_from_db()
        assert transaction.name == 'Nome Atualizado'
