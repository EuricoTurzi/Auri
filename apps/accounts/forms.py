import re

from django import forms


class LoginForm(forms.Form):
    """Formulário de login com e-mail e senha."""
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'placeholder': 'seu@email.com', 'autofocus': True}),
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'placeholder': 'Sua senha'}),
    )


class RegisterForm(forms.Form):
    """Formulário de registro com nickname e e-mail."""
    nickname = forms.CharField(
        label='Nickname',
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'seu_nickname', 'autofocus': True}),
    )
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'placeholder': 'seu@email.com'}),
    )

    def clean_nickname(self):
        nickname = self.cleaned_data['nickname']
        if not re.match(r'^[a-zA-Z0-9_-]+$', nickname):
            raise forms.ValidationError(
                'Nickname deve conter apenas letras, números, underscore e hífen.'
            )
        return nickname


class ChangePasswordForm(forms.Form):
    """Formulário de troca de senha no primeiro acesso."""
    new_password = forms.CharField(
        label='Nova senha',
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 8 caracteres'}),
    )
    confirm_password = forms.CharField(
        label='Confirmar senha',
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': 'Repita a senha'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError('As senhas não coincidem.')
        return cleaned_data
