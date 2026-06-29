"""Vistas transversales: login JWT con claims, datos del usuario actual y
administración de usuarios, grupos (roles) y permisos (solo superadministrador)."""

from django.contrib.auth.models import Group, Permission, User
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.permissions import IsSuperUser
from apps.common.serializers import (
    CustomTokenObtainPairSerializer,
    GroupSerializer,
    MeSerializer,
    PermissionSerializer,
    SetPasswordSerializer,
    UserCreateSerializer,
    UserReadSerializer,
    UserUpdateSerializer,
)
from apps.common.services import registrar_auditoria


class CustomTokenObtainPairView(TokenObtainPairView):
    """Obtiene el par de tokens JWT incluyendo roles y nombre en los claims."""

    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    """Devuelve la identidad, roles y perfiles institucionales del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """CRUD de usuarios (solo superadministrador). `DELETE` desactiva, no borra."""

    queryset = User.objects.prefetch_related("groups").all()
    permission_classes = [IsSuperUser]
    filterset_fields = ["is_active", "is_superuser", "is_staff", "groups"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["id", "username", "date_joined", "last_login"]
    ordering = ["id"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        if self.action == "set_password":
            return SetPasswordSerializer
        return UserReadSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "CREAR", objeto)

    @transaction.atomic
    def perform_update(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "ACTUALIZAR", objeto)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Desactiva el usuario (`is_active=False`) conservando su trazabilidad."""
        usuario = self.get_object()
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        registrar_auditoria(
            request.user,
            "DESACTIVAR",
            usuario,
            nombre_campo="is_active",
            valor_anterior=True,
            valor_nuevo=False,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="set-password")
    @transaction.atomic
    def set_password(self, request, pk=None):
        """Cambia la contraseña del usuario sin exponer su valor en la auditoría."""
        usuario = self.get_object()
        ser = SetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        usuario.set_password(ser.validated_data["password"])
        usuario.save(update_fields=["password"])
        registrar_auditoria(request.user, "ACTUALIZAR", usuario, nombre_campo="password")
        return Response({"detalle": "Contraseña actualizada."})


class GroupViewSet(viewsets.ModelViewSet):
    """CRUD de grupos (roles) con asignación de permisos (solo superadministrador)."""

    queryset = Group.objects.prefetch_related("permissions").all()
    serializer_class = GroupSerializer
    permission_classes = [IsSuperUser]
    search_fields = ["name"]
    ordering_fields = ["id", "name"]
    ordering = ["name"]

    @transaction.atomic
    def perform_create(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "CREAR", objeto)

    @transaction.atomic
    def perform_update(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "ACTUALIZAR", objeto)

    @transaction.atomic
    def perform_destroy(self, instance):
        registrar_auditoria(self.request.user, "ELIMINAR", instance)
        instance.delete()


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de permisos (solo lectura, solo superadministrador)."""

    queryset = Permission.objects.select_related("content_type").all()
    serializer_class = PermissionSerializer
    permission_classes = [IsSuperUser]
    filterset_fields = ["content_type", "content_type__app_label"]
    search_fields = ["name", "codename"]
    ordering_fields = ["id", "codename"]
    ordering = ["content_type", "codename"]
