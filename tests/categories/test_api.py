import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.categories.models import Category


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        email='api@test.com',
        nickname='apiuser',
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
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


@pytest.fixture
def category(user):
    return Category.objects.create(user=user, name='Alimentação', color='#4CAF50')


class TestCategoryListCreateAPI:
    def test_get_sem_jwt_retorna_401(self, api_client):
        response = api_client.get('/api/v1/categories/')
        assert response.status_code == 401

    def test_get_com_jwt_retorna_lista(self, auth_client, category):
        response = auth_client.get('/api/v1/categories/')
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['name'] == 'Alimentação'

    def test_get_nao_retorna_categorias_inativas(self, auth_client, user):
        Category.objects.create(user=user, name='Ativa', is_active=True)
        Category.objects.create(user=user, name='Inativa', is_active=False)
        response = auth_client.get('/api/v1/categories/')
        names = [c['name'] for c in response.data]
        assert 'Ativa' in names
        assert 'Inativa' not in names

    def test_post_cria_categoria(self, auth_client, user):
        response = auth_client.post('/api/v1/categories/', {'name': 'Transporte', 'color': '#2196F3'})
        assert response.status_code == 201
        assert response.data['name'] == 'Transporte'
        assert Category.objects.filter(user=user, name='Transporte').exists()

    def test_post_nome_duplicado_retorna_400(self, auth_client, category):
        response = auth_client.post('/api/v1/categories/', {'name': 'Alimentação'})
        assert response.status_code == 400

    def test_tenant_isolation_get(self, auth_client, other_user):
        Category.objects.create(user=other_user, name='Outro')
        response = auth_client.get('/api/v1/categories/')
        assert all(c['name'] != 'Outro' for c in response.data)


class TestCategoryDetailAPI:
    def test_get_sem_jwt_retorna_401(self, api_client, category):
        response = api_client.get(f'/api/v1/categories/{category.pk}/')
        assert response.status_code == 401

    def test_get_com_jwt_retorna_categoria(self, auth_client, category):
        response = auth_client.get(f'/api/v1/categories/{category.pk}/')
        assert response.status_code == 200
        assert response.data['name'] == 'Alimentação'

    def test_put_atualiza_categoria(self, auth_client, category):
        response = auth_client.put(f'/api/v1/categories/{category.pk}/', {
            'name': 'Comida',
            'color': '#4CAF50',
        })
        assert response.status_code == 200
        assert response.data['name'] == 'Comida'

    def test_put_nome_duplicado_retorna_400(self, auth_client, user, category):
        Category.objects.create(user=user, name='Transporte')
        response = auth_client.put(f'/api/v1/categories/{category.pk}/', {'name': 'Transporte'})
        assert response.status_code == 400

    def test_delete_soft_deleta_categoria(self, auth_client, category):
        response = auth_client.delete(f'/api/v1/categories/{category.pk}/')
        assert response.status_code == 204
        category.refresh_from_db()
        assert category.is_active is False

    def test_nao_pode_acessar_categoria_de_outro_usuario(self, auth_client, other_user):
        other_cat = Category.objects.create(user=other_user, name='Outro')
        response = auth_client.get(f'/api/v1/categories/{other_cat.pk}/')
        assert response.status_code == 404

    def test_nao_pode_deletar_categoria_de_outro_usuario(self, auth_client, other_user):
        other_cat = Category.objects.create(user=other_user, name='Outro')
        response = auth_client.delete(f'/api/v1/categories/{other_cat.pk}/')
        assert response.status_code == 404
        other_cat.refresh_from_db()
        assert other_cat.is_active is True
