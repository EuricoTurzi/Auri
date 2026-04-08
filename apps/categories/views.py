from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from apps.categories.models import Category
from apps.categories.selectors import get_category_by_id, get_user_categories
from apps.categories.services import (
    create_category,
    deactivate_category,
    update_category,
)

DEFAULT_COLOR = '#c9a84c'


def _form_context(action, post_data=None, category=None):
    """Constrói contexto padrão para o formulário de categoria."""
    if post_data is not None:
        return {
            'action': action,
            'initial_name': post_data.get('name', ''),
            'initial_description': post_data.get('description', ''),
            'initial_color': post_data.get('color', DEFAULT_COLOR),
            'initial_icon': post_data.get('icon', ''),
        }
    if category is not None:
        return {
            'action': action,
            'initial_name': category.name,
            'initial_description': category.description or '',
            'initial_color': category.color or DEFAULT_COLOR,
            'initial_icon': category.icon or '',
        }
    return {
        'action': action,
        'initial_name': '',
        'initial_description': '',
        'initial_color': DEFAULT_COLOR,
        'initial_icon': '',
    }


class CategoryListView(LoginRequiredMixin, View):
    """GET /categories/ — lista categorias ativas do usuário."""

    def get(self, request):
        categories = get_user_categories(request.user, active_only=True)
        return render(request, 'categories/category_list.html', {'categories': categories})


class CategoryCreateView(LoginRequiredMixin, View):
    """GET/POST /categories/create/ — formulário de criação de categoria."""

    def get(self, request):
        return render(request, 'categories/category_form.html', _form_context('create'))

    def post(self, request):
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip() or None
        color = request.POST.get('color', '').strip() or None
        icon = request.POST.get('icon', '').strip() or None

        if not name:
            messages.error(request, 'O nome da categoria é obrigatório.')
            return render(request, 'categories/category_form.html',
                          _form_context('create', post_data=request.POST))

        try:
            create_category(request.user, name, description=description, color=color, icon=icon)
            messages.success(request, f'Categoria "{name}" criada com sucesso.')
            return redirect('categories:list')
        except Exception as e:
            messages.error(request, str(e))
            return render(request, 'categories/category_form.html',
                          _form_context('create', post_data=request.POST))


class CategoryUpdateView(LoginRequiredMixin, View):
    """GET/POST /categories/<uuid:pk>/edit/ — formulário de edição de categoria."""

    def get(self, request, pk):
        try:
            category = get_category_by_id(pk, request.user)
        except Category.DoesNotExist:
            messages.error(request, 'Categoria não encontrada.')
            return redirect('categories:list')
        return render(request, 'categories/category_form.html',
                      _form_context('edit', category=category))

    def post(self, request, pk):
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip() or None
        color = request.POST.get('color', '').strip() or None
        icon = request.POST.get('icon', '').strip() or None

        if not name:
            messages.error(request, 'O nome da categoria é obrigatório.')
            return render(request, 'categories/category_form.html',
                          _form_context('edit', post_data=request.POST))

        try:
            update_category(pk, request.user, name=name, description=description, color=color, icon=icon)
            messages.success(request, f'Categoria "{name}" atualizada com sucesso.')
            return redirect('categories:list')
        except PermissionError:
            messages.error(request, 'Categoria não encontrada.')
            return redirect('categories:list')
        except Exception as e:
            messages.error(request, str(e))
            try:
                category = get_category_by_id(pk, request.user)
            except Category.DoesNotExist:
                return redirect('categories:list')
            return render(request, 'categories/category_form.html',
                          _form_context('edit', category=category))


class CategoryDeleteView(LoginRequiredMixin, View):
    """POST /categories/<uuid:pk>/delete/ — soft-delete de categoria."""

    def post(self, request, pk):
        try:
            deactivate_category(pk, request.user)
            messages.success(request, 'Categoria removida com sucesso.')
        except PermissionError:
            messages.error(request, 'Categoria não encontrada.')
        return redirect('categories:list')
