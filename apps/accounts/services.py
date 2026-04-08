from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string

from apps.accounts.models import CustomUser


def generate_temporary_password():
    """Gera senha temporária aleatória de 12 caracteres."""
    return get_random_string(length=12)


def send_first_access_email(user, temporary_password):
    """Envia e-mail com senha temporária e instruções de primeiro acesso."""
    subject = 'Auri — Seu acesso foi criado'
    message = (
        f'Olá {user.nickname},\n\n'
        f'Sua conta na Auri foi criada com sucesso!\n\n'
        f'Sua senha temporária é: {temporary_password}\n\n'
        f'Ao fazer login pela primeira vez, você será obrigado(a) a trocar a senha.\n\n'
        f'Acesse: {settings.LOGIN_URL}\n\n'
        f'— Equipe Auri'
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def register_user(email, nickname):
    """
    Registra novo usuário com senha temporária.
    Envia e-mail com a senha gerada. Retorna o usuário criado (sem a senha).
    """
    temporary_password = generate_temporary_password()
    user = CustomUser.objects.create_user(
        email=email,
        nickname=nickname,
        password=temporary_password,
    )
    send_first_access_email(user, temporary_password)
    return user


def change_first_access_password(user, new_password):
    """
    Troca a senha no primeiro acesso.
    Valida que o usuário está em primeiro acesso e que a senha tem mínimo 8 caracteres.
    """
    if not user.is_first_access:
        raise ValueError('Usuário já realizou a troca de senha.')

    if len(new_password) < 8:
        raise ValueError('A senha deve ter no mínimo 8 caracteres.')

    user.set_password(new_password)
    user.is_first_access = False
    user.save(update_fields=['password', 'is_first_access', 'updated_at'])
    return user
