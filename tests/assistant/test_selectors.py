"""
Testes dos selectors do app assistant.
"""
import pytest
from decimal import Decimal

from django.http import Http404

from apps.accounts.models import CustomUser
from apps.assistant.models import AssistantInteraction
from apps.assistant.selectors import get_user_interactions, get_interaction_by_id


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        email="selector@test.com",
        nickname="selectoruser",
        password="pass12345",
    )


@pytest.fixture
def other_user(db):
    return CustomUser.objects.create_user(
        email="selectorother@test.com",
        nickname="selectorother",
        password="pass12345",
    )


@pytest.fixture
def interaction_user(user):
    return AssistantInteraction.objects.create(
        user=user,
        input_type="texto",
        input_content="Almoco 45",
        llm_response={"missing_fields": []},
        status="pendente",
    )


@pytest.fixture
def interaction_other(other_user):
    return AssistantInteraction.objects.create(
        user=other_user,
        input_type="texto",
        input_content="Compra do outro",
        llm_response={"missing_fields": []},
        status="pendente",
    )


class TestGetUserInteractions:
    def test_tenant_isolation(self, user, other_user, interaction_user, interaction_other):
        """User A só vê suas próprias interações, não as do User B."""
        qs = get_user_interactions(user)
        ids = list(qs.values_list("id", flat=True))
        assert interaction_user.id in ids
        assert interaction_other.id not in ids

    def test_filtro_status(self, user):
        """Filtro por status retorna apenas registros com aquele status."""
        AssistantInteraction.objects.create(
            user=user,
            input_type="texto",
            input_content="pendente",
            llm_response={"missing_fields": []},
            status="pendente",
        )
        AssistantInteraction.objects.create(
            user=user,
            input_type="texto",
            input_content="confirmado",
            llm_response={"missing_fields": []},
            status="confirmado",
        )

        pendentes = get_user_interactions(user, status="pendente")
        confirmados = get_user_interactions(user, status="confirmado")

        assert all(i.status == "pendente" for i in pendentes)
        assert all(i.status == "confirmado" for i in confirmados)


class TestGetInteractionById:
    def test_sucesso(self, user, interaction_user):
        """Retorna a interação correta para o user correto."""
        result = get_interaction_by_id(interaction_user.id, user)
        assert result.id == interaction_user.id

    def test_usuario_errado_levanta_404(self, other_user, interaction_user):
        """Levantar Http404 quando outro user tenta acessar a interação."""
        with pytest.raises(Http404):
            get_interaction_by_id(interaction_user.id, other_user)
