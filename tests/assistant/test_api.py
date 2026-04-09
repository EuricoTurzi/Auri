"""
Testes de integração para a API REST do app assistant.
"""
import json
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.assistant.models import AssistantInteraction
from apps.cards.models import Card
from apps.categories.models import Category
from apps.transactions.models import Transaction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        email="apiassistant@test.com",
        nickname="apiassistant",
        password="pass12345",
    )


@pytest.fixture
def other_user(db):
    return CustomUser.objects.create_user(
        email="apiother@test.com",
        nickname="apiother",
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
def auth_client_other(other_user):
    client = APIClient()
    token = RefreshToken.for_user(other_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.fixture
def category(user):
    return Category.objects.create(
        user=user,
        name="Alimentacao",
        is_active=True,
    )


@pytest.fixture
def other_category(other_user):
    return Category.objects.create(
        user=other_user,
        name="Transporte",
        is_active=True,
    )


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
def llm_response_completo(category, card):
    return {
        "name": "Almoco",
        "amount": 45.90,
        "type": "saida",
        "category": {"id": str(category.id), "name": category.name},
        "date": "2024-06-15",
        "description": "Almoco com colegas",
        "card": {"id": str(card.id), "name": card.name},
        "missing_fields": [],
    }


@pytest.fixture
def interaction_pendente(user, llm_response_completo):
    return AssistantInteraction.objects.create(
        user=user,
        input_type="texto",
        input_content="Almoco no restaurante 45.90",
        llm_response=llm_response_completo,
        status="pendente",
    )


# ---------------------------------------------------------------------------
# TestTextAPI
# ---------------------------------------------------------------------------

class TestTextAPI:
    @patch("apps.assistant.api_views.interpret_transaction")
    def test_text_api_com_jwt(self, mock_interpret, auth_client, llm_response_completo):
        """POST /api/v1/assistant/text/ com JWT valido retorna 200 com preview."""
        mock_interpret.return_value = llm_response_completo

        response = auth_client.post(
            "/api/v1/assistant/text/",
            data={"message": "Almoco no restaurante 45.90"},
            format="json",
        )

        assert response.status_code == 200
        assert "interaction_id" in response.data
        assert "preview" in response.data

    def test_text_api_sem_jwt(self, api_client):
        """POST /api/v1/assistant/text/ sem JWT retorna 401."""
        response = api_client.post(
            "/api/v1/assistant/text/",
            data={"message": "Algum texto"},
            format="json",
        )
        assert response.status_code == 401

    def test_audio_api_sem_jwt(self, api_client):
        """POST /api/v1/assistant/audio/ sem JWT retorna 401."""
        response = api_client.post("/api/v1/assistant/audio/", format="multipart")
        assert response.status_code == 401

    def test_confirm_api_sem_jwt(self, api_client):
        """POST /api/v1/assistant/confirm/<uuid>/ sem JWT retorna 401."""
        import uuid
        response = api_client.post(f"/api/v1/assistant/confirm/{uuid.uuid4()}/", format="json")
        assert response.status_code == 401

    def test_cancel_api_sem_jwt(self, api_client):
        """POST /api/v1/assistant/cancel/<uuid>/ sem JWT retorna 401."""
        import uuid
        response = api_client.post(f"/api/v1/assistant/cancel/{uuid.uuid4()}/", format="json")
        assert response.status_code == 401

    def test_history_api_sem_jwt(self, api_client):
        """GET /api/v1/assistant/history/ sem JWT retorna 401."""
        response = api_client.get("/api/v1/assistant/history/")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# TestAudioAPI
# ---------------------------------------------------------------------------

class TestAudioAPI:
    @patch("apps.assistant.api_views.interpret_transaction")
    @patch("apps.assistant.api_views.transcribe_audio")
    def test_audio_api_com_jwt(self, mock_transcribe, mock_interpret, auth_client, llm_response_completo):
        """POST /api/v1/assistant/audio/ com JWT + mock Whisper + mock GPT."""
        mock_transcribe.return_value = "Gastei cinquenta reais no mercado"
        mock_interpret.return_value = llm_response_completo

        audio_file = BytesIO(b"fake audio content")
        audio_file.name = "audio.webm"

        response = auth_client.post(
            "/api/v1/assistant/audio/",
            data={"audio": audio_file},
            format="multipart",
        )

        assert response.status_code == 200
        assert "interaction_id" in response.data


# ---------------------------------------------------------------------------
# TestConfirmAPI
# ---------------------------------------------------------------------------

class TestConfirmAPI:
    def test_confirm_api(self, auth_client, interaction_pendente, category, card):
        """POST /api/v1/assistant/confirm/<uuid>/ com JWT confirma e cria transação."""
        response = auth_client.post(
            f"/api/v1/assistant/confirm/{interaction_pendente.id}/",
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "confirmed"
        assert "transaction_id" in response.data

        interaction_pendente.refresh_from_db()
        assert interaction_pendente.status == "confirmado"
        assert interaction_pendente.transaction is not None


# ---------------------------------------------------------------------------
# TestCancelAPI
# ---------------------------------------------------------------------------

class TestCancelAPI:
    def test_cancel_api(self, auth_client, interaction_pendente):
        """POST /api/v1/assistant/cancel/<uuid>/ com JWT cancela interação."""
        response = auth_client.post(
            f"/api/v1/assistant/cancel/{interaction_pendente.id}/",
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "cancelled"

        interaction_pendente.refresh_from_db()
        assert interaction_pendente.status == "cancelado"


# ---------------------------------------------------------------------------
# TestHistoryAPI
# ---------------------------------------------------------------------------

class TestHistoryAPI:
    def test_history_api(self, auth_client, user):
        """GET /api/v1/assistant/history/ com JWT retorna lista de interações."""
        # Cria algumas interações para o usuário
        for i in range(3):
            AssistantInteraction.objects.create(
                user=user,
                input_type="texto",
                input_content=f"Mensagem {i}",
                llm_response={"name": f"Item {i}", "missing_fields": []},
                status="pendente",
            )

        response = auth_client.get("/api/v1/assistant/history/")

        assert response.status_code == 200
        assert len(response.data) == 3


# ---------------------------------------------------------------------------
# TestTenantIsolation
# ---------------------------------------------------------------------------

class TestTenantIsolation:
    def test_tenant_isolation_api(self, auth_client_other, interaction_pendente):
        """User B não consegue confirmar interação do User A."""
        response = auth_client_other.post(
            f"/api/v1/assistant/confirm/{interaction_pendente.id}/",
            format="json",
        )

        assert response.status_code == 400
        assert "permissão" in response.data["detail"].lower() or "permiss" in response.data["detail"].lower()

        # Interação permanece pendente
        interaction_pendente.refresh_from_db()
        assert interaction_pendente.status == "pendente"
