from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.categories.models import Category
from apps.categories.selectors import get_category_by_id, get_user_categories
from apps.categories.serializers import CategoryCreateUpdateSerializer, CategorySerializer
from apps.categories.services import create_category, deactivate_category, update_category


class CategoryListCreateAPIView(APIView):
    """GET/POST /api/v1/categories/ — lista e criação de categorias."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = get_user_categories(request.user, active_only=True)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CategoryCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            category = create_category(
                user=request.user,
                name=data['name'],
                description=data.get('description') or None,
                color=data.get('color') or None,
                icon=data.get('icon') or None,
            )
        except ValidationError as e:
            return Response({'detail': e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)


class CategoryDetailAPIView(APIView):
    """GET/PUT/DELETE /api/v1/categories/<pk>/ — detalhe, atualização e soft-delete."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            category = get_category_by_id(pk, request.user)
        except Category.DoesNotExist:
            return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CategorySerializer(category).data)

    def put(self, request, pk):
        serializer = CategoryCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            category = update_category(
                pk,
                request.user,
                name=data['name'],
                description=data.get('description') or None,
                color=data.get('color') or None,
                icon=data.get('icon') or None,
            )
        except PermissionError:
            return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({'detail': e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CategorySerializer(category).data)

    def delete(self, request, pk):
        try:
            deactivate_category(pk, request.user)
        except PermissionError:
            return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
