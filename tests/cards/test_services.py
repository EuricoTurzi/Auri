import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import CustomUser
from apps.cards.models import Card
from apps.cards.services import create_card, deactivate_card, update_card
from apps.cards.selectors import get_available_limit, get_card_by_id, get_user_cards


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
def card(user):
    return Card.objects.create(
        user=user,
        name='Nubank',
        brand='Mastercard',
        last_four_digits='1234',
        card_type='credito',
        credit_limit=5000,
        billing_close_day=3,
        billing_due_day=10,
    )


class TestCreateCard:
    def test_cria_cartao_credito_valido(self, user):
        """Cria cartão de crédito com todos os campos e valida estado inicial."""
        card = create_card(user, 'Nubank', 'Mastercard', '1234', 'credito', credit_limit=5000)
        assert card.name == 'Nubank'
        assert card.is_active is True

    def test_cria_cartao_debito_valido(self, user):
        """Cria cartão de débito sem campos exclusivos de crédito."""
        card = create_card(user, 'Itaú', 'Visa', '5678', 'debito')
        assert card.card_type == 'debito'

    def test_rejeita_digitos_invalidos_letras(self, user):
        """Rejeita criação de cartão com letras nos últimos 4 dígitos."""
        with pytest.raises(ValidationError):
            create_card(user, 'Test', 'Visa', '12AB', 'debito')

    def test_rejeita_menos_de_4_digitos(self, user):
        """Rejeita criação de cartão com menos de 4 dígitos."""
        with pytest.raises(ValidationError):
            create_card(user, 'Test', 'Visa', '123', 'debito')

    def test_rejeita_mais_de_4_digitos(self, user):
        """Rejeita criação de cartão com mais de 4 dígitos."""
        with pytest.raises(ValidationError):
            create_card(user, 'Test', 'Visa', '12345', 'debito')


class TestUpdateCard:
    def test_atualiza_nome(self, user, card):
        """Atualiza o nome do cartão com sucesso."""
        updated = update_card(card.id, user, name='Novo Nome')
        assert updated.name == 'Novo Nome'

    def test_rejeita_digitos_invalidos_no_update(self, user, card):
        """Rejeita atualização com últimos 4 dígitos inválidos (letras)."""
        with pytest.raises(ValidationError):
            update_card(card.id, user, last_four_digits='ABCD')

    def test_rejeita_ownership_errado(self, other_user, card):
        """Rejeita atualização quando o usuário não é dono do cartão."""
        with pytest.raises(PermissionError):
            update_card(card.id, other_user, name='Hack')


class TestDeactivateCard:
    def test_soft_delete(self, user, card):
        """Desativa o cartão (soft-delete), is_active deve ser False."""
        result = deactivate_card(card.id, user)
        assert result.is_active is False
        card.refresh_from_db()
        assert card.is_active is False

    def test_rejeita_ownership_errado(self, other_user, card):
        """Rejeita desativação quando o usuário não é dono do cartão."""
        with pytest.raises(PermissionError):
            deactivate_card(card.id, other_user)

    def test_cartao_desativado_nao_aparece_em_cards_ativos(self, user, card):
        """Cartão desativado não deve aparecer na listagem de cartões ativos."""
        deactivate_card(card.id, user)
        qs = get_user_cards(user, active_only=True)
        assert card not in qs


class TestSelectors:
    def test_get_user_cards_retorna_apenas_ativos(self, user, card, other_user):
        """get_user_cards retorna apenas cartões ativos do usuário."""
        card_inativo = Card.objects.create(
            user=user,
            name='Inativo',
            brand='Visa',
            last_four_digits='9999',
            card_type='debito',
            is_active=False,
        )
        qs = get_user_cards(user, active_only=True)
        assert card in qs
        assert card_inativo not in qs

    def test_get_user_cards_nao_retorna_de_outro_usuario(self, user, card, other_user):
        """get_user_cards não retorna cartões de outro usuário."""
        outro_cartao = Card.objects.create(
            user=other_user,
            name='Outro',
            brand='Elo',
            last_four_digits='4321',
            card_type='debito',
        )
        qs = get_user_cards(user, active_only=True)
        assert outro_cartao not in qs

    def test_get_card_by_id_valida_ownership(self, card, other_user):
        """get_card_by_id levanta PermissionError para usuário errado."""
        with pytest.raises(PermissionError):
            get_card_by_id(card.id, other_user)

    def test_get_card_by_id_retorna_cartao_do_dono(self, card, user):
        """get_card_by_id retorna o cartão quando o usuário é o dono."""
        resultado = get_card_by_id(card.id, user)
        assert resultado == card

    def test_get_available_limit_credito_sem_transacoes(self, user):
        """get_available_limit retorna credit_limit completo quando não há transações."""
        from decimal import Decimal
        cartao = Card.objects.create(
            user=user,
            name='Crédito Teste',
            brand='Mastercard',
            last_four_digits='1111',
            card_type='credito',
            credit_limit=Decimal('5000.00'),
        )
        resultado = get_available_limit(cartao)
        assert resultado == Decimal('5000.00')

    def test_get_available_limit_retorna_none_para_debito(self, user):
        """get_available_limit retorna None para cartão de débito."""
        cartao = Card.objects.create(
            user=user,
            name='Débito Teste',
            brand='Visa',
            last_four_digits='2222',
            card_type='debito',
        )
        resultado = get_available_limit(cartao)
        assert resultado is None

    def test_get_available_limit_retorna_none_sem_credit_limit(self, user):
        """get_available_limit retorna None para cartão de crédito sem credit_limit definido."""
        cartao = Card.objects.create(
            user=user,
            name='Crédito Sem Limite',
            brand='Elo',
            last_four_digits='3333',
            card_type='credito',
            credit_limit=None,
        )
        resultado = get_available_limit(cartao)
        assert resultado is None
