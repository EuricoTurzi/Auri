"""
Testes unitários para selectors do app reports.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cards.models import Card
from apps.categories.models import Category
from apps.transactions.models import Transaction
from apps.reports.models import ScheduledReport


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        email="reports@test.com",
        nickname="reportsuser",
        password="pass12345",
    )


@pytest.fixture
def other_user(db):
    return CustomUser.objects.create_user(
        email="other@test.com",
        nickname="otheruser",
        password="pass12345",
    )


@pytest.fixture
def category(user):
    return Category.objects.create(user=user, name="Alimentação", is_active=True)


@pytest.fixture
def category2(user):
    return Category.objects.create(user=user, name="Transporte", is_active=True)


@pytest.fixture
def card(user):
    return Card.objects.create(
        user=user,
        name="Nubank",
        brand="Mastercard",
        last_four_digits="1234",
        card_type="credito",
        credit_limit=Decimal("5000.00"),
    )


@pytest.fixture
def card2(user):
    return Card.objects.create(
        user=user,
        name="Inter",
        brand="Visa",
        last_four_digits="5678",
        card_type="credito",
        credit_limit=Decimal("3000.00"),
    )


@pytest.fixture
def transactions(user, category, category2, card, card2):
    """Cria um conjunto de transações para testes de dashboard."""
    txs = []
    # Entradas
    txs.append(Transaction.objects.create(
        user=user, name="Salário", amount=Decimal("5000.00"),
        type="entrada", status="pago", category=category,
        date=date(2024, 1, 15),
    ))
    txs.append(Transaction.objects.create(
        user=user, name="Freelance", amount=Decimal("1500.00"),
        type="entrada", status="pago", category=category2,
        date=date(2024, 2, 10),
    ))
    # Saídas
    txs.append(Transaction.objects.create(
        user=user, name="Almoço", amount=Decimal("50.00"),
        type="saida", status="pago", category=category, card=card,
        date=date(2024, 1, 20),
    ))
    txs.append(Transaction.objects.create(
        user=user, name="Uber", amount=Decimal("30.00"),
        type="saida", status="pendente", category=category2, card=card2,
        date=date(2024, 2, 5),
    ))
    txs.append(Transaction.objects.create(
        user=user, name="Mercado", amount=Decimal("200.00"),
        type="saida", status="pago", category=category, card=card,
        date=date(2024, 2, 15),
    ))
    return txs


@pytest.fixture
def other_transaction(other_user):
    cat = Category.objects.create(user=other_user, name="Outros", is_active=True)
    return Transaction.objects.create(
        user=other_user, name="Outro Salário", amount=Decimal("3000.00"),
        type="entrada", status="pago", category=cat,
        date=date(2024, 1, 15),
    )


# ---------------------------------------------------------------------------
# Testes: get_dashboard_data
# ---------------------------------------------------------------------------

class TestGetDashboardData:
    def test_totais_corretos(self, user, transactions):
        from apps.reports.selectors import get_dashboard_data
        data = get_dashboard_data(user)

        assert data["total_entradas"] == Decimal("6500.00")
        assert data["total_saidas"] == Decimal("280.00")
        assert data["saldo"] == Decimal("6220.00")

    def test_gastos_por_categoria(self, user, transactions):
        from apps.reports.selectors import get_dashboard_data
        data = get_dashboard_data(user)

        categorias = {item["categoria"]: item["total"] for item in data["gastos_por_categoria"]}
        assert categorias["Alimentação"] == Decimal("250.00")
        assert categorias["Transporte"] == Decimal("30.00")

    def test_evolucao_temporal(self, user, transactions):
        from apps.reports.selectors import get_dashboard_data
        data = get_dashboard_data(user)

        meses = {item["mes"]: item for item in data["evolucao_temporal"]}
        assert meses["2024-01"]["entradas"] == Decimal("5000.00")
        assert meses["2024-01"]["saidas"] == Decimal("50.00")
        assert meses["2024-02"]["entradas"] == Decimal("1500.00")
        assert meses["2024-02"]["saidas"] == Decimal("230.00")

    def test_gastos_por_cartao(self, user, transactions):
        from apps.reports.selectors import get_dashboard_data
        data = get_dashboard_data(user)

        cartoes = {item["cartao"]: item["total"] for item in data["gastos_por_cartao"]}
        assert cartoes["Nubank"] == Decimal("250.00")
        assert cartoes["Inter"] == Decimal("30.00")

    def test_filtro_periodo(self, user, transactions):
        from apps.reports.selectors import get_dashboard_data
        filters = {"period_start": "2024-02-01", "period_end": "2024-02-28"}
        data = get_dashboard_data(user, filters)

        assert data["total_entradas"] == Decimal("1500.00")
        assert data["total_saidas"] == Decimal("230.00")

    def test_filtro_categoria(self, user, transactions, category):
        from apps.reports.selectors import get_dashboard_data
        filters = {"category_ids": [str(category.id)]}
        data = get_dashboard_data(user, filters)

        assert data["total_entradas"] == Decimal("5000.00")
        assert data["total_saidas"] == Decimal("250.00")

    def test_filtro_tipo(self, user, transactions):
        from apps.reports.selectors import get_dashboard_data
        filters = {"type": "saida"}
        data = get_dashboard_data(user, filters)

        assert data["total_entradas"] == Decimal("0")
        assert data["total_saidas"] == Decimal("280.00")

    def test_filtro_cartao(self, user, transactions, card):
        from apps.reports.selectors import get_dashboard_data
        filters = {"card_ids": [str(card.id)]}
        data = get_dashboard_data(user, filters)

        assert data["total_saidas"] == Decimal("250.00")

    def test_sem_transacoes_retorna_zeros(self, user):
        from apps.reports.selectors import get_dashboard_data
        data = get_dashboard_data(user)

        assert data["total_entradas"] == Decimal("0")
        assert data["total_saidas"] == Decimal("0")
        assert data["saldo"] == Decimal("0")
        assert data["gastos_por_categoria"] == []
        assert data["evolucao_temporal"] == []
        assert data["gastos_por_cartao"] == []

    def test_tenant_isolation(self, user, transactions, other_transaction):
        from apps.reports.selectors import get_dashboard_data
        data = get_dashboard_data(user)

        # Não deve incluir a transação do other_user
        assert data["total_entradas"] == Decimal("6500.00")


# ---------------------------------------------------------------------------
# Testes: get_filtered_transactions
# ---------------------------------------------------------------------------

class TestGetFilteredTransactions:
    def test_retorna_todas_sem_filtro(self, user, transactions):
        from apps.reports.selectors import get_filtered_transactions
        qs = get_filtered_transactions(user, {})
        assert qs.count() == 5

    def test_filtro_periodo(self, user, transactions):
        from apps.reports.selectors import get_filtered_transactions
        filters = {"period_start": "2024-02-01", "period_end": "2024-02-28"}
        qs = get_filtered_transactions(user, filters)
        assert qs.count() == 3

    def test_filtro_tipo(self, user, transactions):
        from apps.reports.selectors import get_filtered_transactions
        filters = {"type": "entrada"}
        qs = get_filtered_transactions(user, filters)
        assert qs.count() == 2

    def test_filtro_categoria(self, user, transactions, category):
        from apps.reports.selectors import get_filtered_transactions
        filters = {"category_ids": [str(category.id)]}
        qs = get_filtered_transactions(user, filters)
        assert qs.count() == 3

    def test_filtro_cartao(self, user, transactions, card):
        from apps.reports.selectors import get_filtered_transactions
        filters = {"card_ids": [str(card.id)]}
        qs = get_filtered_transactions(user, filters)
        assert qs.count() == 2

    def test_filtros_combinados(self, user, transactions, category, card):
        from apps.reports.selectors import get_filtered_transactions
        filters = {
            "type": "saida",
            "category_ids": [str(category.id)],
            "card_ids": [str(card.id)],
        }
        qs = get_filtered_transactions(user, filters)
        assert qs.count() == 2

    def test_tenant_isolation(self, user, transactions, other_transaction):
        from apps.reports.selectors import get_filtered_transactions
        qs = get_filtered_transactions(user, {})
        assert qs.count() == 5


# ---------------------------------------------------------------------------
# Testes: get_user_scheduled_reports
# ---------------------------------------------------------------------------

class TestGetUserScheduledReports:
    def test_retorna_relatorios_ativos(self, user):
        from apps.reports.selectors import get_user_scheduled_reports
        ScheduledReport.objects.create(
            user=user, name="Semanal", frequency="semanal",
            export_format="csv", filters={}, next_send_at=timezone.now(),
        )
        ScheduledReport.objects.create(
            user=user, name="Mensal", frequency="mensal",
            export_format="pdf", filters={}, next_send_at=timezone.now(),
            is_active=False,
        )
        qs = get_user_scheduled_reports(user)
        assert qs.count() == 1
        assert qs.first().name == "Semanal"

    def test_tenant_isolation(self, user, other_user):
        from apps.reports.selectors import get_user_scheduled_reports
        ScheduledReport.objects.create(
            user=other_user, name="Do outro", frequency="semanal",
            export_format="csv", filters={}, next_send_at=timezone.now(),
        )
        qs = get_user_scheduled_reports(user)
        assert qs.count() == 0
