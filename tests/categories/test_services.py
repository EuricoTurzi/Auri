import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import CustomUser
from apps.categories.models import Category
from apps.categories.services import create_category, deactivate_category, update_category


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        email='user@test.com',
        nickname='testuser',
        password='pass12345',
    )


@pytest.fixture
def other_user(db):
    return CustomUser.objects.create_user(
        email='other@test.com',
        nickname='otheruser',
        password='pass12345',
    )


@pytest.fixture
def category(user):
    return Category.objects.create(user=user, name='Alimentação', color='#4CAF50')


class TestCreateCategory:
    def test_cria_categoria_com_dados_validos(self, user):
        cat = create_category(user, 'Alimentação', description='Comida', color='#4CAF50', icon='🍔')
        assert cat.name == 'Alimentação'
        assert cat.description == 'Comida'
        assert cat.color == '#4CAF50'
        assert cat.icon == '🍔'
        assert cat.user == user
        assert cat.is_active is True

    def test_cria_categoria_apenas_com_nome(self, user):
        cat = create_category(user, 'Transporte')
        assert cat.name == 'Transporte'
        assert cat.description is None
        assert cat.color is None

    def test_trime_espacos_do_nome(self, user):
        cat = create_category(user, '  Saúde  ')
        assert cat.name == 'Saúde'

    def test_levanta_validation_error_nome_duplicado(self, user, category):
        with pytest.raises(ValidationError):
            create_category(user, 'Alimentação')

    def test_permite_mesmo_nome_para_usuarios_diferentes(self, user, other_user):
        create_category(user, 'Alimentação')
        cat2 = create_category(other_user, 'Alimentação')
        assert cat2.name == 'Alimentação'

    def test_permite_recriar_nome_de_categoria_inativada(self, user, category):
        # Inativa a categoria existente (soft-delete)
        deactivate_category(category.id, user)
        # Deve ser possível criar nova categoria com o mesmo nome
        nova = create_category(user, 'Alimentação')
        assert nova.id != category.id
        assert nova.is_active is True
        assert nova.name == 'Alimentação'


class TestUpdateCategory:
    def test_atualiza_campos_da_categoria(self, user, category):
        updated = update_category(category.id, user, description='Gastos com comida')
        assert updated.description == 'Gastos com comida'

    def test_atualiza_nome_valido(self, user, category):
        updated = update_category(category.id, user, name='Comida')
        assert updated.name == 'Comida'

    def test_trime_espacos_do_nome_na_atualizacao(self, user, category):
        updated = update_category(category.id, user, name='  Comida  ')
        assert updated.name == 'Comida'

    def test_levanta_validation_error_nome_duplicado(self, user, category):
        Category.objects.create(user=user, name='Transporte')
        with pytest.raises(ValidationError):
            update_category(category.id, user, name='Transporte')

    def test_permite_renomear_para_nome_de_categoria_inativada(self, user, category):
        inativa = Category.objects.create(user=user, name='Transporte', is_active=False)
        # Deve permitir renomear para um nome que só existe em categoria inativa
        updated = update_category(category.id, user, name='Transporte')
        assert updated.name == 'Transporte'
        assert updated.id == category.id
        # A inativa permanece no banco, inalterada
        inativa.refresh_from_db()
        assert inativa.is_active is False

    def test_levanta_permission_error_para_outro_usuario(self, user, other_user, category):
        with pytest.raises(PermissionError):
            update_category(category.id, other_user, name='Outro')

    def test_atualiza_propria_categoria_sem_erro_unicidade(self, user, category):
        updated = update_category(category.id, user, name='Alimentação', description='Atualizada')
        assert updated.name == 'Alimentação'
        assert updated.description == 'Atualizada'


class TestDeactivateCategory:
    def test_desativa_categoria(self, user, category):
        result = deactivate_category(category.id, user)
        assert result.is_active is False
        category.refresh_from_db()
        assert category.is_active is False

    def test_levanta_permission_error_para_outro_usuario(self, user, other_user, category):
        with pytest.raises(PermissionError):
            deactivate_category(category.id, other_user)

    def test_categoria_permanece_no_banco_apos_desativacao(self, user, category):
        deactivate_category(category.id, user)
        assert Category.objects.filter(id=category.id).exists()
