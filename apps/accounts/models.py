import re

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models

from core.models import BaseModel


def validate_nickname(value):
    """Valida que nickname contém apenas alfanuméricos, underscore e hífen."""
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValidationError(
            'Nickname deve conter apenas letras, números, underscore e hífen.'
        )


class CustomUserManager(BaseUserManager):
    """Manager customizado para CustomUser com e-mail como identificador."""

    def create_user(self, email, nickname, password=None, **extra_fields):
        if not email:
            raise ValueError('O campo e-mail é obrigatório.')
        if not nickname:
            raise ValueError('O campo nickname é obrigatório.')

        email = self.normalize_email(email)
        user = self.model(email=email, nickname=nickname, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nickname, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_first_access', False)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser precisa ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser precisa ter is_superuser=True.')

        return self.create_user(email, nickname, password, **extra_fields)


class CustomUser(BaseModel, AbstractBaseUser, PermissionsMixin):
    """Modelo de usuário da plataforma Auri."""
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=50, unique=True, validators=[validate_nickname])
    is_first_access = models.BooleanField(default=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nickname']

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return self.email
