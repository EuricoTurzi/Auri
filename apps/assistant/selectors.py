from django.db.models import QuerySet
from django.http import Http404

from apps.assistant.models import AssistantInteraction


def get_user_interactions(user, status=None) -> QuerySet:
    """
    Retorna interações do usuário, opcionalmente filtradas por status.
    Tenant isolation: filtra por user.
    """
    qs = AssistantInteraction.objects.filter(user=user)

    if status is not None:
        qs = qs.filter(status=status)

    return qs


def get_interaction_by_id(interaction_id, user) -> AssistantInteraction:
    """
    Retorna interação por ID, validando ownership (user).
    Levanta Http404 se não encontrada ou não pertencer ao usuário.
    """
    try:
        return AssistantInteraction.objects.get(id=interaction_id, user=user)
    except AssistantInteraction.DoesNotExist:
        raise Http404(
            f"Interação {interaction_id} não encontrada ou não pertence ao usuário."
        )
