import pytest
from django.test import Client

from apps.accounts.models import CustomUser
from apps.categories.models import Category


@pytest.fixture
def user(db):
    user = CustomUser.objects.create_user(
        email='view@test.com',
        nickname='viewuser',
        password='pass12345',
    )
    user.is_first_access = False
    user.save()
    return user


@pytest.fixture
def other_user(db):
    other = CustomUser.objects.create_user(
        email='other@test.com',
        nickname='otheruser',
        password='pass12345',
    )
    other.is_first_access = False
    other.save()
    return other


@pytest.fixture
def client_auth(user):
    client = Client()
    client.login(username='view@test.com', password='pass12345')
    return client


@pytest.fixture
def category(user):
    return Category.objects.create(user=user, name='Alimentação', color='#4CAF50')


class TestCategoryListView:
    def test_acesso_autenticado_retorna_200(self, client_auth):
        response = client_auth.get('/categories/')
        assert response.status_code == 200

    def test_acesso_nao_autenticado_redireciona(self, db):
        client = Client()
        response = client.get('/categories/')
        assert response.status_code == 302

    def test_lista_apenas_categorias_ativas_do_usuario(self, client_auth, user, other_user):
        Category.objects.create(user=user, name='Ativa', is_active=True)
        Category.objects.create(user=user, name='Inativa', is_active=False)
        Category.objects.create(user=other_user, name='Outro usuario')

        response = client_auth.get('/categories/')
        categories = response.context['categories']
        names = [c.name for c in categories]

        assert 'Ativa' in names
        assert 'Inativa' not in names
        assert 'Outro usuario' not in names


class TestCategoryCreateView:
    def test_get_retorna_formulario(self, client_auth):
        response = client_auth.get('/categories/create/')
        assert response.status_code == 200

    def test_post_valido_cria_e_redireciona(self, client_auth, user):
        response = client_auth.post('/categories/create/', {
            'name': 'Transporte',
            'color': '#2196F3',
        })
        assert response.status_code == 302
        assert response['Location'] == '/categories/'
        assert Category.objects.filter(user=user, name='Transporte').exists()

    def test_post_nome_duplicado_retorna_formulario(self, client_auth, user, category):
        response = client_auth.post('/categories/create/', {'name': 'Alimentação'})
        assert response.status_code == 200

    def test_post_sem_nome_retorna_formulario(self, client_auth):
        response = client_auth.post('/categories/create/', {'name': ''})
        assert response.status_code == 200


class TestCategoryUpdateView:
    def test_get_retorna_formulario(self, client_auth, category):
        response = client_auth.get(f'/categories/{category.pk}/edit/')
        assert response.status_code == 200

    def test_post_valido_atualiza_e_redireciona(self, client_auth, category):
        response = client_auth.post(f'/categories/{category.pk}/edit/', {
            'name': 'Comida',
            'color': '#4CAF50',
        })
        assert response.status_code == 302
        category.refresh_from_db()
        assert category.name == 'Comida'

    def test_nao_pode_editar_categoria_de_outro_usuario(self, client_auth, other_user):
        other_cat = Category.objects.create(user=other_user, name='Outro')
        response = client_auth.post(f'/categories/{other_cat.pk}/edit/', {'name': 'Hack'})
        assert response.status_code == 302
        other_cat.refresh_from_db()
        assert other_cat.name == 'Outro'


class TestCategoryDeleteView:
    def test_post_desativa_categoria(self, client_auth, category):
        response = client_auth.post(f'/categories/{category.pk}/delete/')
        assert response.status_code == 302
        category.refresh_from_db()
        assert category.is_active is False

    def test_categoria_desativada_nao_aparece_na_listagem(self, client_auth, user):
        cat = Category.objects.create(user=user, name='Temp')
        client_auth.post(f'/categories/{cat.pk}/delete/')
        response = client_auth.get('/categories/')
        names = [c.name for c in response.context['categories']]
        assert 'Temp' not in names

    def test_nao_pode_deletar_categoria_de_outro_usuario(self, client_auth, other_user):
        other_cat = Category.objects.create(user=other_user, name='Outro')
        client_auth.post(f'/categories/{other_cat.pk}/delete/')
        other_cat.refresh_from_db()
        assert other_cat.is_active is True
