from rest_framework import serializers

from apps.accounts.models import CustomUser


class RegisterSerializer(serializers.Serializer):
    """Serializer para registro de usuário. Não retorna senha."""
    email = serializers.EmailField()
    nickname = serializers.CharField(max_length=50)

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este e-mail já está em uso.')
        return value

    def validate_nickname(self, value):
        if CustomUser.objects.filter(nickname=value).exists():
            raise serializers.ValidationError('Este nickname já está em uso.')
        return value


class LoginSerializer(serializers.Serializer):
    """Serializer para login com e-mail e senha."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para troca de senha no primeiro acesso."""
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError('As senhas não coincidem.')
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer read-only para dados do usuário."""

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'nickname', 'is_first_access', 'phone_number', 'created_at']
        read_only_fields = fields
