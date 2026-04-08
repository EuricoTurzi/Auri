from apps.accounts.models import CustomUser


def get_user_by_email(email):
    """Busca usuário ativo por e-mail. Levanta DoesNotExist se não encontrado."""
    return CustomUser.objects.get(email=email, is_active=True)


def get_user_by_id(user_id):
    """Busca usuário ativo por UUID. Levanta DoesNotExist se não encontrado."""
    return CustomUser.objects.get(id=user_id, is_active=True)
