import pytest
from unittest.mock import patch

from apps.accounts.models import CustomUser
from apps.accounts.services import (
    change_first_access_password,
    generate_temporary_password,
    register_user,
)


class TestGenerateTemporaryPassword:
    def test_gera_senha_com_12_caracteres(self):
        senha = generate_temporary_password()
        assert len(senha) == 12

    def test_gera_senhas_diferentes(self):
        senha1 = generate_temporary_password()
        senha2 = generate_temporary_password()
        assert senha1 != senha2


class TestRegisterUser:
    @patch('apps.accounts.services.send_mail')
    def test_registro_com_dados_validos(self, mock_send_mail):
        user = register_user(email='teste@email.com', nickname='testuser')

        assert user.email == 'teste@email.com'
        assert user.nickname == 'testuser'
        assert user.is_first_access is True
        assert user.is_active is True
        assert user.has_usable_password()
        mock_send_mail.assert_called_once()

    @patch('apps.accounts.services.send_mail')
    def test_registro_email_duplicado(self, mock_send_mail):
        register_user(email='dup@email.com', nickname='user1')
        with pytest.raises(Exception):
            register_user(email='dup@email.com', nickname='user2')

    @patch('apps.accounts.services.send_mail')
    def test_registro_nickname_duplicado(self, mock_send_mail):
        register_user(email='a@email.com', nickname='dupnick')
        with pytest.raises(Exception):
            register_user(email='b@email.com', nickname='dupnick')

    @patch('apps.accounts.services.send_mail')
    def test_email_enviado_com_senha_temporaria(self, mock_send_mail):
        register_user(email='mail@test.com', nickname='mailuser')

        call_args = mock_send_mail.call_args
        message = call_args.kwargs.get('message') or call_args[1].get('message') or call_args[0][1]
        assert 'senha temporária' in message.lower() or 'temporária' in message

    @patch('apps.accounts.services.send_mail')
    def test_senha_nao_retornada_no_user(self, mock_send_mail):
        user = register_user(email='nosecret@email.com', nickname='nosecret')
        # Verifica que não há atributo de senha plain text
        assert not hasattr(user, 'temporary_password')
        assert not hasattr(user, 'plain_password')


class TestChangeFirstAccessPassword:
    @patch('apps.accounts.services.send_mail')
    def test_troca_senha_primeiro_acesso(self, mock_send_mail):
        user = register_user(email='change@email.com', nickname='changeuser')
        assert user.is_first_access is True

        updated_user = change_first_access_password(user, 'novasenha123')

        assert updated_user.is_first_access is False
        assert updated_user.check_password('novasenha123')

    @patch('apps.accounts.services.send_mail')
    def test_senha_antiga_nao_funciona_apos_troca(self, mock_send_mail):
        user = register_user(email='old@email.com', nickname='olduser')
        # Guardar a senha temporária para testar
        old_password = 'qualquersenha'
        user.set_password(old_password)
        user.save()

        change_first_access_password(user, 'novasenha456')

        user.refresh_from_db()
        assert not user.check_password(old_password)
        assert user.check_password('novasenha456')

    @patch('apps.accounts.services.send_mail')
    def test_erro_se_nao_primeiro_acesso(self, mock_send_mail):
        user = register_user(email='done@email.com', nickname='doneuser')
        change_first_access_password(user, 'novasenha789')

        with pytest.raises(ValueError, match='já realizou'):
            change_first_access_password(user, 'outrasenha')

    @patch('apps.accounts.services.send_mail')
    def test_erro_senha_curta(self, mock_send_mail):
        user = register_user(email='short@email.com', nickname='shortuser')

        with pytest.raises(ValueError, match='mínimo 8'):
            change_first_access_password(user, '1234567')
