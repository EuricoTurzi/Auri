from django.contrib.auth import authenticate
from rest_framework import serializers as drf_serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from apps.accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.accounts.services import change_first_access_password, register_user


class _LoginResponseSerializer(drf_serializers.Serializer):
    access = drf_serializers.CharField()
    refresh = drf_serializers.CharField()
    user = UserSerializer()


class RegisterAPIView(APIView):
    """POST /api/v1/accounts/register/ — registro de novo usuário."""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Accounts'],
        summary='Registrar novo usuário',
        request=RegisterSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_user(
            email=serializer.validated_data['email'],
            nickname=serializer.validated_data['nickname'],
        )
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    """POST /api/v1/accounts/login/ — retorna JWT tokens."""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Accounts'],
        summary='Login — obter tokens JWT',
        request=LoginSerializer,
        responses={200: _LoginResponseSerializer, 401: None},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )

        if user is None:
            return Response(
                {'detail': 'E-mail ou senha inválidos.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {'detail': 'Conta desativada.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class ChangePasswordAPIView(APIView):
    """POST /api/v1/accounts/change-password/ — troca senha primeiro acesso."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Accounts'],
        summary='Trocar senha (primeiro acesso)',
        request=ChangePasswordSerializer,
        responses={200: UserSerializer},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = change_first_access_password(
                user=request.user,
                new_password=serializer.validated_data['new_password'],
            )
            return Response(UserSerializer(user).data)
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeAPIView(APIView):
    """GET /api/v1/accounts/me/ — dados do usuário autenticado."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Accounts'],
        summary='Dados do usuário autenticado',
        responses={200: UserSerializer},
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)
