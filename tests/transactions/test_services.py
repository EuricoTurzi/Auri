"""
Testes unitários para services e selectors do app transactions.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.accounts.models import CustomUser
from apps.cards.models import Card
from apps.categories.models import Category
from apps.transactions.models import Installment, RecurringConfig, Transaction
from apps.transactions.services import (
    create_installment_transaction,
    create_recurring_transaction,
    create_transaction,
    deactivate_transaction,
    delete_recurring_transaction,
    update_status,
    update_transaction,
)
from apps.transactions.selectors import (
    get_installments,
    get_recurring_transactions,
    get_transaction_by_id,
    get_user_transactions,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
    return Category.objects.create(
        user=user,
        name='Test Category',
        is_active=True,
    )


@pytest.fixture
def other_category(other_user):
    return Category.objects.create(
        user=other_user,
        name='Other Category',
        is_active=True,
    )


@pytest.fixture
def card(user):
    return Card.objects.create(
        user=user,
        name='Nubank',
        brand='Mastercard',
        last_four_digits='1234',
        card_type='credito',
        credit_limit=Decimal('5000.00'),
    )


@pytest.fixture
def other_card(other_user):
    return Card.objects.create(
        user=other_user,
        name='Outro Cartão',
        brand='Visa',
        last_four_digits='9999',
        card_type='debito',
    )


@pytest.fixture
def transaction(user, category):
    return Transaction.objects.create(
        user=user,
        name='Salário',
        amount=Decimal('3000.00'),
        type='entrada',
        status='pendente',
        category=category,
        date=date(2024, 1, 15),
    )


# ---------------------------------------------------------------------------
# TestCreateTransaction
# ---------------------------------------------------------------------------

class TestCreateTransaction:
    def test_cria_transacao_simples_valida(self, user, category):
        """Cria transação com todos os campos obrigatórios e valida o estado inicial."""
        t = create_transaction(
            user=user,
            name='Aluguel',
            amount=Decimal('1500.00'),
            type='saida',
            category_id=category.id,
            date=date(2024, 1, 10),
            description='Pagamento mensal',
            status='pendente',
        )
        assert t.name == 'Aluguel'
        assert t.amount == Decimal('1500.00')
        assert t.type == 'saida'
        assert t.status == 'pendente'
        assert t.category == category
        assert t.user == user
        assert t.is_active is True
        assert t.card is None

    def test_rejeita_tipo_invalido(self, user, category):
        """Rejeita criação com tipo diferente de 'entrada' ou 'saida'."""
        with pytest.raises(ValidationError):
            create_transaction(
                user=user,
                name='Teste',
                amount=Decimal('100.00'),
                type='invalido',
                category_id=category.id,
                date=date(2024, 1, 1),
            )

    def test_rejeita_amount_zero(self, user, category):
        """Rejeita criação com amount igual a zero."""
        with pytest.raises(ValidationError):
            create_transaction(
                user=user,
                name='Teste',
                amount=Decimal('0.00'),
                type='entrada',
                category_id=category.id,
                date=date(2024, 1, 1),
            )

    def test_rejeita_amount_negativo(self, user, category):
        """Rejeita criação com amount negativo."""
        with pytest.raises(ValidationError):
            create_transaction(
                user=user,
                name='Teste',
                amount=Decimal('-50.00'),
                type='saida',
                category_id=category.id,
                date=date(2024, 1, 1),
            )

    def test_rejeita_categoria_de_outro_usuario(self, user, other_category):
        """Rejeita criação com categoria pertencente a outro usuário."""
        with pytest.raises(PermissionError):
            create_transaction(
                user=user,
                name='Teste',
                amount=Decimal('100.00'),
                type='saida',
                category_id=other_category.id,
                date=date(2024, 1, 1),
            )

    def test_rejeita_cartao_de_outro_usuario(self, user, category, other_card):
        """Rejeita criação com cartão pertencente a outro usuário."""
        with pytest.raises(PermissionError):
            create_transaction(
                user=user,
                name='Teste',
                amount=Decimal('100.00'),
                type='saida',
                category_id=category.id,
                date=date(2024, 1, 1),
                card_id=other_card.id,
            )

    def test_cria_sem_cartao(self, user, category):
        """Criação sem cartão é válida (card_id=None)."""
        t = create_transaction(
            user=user,
            name='Sem Cartão',
            amount=Decimal('200.00'),
            type='entrada',
            category_id=category.id,
            date=date(2024, 1, 1),
        )
        assert t.card is None


# ---------------------------------------------------------------------------
# TestUpdateTransaction
# ---------------------------------------------------------------------------

class TestUpdateTransaction:
    def test_atualiza_nome(self, user, transaction):
        """Atualiza o nome da transação com sucesso."""
        updated = update_transaction(transaction.id, user, name='Novo Nome')
        assert updated.name == 'Novo Nome'
        transaction.refresh_from_db()
        assert transaction.name == 'Novo Nome'

    def test_rejeita_transacao_de_outro_usuario(self, other_user, transaction):
        """Rejeita atualização quando o usuário não é o dono da transação."""
        with pytest.raises(PermissionError):
            update_transaction(transaction.id, other_user, name='Hack')

    def test_rejeita_categoria_de_outro_usuario_no_update(self, user, transaction, other_category):
        """Rejeita atualização de categoria com categoria de outro usuário."""
        with pytest.raises(PermissionError):
            update_transaction(transaction.id, user, category_id=other_category.id)


# ---------------------------------------------------------------------------
# TestDeactivateTransaction
# ---------------------------------------------------------------------------

class TestDeactivateTransaction:
    def test_soft_delete(self, user, transaction):
        """Desativa (soft-delete) a transação — is_active deve ser False."""
        result = deactivate_transaction(transaction.id, user)
        assert result.is_active is False
        transaction.refresh_from_db()
        assert transaction.is_active is False
        # Não deve ser hard-deleted — ainda existe no DB
        assert Transaction.objects.filter(id=transaction.id).exists()

    def test_rejeita_sem_permissao(self, other_user, transaction):
        """Rejeita desativação quando o usuário não é o dono."""
        with pytest.raises(PermissionError):
            deactivate_transaction(transaction.id, other_user)


# ---------------------------------------------------------------------------
# TestUpdateStatus
# ---------------------------------------------------------------------------

class TestUpdateStatus:
    def test_altera_para_pago(self, user, transaction):
        """Altera o status da transação para 'pago'."""
        result = update_status(transaction.id, user, 'pago')
        assert result.status == 'pago'

    def test_altera_para_pendente(self, user, transaction):
        """Altera o status de volta para 'pendente'."""
        transaction.status = 'pago'
        transaction.save()
        result = update_status(transaction.id, user, 'pendente')
        assert result.status == 'pendente'

    def test_rejeita_status_invalido(self, user, transaction):
        """Rejeita status que não seja 'pendente' ou 'pago'."""
        with pytest.raises(ValidationError):
            update_status(transaction.id, user, 'cancelado')


# ---------------------------------------------------------------------------
# TestCreateRecurringTransaction
# ---------------------------------------------------------------------------

class TestCreateRecurringTransaction:
    def test_cria_mensal_gera_12_ocorrencias(self, user, category):
        """Transação mensal gera exatamente 12 ocorrências futuras."""
        pai = create_recurring_transaction(
            user=user,
            transaction_data={
                'name': 'Aluguel',
                'amount': Decimal('1500.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 10),
            },
            frequency='mensal',
        )
        filhos = Transaction.objects.filter(recurring_parent=pai)
        assert filhos.count() == 12

    def test_cria_semanal_gera_ocorrencias_corretas(self, user, category):
        """Transação semanal tem ocorrências com 7 dias de diferença."""
        data_base = date(2024, 1, 1)
        pai = create_recurring_transaction(
            user=user,
            transaction_data={
                'name': 'Mercado',
                'amount': Decimal('300.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': data_base,
            },
            frequency='semanal',
        )
        filhos = list(
            Transaction.objects.filter(recurring_parent=pai).order_by('date')
        )
        assert len(filhos) > 0
        # Verifica que cada ocorrência está 7 dias após a anterior
        datas = [pai.date] + [f.date for f in filhos]
        for i in range(1, len(datas)):
            assert datas[i] - datas[i - 1] == timedelta(days=7)

    def test_cria_recurring_config(self, user, category):
        """RecurringConfig é criado para a transação pai."""
        pai = create_recurring_transaction(
            user=user,
            transaction_data={
                'name': 'Assinatura',
                'amount': Decimal('50.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            frequency='mensal',
        )
        assert RecurringConfig.objects.filter(transaction=pai).exists()
        config = RecurringConfig.objects.get(transaction=pai)
        assert config.frequency == 'mensal'

    def test_ocorrencias_tem_recurring_parent(self, user, category):
        """Todas as ocorrências geradas têm recurring_parent apontando para o pai."""
        pai = create_recurring_transaction(
            user=user,
            transaction_data={
                'name': 'Mensalidade',
                'amount': Decimal('200.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            frequency='mensal',
        )
        filhos = Transaction.objects.filter(recurring_parent=pai)
        for filho in filhos:
            assert filho.recurring_parent == pai
            assert filho.is_recurring is True

    def test_rejeita_frequencia_invalida(self, user, category):
        """Rejeita criação com frequência inválida."""
        with pytest.raises(ValidationError):
            create_recurring_transaction(
                user=user,
                transaction_data={
                    'name': 'Teste',
                    'amount': Decimal('100.00'),
                    'type': 'saida',
                    'category_id': category.id,
                    'date': date(2024, 1, 1),
                },
                frequency='anual',
            )


# ---------------------------------------------------------------------------
# TestDeleteRecurringTransaction
# ---------------------------------------------------------------------------

class TestDeleteRecurringTransaction:
    def test_deleta_pai_e_filhos(self, user, category):
        """Soft-delete no pai e em todos os filhos após delete_recurring_transaction."""
        pai = create_recurring_transaction(
            user=user,
            transaction_data={
                'name': 'Salário',
                'amount': Decimal('5000.00'),
                'type': 'entrada',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            frequency='mensal',
        )
        filhos_ids = list(
            Transaction.objects.filter(recurring_parent=pai).values_list('id', flat=True)
        )

        delete_recurring_transaction(pai.id, user)

        pai.refresh_from_db()
        assert pai.is_active is False

        for filho_id in filhos_ids:
            filho = Transaction.objects.get(id=filho_id)
            assert filho.is_active is False

    def test_rejeita_sem_permissao(self, user, category, other_user):
        """Rejeita exclusão quando o usuário não é o dono."""
        pai = create_recurring_transaction(
            user=user,
            transaction_data={
                'name': 'Teste',
                'amount': Decimal('100.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            frequency='mensal',
        )
        with pytest.raises(PermissionError):
            delete_recurring_transaction(pai.id, other_user)

    def test_rejeita_sem_recurring_config(self, user, transaction):
        """Rejeita exclusão de transação que não possui RecurringConfig."""
        with pytest.raises(ValidationError):
            delete_recurring_transaction(transaction.id, user)


# ---------------------------------------------------------------------------
# TestCreateInstallmentTransaction
# ---------------------------------------------------------------------------

class TestCreateInstallmentTransaction:
    def test_cria_5_parcelas_de_60(self, user, category):
        """R$300 em 5x gera 5 parcelas de R$60 cada."""
        pai = create_installment_transaction(
            user=user,
            transaction_data={
                'name': 'TV',
                'amount': Decimal('300.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 10),
            },
            total_installments=5,
        )
        parcelas = list(Installment.objects.filter(parent_transaction=pai).order_by('installment_number'))
        assert len(parcelas) == 5
        for p in parcelas:
            assert p.amount == Decimal('60.00')

    def test_distribui_centavos(self, user, category):
        """R$100 em 3x: primeira parcela recebe o centavo extra [33.34, 33.33, 33.33]."""
        pai = create_installment_transaction(
            user=user,
            transaction_data={
                'name': 'Notebook',
                'amount': Decimal('100.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            total_installments=3,
        )
        parcelas = list(Installment.objects.filter(parent_transaction=pai).order_by('installment_number'))
        assert len(parcelas) == 3
        assert parcelas[0].amount == Decimal('33.34')
        assert parcelas[1].amount == Decimal('33.33')
        assert parcelas[2].amount == Decimal('33.33')

    def test_numeracao_sequencial(self, user, category):
        """Parcelas são numeradas de 1 a N sequencialmente."""
        total = 4
        pai = create_installment_transaction(
            user=user,
            transaction_data={
                'name': 'Geladeira',
                'amount': Decimal('800.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            total_installments=total,
        )
        numeros = list(
            Installment.objects.filter(parent_transaction=pai)
            .order_by('installment_number')
            .values_list('installment_number', flat=True)
        )
        assert numeros == list(range(1, total + 1))

    def test_rejeita_tipo_entrada(self, user, category):
        """Parcelamento é rejeitado para transações do tipo 'entrada'."""
        with pytest.raises(ValidationError):
            create_installment_transaction(
                user=user,
                transaction_data={
                    'name': 'Salário',
                    'amount': Decimal('3000.00'),
                    'type': 'entrada',
                    'category_id': category.id,
                    'date': date(2024, 1, 1),
                },
                total_installments=3,
            )

    def test_rejeita_menos_de_2_parcelas(self, user, category):
        """Número de parcelas menor que 2 deve levantar ValidationError."""
        with pytest.raises(ValidationError):
            create_installment_transaction(
                user=user,
                transaction_data={
                    'name': 'Compra',
                    'amount': Decimal('200.00'),
                    'type': 'saida',
                    'category_id': category.id,
                    'date': date(2024, 1, 1),
                },
                total_installments=1,
            )

    def test_due_dates_mensais(self, user, category):
        """Due dates das parcelas são mensais a partir da data da transação."""
        data_base = date(2024, 1, 15)
        pai = create_installment_transaction(
            user=user,
            transaction_data={
                'name': 'Compra',
                'amount': Decimal('300.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': data_base,
            },
            total_installments=3,
        )
        parcelas = list(Installment.objects.filter(parent_transaction=pai).order_by('installment_number'))
        assert parcelas[0].due_date == date(2024, 2, 15)
        assert parcelas[1].due_date == date(2024, 3, 15)
        assert parcelas[2].due_date == date(2024, 4, 15)


# ---------------------------------------------------------------------------
# TestSelectors
# ---------------------------------------------------------------------------

class TestSelectors:
    def test_get_user_transactions_retorna_apenas_do_usuario(self, user, other_user, category):
        """get_user_transactions retorna apenas transações do usuário autenticado."""
        other_cat = Category.objects.create(user=other_user, name='Other')
        Transaction.objects.create(
            user=other_user,
            name='Transação outro',
            amount=Decimal('100.00'),
            type='entrada',
            category=other_cat,
            date=date(2024, 1, 1),
        )
        t = Transaction.objects.create(
            user=user,
            name='Minha Transação',
            amount=Decimal('200.00'),
            type='saida',
            category=category,
            date=date(2024, 1, 1),
        )
        qs = get_user_transactions(user)
        assert t in qs
        assert all(tx.user == user for tx in qs)

    def test_get_user_transactions_filtro_por_tipo(self, user, category):
        """Filtro por tipo retorna apenas transações do tipo especificado."""
        Transaction.objects.create(
            user=user, name='E', amount=Decimal('100.00'),
            type='entrada', category=category, date=date(2024, 1, 1),
        )
        Transaction.objects.create(
            user=user, name='S', amount=Decimal('50.00'),
            type='saida', category=category, date=date(2024, 1, 2),
        )
        qs = get_user_transactions(user, filters={'type': 'entrada'})
        assert all(t.type == 'entrada' for t in qs)

    def test_get_user_transactions_filtro_por_status(self, user, category):
        """Filtro por status retorna apenas transações com o status especificado."""
        Transaction.objects.create(
            user=user, name='Pendente', amount=Decimal('100.00'),
            type='saida', status='pendente', category=category, date=date(2024, 1, 1),
        )
        Transaction.objects.create(
            user=user, name='Pago', amount=Decimal('200.00'),
            type='saida', status='pago', category=category, date=date(2024, 1, 2),
        )
        qs = get_user_transactions(user, filters={'status': 'pago'})
        assert all(t.status == 'pago' for t in qs)

    def test_get_transaction_by_id_retorna_correta(self, user, transaction):
        """get_transaction_by_id retorna a transação correta para o dono."""
        resultado = get_transaction_by_id(transaction.id, user)
        assert resultado == transaction

    def test_get_transaction_by_id_rejeita_outro_usuario(self, other_user, transaction):
        """get_transaction_by_id levanta PermissionError para usuário errado."""
        with pytest.raises(PermissionError):
            get_transaction_by_id(transaction.id, other_user)

    def test_get_installments_retorna_parcelas(self, user, category):
        """get_installments retorna parcelas da transação parcelada."""
        pai = create_installment_transaction(
            user=user,
            transaction_data={
                'name': 'Compra',
                'amount': Decimal('200.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            total_installments=2,
        )
        parcelas = get_installments(pai.id, user)
        assert parcelas.count() == 2

    def test_get_installments_rejeita_outro_usuario(self, other_user, user, category):
        """get_installments levanta PermissionError para usuário sem acesso."""
        pai = create_installment_transaction(
            user=user,
            transaction_data={
                'name': 'Compra',
                'amount': Decimal('200.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            total_installments=2,
        )
        with pytest.raises(PermissionError):
            get_installments(pai.id, other_user)

    def test_get_recurring_transactions_retorna_apenas_pais(self, user, category):
        """get_recurring_transactions retorna apenas as transações pai (sem recurring_parent)."""
        pai = create_recurring_transaction(
            user=user,
            transaction_data={
                'name': 'Recorrente',
                'amount': Decimal('100.00'),
                'type': 'saida',
                'category_id': category.id,
                'date': date(2024, 1, 1),
            },
            frequency='mensal',
        )
        qs = get_recurring_transactions(user)
        assert pai in qs
        # Todos os resultados devem ser pais (sem recurring_parent)
        assert all(t.recurring_parent is None for t in qs)
