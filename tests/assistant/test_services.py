"""
Testes unitários para services do app assistant.

Todas as chamadas à API OpenAI são mockadas — nenhuma requisição real é feita.
"""
import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import openai
import pytest

from apps.accounts.models import CustomUser
from apps.assistant.models import AssistantInteraction
from apps.assistant.services import (
    ServiceError,
    build_system_prompt,
    cancel_interaction,
    confirm_interaction,
    create_interaction,
    interpret_transaction,
    transcribe_audio,
)
from apps.cards.models import Card
from apps.categories.models import Category
from apps.transactions.models import Transaction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        email="assistant@test.com",
        nickname="assistantuser",
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
def llm_response_completo(category, card):
    """Resposta completa da LLM com todos os campos preenchidos."""
    return {
        "name": "Almoco no restaurante",
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
    """Interacao pendente criada para testes de confirm/cancel."""
    return AssistantInteraction.objects.create(
        user=user,
        input_type="texto",
        input_content="Almoco no restaurante 45.90",
        llm_response=llm_response_completo,
        status="pendente",
    )


# ---------------------------------------------------------------------------
# TestTranscribeAudio
# ---------------------------------------------------------------------------

class TestTranscribeAudio:
    @patch("apps.assistant.services.openai.OpenAI")
    @patch("apps.assistant.services.settings")
    def test_transcribe_audio_sucesso(self, mock_settings, mock_openai_cls):
        """Mock Whisper retorna texto transcrito com sucesso."""
        mock_settings.OPENAI_API_KEY = "fake-key"

        mock_response = MagicMock()
        mock_response.text = "Gastei cinquenta reais no mercado"
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        audio_file = MagicMock(name="audio.webm")
        resultado = transcribe_audio(audio_file)

        assert resultado == "Gastei cinquenta reais no mercado"
        mock_client.audio.transcriptions.create.assert_called_once()

    @patch("apps.assistant.services.openai.OpenAI")
    @patch("apps.assistant.services.settings")
    def test_transcribe_audio_erro_api(self, mock_settings, mock_openai_cls):
        """Erro na API OpenAI levanta ServiceError."""
        mock_settings.OPENAI_API_KEY = "fake-key"

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = openai.OpenAIError("API error")
        mock_openai_cls.return_value = mock_client

        audio_file = MagicMock(name="audio.webm")
        with pytest.raises(ServiceError):
            transcribe_audio(audio_file)


# ---------------------------------------------------------------------------
# TestInterpretTransaction
# ---------------------------------------------------------------------------

class TestInterpretTransaction:
    @patch("apps.assistant.services.openai.OpenAI")
    @patch("apps.assistant.services.settings")
    def test_interpret_transaction_completo(self, mock_settings, mock_openai_cls, user, category, card):
        """Mock GPT retorna JSON completo com todos os campos preenchidos."""
        mock_settings.OPENAI_API_KEY = "fake-key"

        gpt_json = {
            "name": "Almoco",
            "amount": 45.90,
            "type": "saida",
            "category": {"id": str(category.id), "name": category.name},
            "date": "2024-06-15",
            "description": "Almoco com colegas",
            "card": {"id": str(card.id), "name": card.name},
            "missing_fields": [],
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(gpt_json)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        resultado = interpret_transaction(user, "Almoco no restaurante 45.90")

        assert resultado["name"] == "Almoco"
        assert resultado["amount"] == 45.90
        assert resultado["type"] == "saida"
        assert resultado["missing_fields"] == []
        assert resultado["category"]["id"] == str(category.id)

    @patch("apps.assistant.services.openai.OpenAI")
    @patch("apps.assistant.services.settings")
    def test_interpret_transaction_faltando_campos(self, mock_settings, mock_openai_cls, user):
        """Mock GPT retorna JSON com campos null e missing_fields populado."""
        mock_settings.OPENAI_API_KEY = "fake-key"

        gpt_json = {
            "name": "Compra",
            "amount": None,
            "type": "saida",
            "category": None,
            "date": None,
            "description": None,
            "card": None,
            "missing_fields": ["amount", "category"],
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(gpt_json)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        resultado = interpret_transaction(user, "Fiz uma compra")

        assert resultado["amount"] is None
        assert resultado["category"] is None
        assert "amount" in resultado["missing_fields"]
        assert "category" in resultado["missing_fields"]

    @patch("apps.assistant.services.openai.OpenAI")
    @patch("apps.assistant.services.settings")
    def test_interpret_transaction_erro_api(self, mock_settings, mock_openai_cls, user):
        """Erro na API OpenAI levanta ServiceError."""
        mock_settings.OPENAI_API_KEY = "fake-key"

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.OpenAIError("API error")
        mock_openai_cls.return_value = mock_client

        with pytest.raises(ServiceError):
            interpret_transaction(user, "Algum texto")


    @patch("apps.assistant.services.openai.OpenAI")
    @patch("apps.assistant.services.settings")
    def test_interpret_transaction_entrada(self, mock_settings, mock_openai_cls, user):
        """Mock GPT retorna type=entrada (ex: recebi 3000 de salário)."""
        mock_settings.OPENAI_API_KEY = "fake-key"

        gpt_json = {
            "name": "Salário",
            "amount": 3000.0,
            "type": "entrada",
            "category": None,
            "date": "2024-06-01",
            "description": "Salário mensal",
            "card": None,
            "missing_fields": [],
        }

        mock_message = MagicMock()
        mock_message.content = json.dumps(gpt_json)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        resultado = interpret_transaction(user, "recebi 3000 de salário dia primeiro")

        assert resultado["type"] == "entrada"
        assert resultado["amount"] == 3000.0
        assert resultado["name"] == "Salário"
        assert resultado["missing_fields"] == []


class TestBuildSystemPrompt:
    def test_build_system_prompt_inclui_categorias_e_cartoes(self, user, category, card):
        """O prompt do sistema contém os nomes das categorias e cartões do usuário."""
        prompt = build_system_prompt(user)

        assert category.name in prompt
        assert card.name in prompt
        assert "Alimentacao" in prompt
        assert "Nubank" in prompt


# ---------------------------------------------------------------------------
# TestCreateInteraction
# ---------------------------------------------------------------------------

class TestCreateInteraction:
    def test_create_interaction(self, user, llm_response_completo):
        """Cria interação pendente e valida campos."""
        interaction = create_interaction(
            user=user,
            input_type="texto",
            input_content="Almoco no restaurante 45.90",
            llm_response=llm_response_completo,
        )

        assert interaction.user == user
        assert interaction.input_type == "texto"
        assert interaction.input_content == "Almoco no restaurante 45.90"
        assert interaction.llm_response == llm_response_completo
        assert interaction.status == "pendente"
        assert interaction.transaction is None


# ---------------------------------------------------------------------------
# TestConfirmInteraction
# ---------------------------------------------------------------------------

class TestConfirmInteraction:
    def test_confirm_interaction_cria_transacao(self, user, interaction_pendente, category, card):
        """Confirma interação pendente e valida que transação foi criada."""
        transaction = confirm_interaction(interaction_pendente.id, user)

        assert isinstance(transaction, Transaction)
        assert transaction.name == "Almoco no restaurante"
        assert transaction.user == user

        interaction_pendente.refresh_from_db()
        assert interaction_pendente.status == "confirmado"
        assert interaction_pendente.transaction == transaction

    def test_confirm_interaction_dados_ajustados(self, user, interaction_pendente, category, card):
        """Confirma com adjusted_data e valida que os dados ajustados foram usados."""
        adjusted = {
            "name": "Jantar ajustado",
            "amount": 99.99,
            "type": "saida",
            "category": {"id": str(category.id), "name": category.name},
            "date": "2024-07-20",
            "description": "Dados ajustados pelo usuario",
            "card": {"id": str(card.id), "name": card.name},
        }

        transaction = confirm_interaction(interaction_pendente.id, user, adjusted_data=adjusted)

        assert transaction.name == "Jantar ajustado"
        assert float(transaction.amount) == pytest.approx(99.99)

    def test_confirm_interaction_usuario_errado(self, other_user, interaction_pendente):
        """Tentar confirmar interação de outro user levanta ServiceError."""
        with pytest.raises(ServiceError, match="Sem permissão"):
            confirm_interaction(interaction_pendente.id, other_user)

    def test_confirm_interaction_normaliza_amount_string(self, user, interaction_pendente, category, card):
        """Amount vindo como string (adjusted_data do front) deve ser convertido para Decimal."""
        adjusted = {
            "name": "Ajustado",
            "amount": "150.75",  # string, como vem do JSON.stringify
            "type": "saida",
            "category": {"id": str(category.id), "name": category.name},
            "date": "2024-07-20",
            "description": "",
            "card": {"id": str(card.id), "name": card.name},
        }
        transaction = confirm_interaction(interaction_pendente.id, user, adjusted_data=adjusted)
        assert transaction.amount == Decimal("150.75")

    def test_confirm_interaction_normaliza_date_string_para_recorrencia(
        self, user, interaction_pendente, category, card
    ):
        """Date como string não deve quebrar create_recurring_transaction."""
        adjusted = {
            "name": "Recorrente",
            "amount": "200.00",
            "type": "saida",
            "category": {"id": str(category.id), "name": category.name},
            "date": "2026-04-10",  # string, não date
            "description": "",
            "card": {"id": str(card.id), "name": card.name},
            "is_recurring": True,
            "frequency": "mensal",
        }
        transaction = confirm_interaction(interaction_pendente.id, user, adjusted_data=adjusted)
        assert transaction.is_recurring is True
        assert transaction.date == date(2026, 4, 10)
        # Deve ter criado ocorrências filhas (12 meses)
        filhas = Transaction.objects.filter(recurring_parent=transaction)
        assert filhas.count() >= 11

    def test_confirm_interaction_normaliza_amount_e_date_para_parcelamento(
        self, user, interaction_pendente, category, card
    ):
        """Amount+date como string não deve quebrar create_installment_transaction."""
        adjusted = {
            "name": "Parcelado",
            "amount": "300.00",
            "type": "saida",
            "category": {"id": str(category.id), "name": category.name},
            "date": "2026-04-10",
            "description": "",
            "card": {"id": str(card.id), "name": card.name},
            "is_installment": True,
            "total_installments": 3,
        }
        transaction = confirm_interaction(interaction_pendente.id, user, adjusted_data=adjusted)
        assert transaction.is_installment is True
        assert transaction.amount == Decimal("300.00")
        # 3 parcelas filhas criadas
        filhas = Transaction.objects.filter(recurring_parent=transaction, is_installment=True)
        assert filhas.count() == 3


# ---------------------------------------------------------------------------
# TestCancelInteraction
# ---------------------------------------------------------------------------

class TestCancelInteraction:
    def test_cancel_interaction(self, user, interaction_pendente):
        """Cancela interação e valida status e ausência de transação."""
        result = cancel_interaction(interaction_pendente.id, user)

        assert result.status == "cancelado"
        interaction_pendente.refresh_from_db()
        assert interaction_pendente.status == "cancelado"
        assert interaction_pendente.transaction is None

        # Nenhuma transação deve ter sido criada
        assert Transaction.objects.filter(
            assistant_interactions=interaction_pendente
        ).count() == 0
