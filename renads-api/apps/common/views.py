"""Vistas transversales: login JWT con claims y datos del usuario actual."""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.serializers import CustomTokenObtainPairSerializer, MeSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """Obtiene el par de tokens JWT incluyendo roles y nombre en los claims."""

    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    """Devuelve la identidad, roles y perfiles institucionales del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user).data)
