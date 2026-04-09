"""
Testes das views SSR do app assistant.
"""
import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client

from apps.accounts.models import CustomUser
from apps.assistant.models import AssistantInteraction
from apps.cards.models import Card
from apps.categories.models import Category


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    u = CustomUser.objects.create_user(
        email="viewuser@test.com",
        nickname="viewuser",
        password="pass12345",
    )
    u.is_first_access = False
    u.save()
    return u


@pytest.fixture
def other_user(db):
    return CustomUser.objects.create_user(
        email="viewother@test.com",
        nickname="viewother",
        password="pass12345",
    )


@pytest.fixture
def category(user):
    return Category.objects.create(
        user=user,
        name="Alimentacao",
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
def auth_client(user):
    client = Client()
    client.login(email="viewuser@test.com", password="pass12345")
    return client


@pytest.fixture
def anon_client():
    return Client()


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
def llm_response_faltando():
    return {
        "name": "Compra",
        "amount": None,
        "type": "saida",
        "category": None,
        "date": None,
        "description": None,
        "card": None,
        "missing_fields": ["amount", "category"],
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
# TestAssistantView
# ---------------------------------------------------------------------------

class TestAssistantView:
    def test_assistant_view_get(self, auth_client):
        """GET /assistant/ retorna 200 para user autenticado."""
        response = auth_client.get("/assistant/")
        assert response.status_code == 200

    def test_assistant_view_nao_autenticado(self, anon_client):
        """GET /assistant/ redireciona para user não autenticado."""
        response = anon_client.get("/assistant/")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# TestAssistantTextView
# ---------------------------------------------------------------------------

class TestAssistantTextView:
    @patch("apps.assistant.views.interpret_transaction")
    def test_text_view_post_completo(self, mock_interpret, auth_client, llm_response_completo):
        """POST /assistant/text/ com dados completos retorna JSON com status=preview."""
        mock_interpret.return_value = llm_response_completo

        response = auth_client.post(
            "/assistant/text/",
            data=json.dumps({"message": "Almoco no restaurante 45.90"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "preview"
        assert "interaction_id" in data
        assert data["data"]["name"] == "Almoco"

    @patch("apps.assistant.views.interpret_transaction")
    def test_text_view_post_faltando_dados(self, mock_interpret, auth_client, llm_response_faltando):
        """POST /assistant/text/ com missing_fields retorna JSON com status=missing."""
        mock_interpret.return_value = llm_response_faltando

        response = auth_client.post(
            "/assistant/text/",
            data=json.dumps({"message": "Fiz uma compra"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "missing"
        assert "amount" in data["missing_fields"]
        assert "category" in data["missing_fields"]


# ---------------------------------------------------------------------------
# TestAssistantAudioView
# ---------------------------------------------------------------------------

class TestAssistantAudioView:
    @patch("apps.assistant.views.interpret_transaction")
    @patch("apps.assistant.views.transcribe_audio")
    def test_audio_view_post(self, mock_transcribe, mock_interpret, auth_client, llm_response_completo):
        """POST /assistant/audio/ com mock Whisper + mock GPT retorna JSON."""
        mock_transcribe.return_value = "Gastei cinquenta reais no mercado"
        mock_interpret.return_value = llm_response_completo

        from io import BytesIO
        audio_file = BytesIO(b"fake audio content")
        audio_file.name = "audio.webm"

        response = auth_client.post(
            "/assistant/audio/",
            data={"audio": audio_file},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "preview"
        assert "interaction_id" in data


# ---------------------------------------------------------------------------
# TestAssistantConfirmView
# ---------------------------------------------------------------------------

class TestAssistantConfirmView:
    def test_confirm_view(self, auth_client, interaction_pendente, category, card):
        """POST /assistant/confirm/<uuid>/ cria transação."""
        response = auth_client.post(
            f"/assistant/confirm/{interaction_pendente.id}/",
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"
        assert "transaction_id" in data

        interaction_pendente.refresh_from_db()
        assert interaction_pendente.status == "confirmado"


# ---------------------------------------------------------------------------
# TestAssistantCancelView
# ---------------------------------------------------------------------------

class TestAssistantCancelView:
    def test_cancel_view(self, auth_client, interaction_pendente):
        """POST /assistant/cancel/<uuid>/ cancela interação."""
        response = auth_client.post(
            f"/assistant/cancel/{interaction_pendente.id}/",
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        interaction_pendente.refresh_from_db()
        assert interaction_pendente.status == "cancelado"
