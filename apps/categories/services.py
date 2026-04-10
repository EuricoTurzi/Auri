from django.core.exceptions import ValidationError

from apps.categories.models import Category


def create_category(user, name, description=None, color=None, icon=None):
    """
    Cria categoria para o usuário. Levanta ValidationError se nome duplicado.
    """
    name = name.strip()
    if Category.objects.filter(user=user, name=name, is_active=True).exists():
        raise ValidationError('Já existe uma categoria com este nome.')
    return Category.objects.create(
        user=user,
        name=name,
        description=description,
        color=color,
        icon=icon,
    )


def update_category(category_id, user, **kwargs):
    """
    Atualiza campos da categoria. Levanta PermissionError se não pertence ao usuário.
    Levanta ValidationError se novo nome já existe.
    """
    try:
        category = Category.objects.get(id=category_id, user=user)
    except Category.DoesNotExist:
        raise PermissionError('Categoria não encontrada ou não pertence ao usuário.')

    if 'name' in kwargs:
        new_name = kwargs['name'].strip()
        kwargs['name'] = new_name
        if Category.objects.filter(user=user, name=new_name, is_active=True).exclude(id=category_id).exists():
            raise ValidationError('Já existe uma categoria com este nome.')

    for field, value in kwargs.items():
        setattr(category, field, value)

    category.save()
    return category


def deactivate_category(category_id, user):
    """
    Soft-delete via is_active=False. Levanta PermissionError se não pertence ao usuário.
    """
    try:
        category = Category.objects.get(id=category_id, user=user)
    except Category.DoesNotExist:
        raise PermissionError('Categoria não encontrada ou não pertence ao usuário.')

    category.is_active = False
    category.save(update_fields=['is_active', 'updated_at'])
    return category
