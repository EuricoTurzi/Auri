"""
Testes de integração para as views SSR do app reports.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.test import Client
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
    u = CustomUser.objects.create_user(
        email="view@test.com",
        nickname="viewuser",
        password="pass12345",
    )
    u.is_first_access = False
    u.save()
    return u


@pytest.fixture
def other_user(db):
    u = CustomUser.objects.create_user(
        email="other@test.com",
        nickname="otheruser",
        password="pass12345",
    )
    u.is_first_access = False
    u.save()
    return u


@pytest.fixture
def category(user):
    return Category.objects.create(user=user, name="Alimentação", is_active=True)


@pytest.fixture
def card(user):
    return Card.objects.create(
        user=user, name="Nubank", brand="Mastercard",
        last_four_digits="1234", card_type="credito",
        credit_limit=Decimal("5000.00"),
    )


@pytest.fixture
def transaction(user, category, card):
    return Transaction.objects.create(
        user=user, name="Salário", amount=Decimal("5000.00"),
        type="entrada", status="pago", category=category,
        date=date(2024, 1, 15),
    )


@pytest.fixture
def client_auth(user):
    client = Client()
    client.login(email="view@test.com", password="pass12345")
    return client


@pytest.fixture
def scheduled_report(user):
    return ScheduledReport.objects.create(
        user=user, name="Semanal CSV", frequency="semanal",
        export_format="csv", filters={},
        next_send_at=timezone.now() + timedelta(days=7),
    )


# ---------------------------------------------------------------------------
# Testes: DashboardView
# ---------------------------------------------------------------------------

class TestDashboardView:
    def test_dashboard_autenticado(self, client_auth, transaction):
        response = client_auth.get("/reports/")
        assert response.status_code == 200

    def test_dashboard_nao_autenticado(self):
        client = Client()
        response = client.get("/reports/")
        assert response.status_code == 302

    def test_dashboard_com_filtros(self, client_auth, transaction):
        response = client_auth.get("/reports/?period_start=2024-01-01&period_end=2024-12-31")
        assert response.status_code == 200

    def test_dashboard_contexto(self, client_auth, transaction):
        response = client_auth.get("/reports/")
        assert "dashboard" in response.context
        assert "total_entradas" in response.context["dashboard"]


# ---------------------------------------------------------------------------
# Testes: ExportView
# ---------------------------------------------------------------------------

class TestExportView:
    def test_export_csv(self, client_auth, transaction):
        response = client_auth.get("/reports/export/csv/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"

    def test_export_xlsx(self, client_auth, transaction):
        response = client_auth.get("/reports/export/xlsx/")
        assert response.status_code == 200
        assert "spreadsheetml" in response["Content-Type"]

    def test_export_pdf(self, client_auth, transaction):
        response = client_auth.get("/reports/export/pdf/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_export_formato_invalido(self, client_auth):
        response = client_auth.get("/reports/export/xml/")
        assert response.status_code == 400

    def test_export_nao_autenticado(self):
        client = Client()
        response = client.get("/reports/export/csv/")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Testes: ScheduledReportListView
# ---------------------------------------------------------------------------

class TestScheduledReportListView:
    def test_lista_autenticado(self, client_auth, scheduled_report):
        response = client_auth.get("/reports/scheduled/")
        assert response.status_code == 200
        assert len(response.context["reports"]) == 1

    def test_tenant_isolation(self, client_auth, other_user):
        ScheduledReport.objects.create(
            user=other_user, name="Do outro", frequency="semanal",
            export_format="csv", filters={},
            next_send_at=timezone.now() + timedelta(days=7),
        )
        response = client_auth.get("/reports/scheduled/")
        assert len(response.context["reports"]) == 0


# ---------------------------------------------------------------------------
# Testes: ScheduledReportCreateView
# ---------------------------------------------------------------------------

class TestScheduledReportCreateView:
    def test_get_formulario(self, client_auth):
        response = client_auth.get("/reports/scheduled/create/")
        assert response.status_code == 200

    def test_post_cria_relatorio(self, client_auth, category):
        response = client_auth.post("/reports/scheduled/create/", {
            "name": "Meu Relatório",
            "frequency": "semanal",
            "export_format": "csv",
        })
        assert response.status_code == 302
        assert ScheduledReport.objects.count() == 1


# ---------------------------------------------------------------------------
# Testes: ScheduledReportDeleteView
# ---------------------------------------------------------------------------

class TestScheduledReportDeleteView:
    def test_soft_delete(self, client_auth, scheduled_report):
        response = client_auth.post(f"/reports/scheduled/{scheduled_report.id}/delete/")
        assert response.status_code == 302
        scheduled_report.refresh_from_db()
        assert scheduled_report.is_active is False

    def test_tenant_isolation(self, other_user, scheduled_report):
        client = Client()
        client.login(email="other@test.com", password="pass12345")
        response = client.post(f"/reports/scheduled/{scheduled_report.id}/delete/")
        assert response.status_code == 302
        scheduled_report.refresh_from_db()
        assert scheduled_report.is_active is True
