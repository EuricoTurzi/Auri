from apps.categories.models import Category


def get_user_categories(user, active_only=True):
    """Retorna categorias do usuário, filtradas por is_active quando active_only=True. Ordenadas por nome."""
    qs = Category.objects.filter(user=user)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by('name')


def get_category_by_id(category_id, user):
    """
    Retorna categoria por ID validando que pertence ao usuário.
    Levanta Category.DoesNotExist se não encontrada ou não pertence ao usuário.
    """
    return Category.objects.get(id=category_id, user=user)
