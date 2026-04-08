from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.accounts.services import change_first_access_password, register_user


class RegisterAPIView(APIView):
    """POST /api/v1/accounts/register/ — registro de novo usuário."""
    permission_classes = [AllowAny]

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

    def get(self, request):
        return Response(UserSerializer(request.user).data)
