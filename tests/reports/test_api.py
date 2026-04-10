"""
Testes de integração para a API REST do app reports.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

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
        email="api@test.com",
        nickname="apiuser",
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
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


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
def scheduled_report(user):
    return ScheduledReport.objects.create(
        user=user, name="Semanal CSV", frequency="semanal",
        export_format="csv", filters={},
        next_send_at=timezone.now() + timedelta(days=7),
    )


# ---------------------------------------------------------------------------
# Testes: DashboardAPIView
# ---------------------------------------------------------------------------

class TestDashboardAPIView:
    def test_get_dashboard(self, auth_client, transaction):
        response = auth_client.get("/api/v1/reports/dashboard/")
        assert response.status_code == 200
        assert "total_entradas" in response.data
        assert "total_saidas" in response.data
        assert "saldo" in response.data

    def test_get_dashboard_com_filtros(self, auth_client, transaction):
        response = auth_client.get("/api/v1/reports/dashboard/?period_start=2024-01-01&period_end=2024-12-31")
        assert response.status_code == 200

    def test_sem_jwt_retorna_401(self, api_client):
        response = api_client.get("/api/v1/reports/dashboard/")
        assert response.status_code == 401

    def test_tenant_isolation(self, auth_client, other_user):
        cat = Category.objects.create(user=other_user, name="Outros", is_active=True)
        Transaction.objects.create(
            user=other_user, name="Outro", amount=Decimal("1000.00"),
            type="entrada", status="pago", category=cat,
            date=date(2024, 1, 1),
        )
        response = auth_client.get("/api/v1/reports/dashboard/")
        assert response.status_code == 200
        assert Decimal(response.data["total_entradas"]) == Decimal("0")


# ---------------------------------------------------------------------------
# Testes: ExportAPIView
# ---------------------------------------------------------------------------

class TestExportAPIView:
    def test_export_csv(self, auth_client, transaction):
        response = auth_client.get("/api/v1/reports/export/csv/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"

    def test_export_xlsx(self, auth_client, transaction):
        response = auth_client.get("/api/v1/reports/export/xlsx/")
        assert response.status_code == 200

    def test_export_pdf(self, auth_client, transaction):
        response = auth_client.get("/api/v1/reports/export/pdf/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_formato_invalido(self, auth_client):
        response = auth_client.get("/api/v1/reports/export/xml/")
        assert response.status_code == 400

    def test_sem_jwt_retorna_401(self, api_client):
        response = api_client.get("/api/v1/reports/export/csv/")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Testes: ScheduledReportListCreateAPIView
# ---------------------------------------------------------------------------

class TestScheduledReportListCreateAPIView:
    def test_list(self, auth_client, scheduled_report):
        response = auth_client.get("/api/v1/reports/scheduled/")
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_create(self, auth_client):
        response = auth_client.post("/api/v1/reports/scheduled/", {
            "name": "Novo Relatório",
            "frequency": "semanal",
            "export_format": "csv",
            "filters": {},
        }, format="json")
        assert response.status_code == 201
        assert ScheduledReport.objects.count() == 1

    def test_tenant_isolation(self, auth_client, other_user):
        ScheduledReport.objects.create(
            user=other_user, name="Do outro", frequency="semanal",
            export_format="csv", filters={},
            next_send_at=timezone.now() + timedelta(days=7),
        )
        response = auth_client.get("/api/v1/reports/scheduled/")
        assert len(response.data) == 0

    def test_sem_jwt_retorna_401(self, api_client):
        response = api_client.get("/api/v1/reports/scheduled/")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Testes: ScheduledReportDetailAPIView
# ---------------------------------------------------------------------------

class TestScheduledReportDetailAPIView:
    def test_get_detail(self, auth_client, scheduled_report):
        response = auth_client.get(f"/api/v1/reports/scheduled/{scheduled_report.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "Semanal CSV"

    def test_put_update(self, auth_client, scheduled_report):
        response = auth_client.put(f"/api/v1/reports/scheduled/{scheduled_report.id}/", {
            "name": "Atualizado",
            "frequency": "mensal",
            "export_format": "pdf",
            "filters": {},
        }, format="json")
        assert response.status_code == 200
        assert response.data["name"] == "Atualizado"

    def test_delete_soft(self, auth_client, scheduled_report):
        response = auth_client.delete(f"/api/v1/reports/scheduled/{scheduled_report.id}/")
        assert response.status_code == 204
        scheduled_report.refresh_from_db()
        assert scheduled_report.is_active is False

    def test_tenant_isolation(self, auth_client, other_user):
        report = ScheduledReport.objects.create(
            user=other_user, name="Do outro", frequency="semanal",
            export_format="csv", filters={},
            next_send_at=timezone.now() + timedelta(days=7),
        )
        response = auth_client.get(f"/api/v1/reports/scheduled/{report.id}/")
        assert response.status_code == 404

    def test_sem_jwt_retorna_401(self, api_client, scheduled_report):
        response = api_client.get(f"/api/v1/reports/scheduled/{scheduled_report.id}/")
        assert response.status_code == 401
