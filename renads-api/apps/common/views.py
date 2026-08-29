"""Vistas transversales: login JWT con claims, datos del usuario actual y
administración de usuarios, grupos (roles) y permisos (solo superadministrador)."""

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.models import UserSecurity
from apps.common.permissions import IsSuperUser
from apps.common.serializers import (
    ASSIGNABLE_PROFILE_MODELS,
    AssignableEntityTypeSerializer,
    ChangeOwnPasswordSerializer,
    ContentTypeSerializer,
    CustomTokenObtainPairSerializer,
    GroupSerializer,
    MeSerializer,
    PermissionSerializer,
    SetPasswordSerializer,
    UserCreateSerializer,
    UserEntityProfileWriteReadSerializer,
    UserEntityProfileWriteSerializer,
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


class MeChangePasswordView(APIView):
    """Cambio de la propia contraseña (RN-22): limpia `debe_cambiar_password`."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangeOwnPasswordSerializer, responses=MeSerializer)
    def post(self, request):
        ser = ChangeOwnPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        usuario = request.user
        if not usuario.check_password(ser.validated_data["password_actual"]):
            return Response(
                {"password_actual": ["La contraseña actual no es correcta."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            usuario.set_password(ser.validated_data["password_nueva"])
            usuario.save(update_fields=["password"])
            seguridad, _ = UserSecurity.objects.get_or_create(usuario=usuario)
            if seguridad.debe_cambiar_password:
                seguridad.debe_cambiar_password = False
                seguridad.save(update_fields=["debe_cambiar_password", "actualizado_en"])
            registrar_auditoria(usuario, "ACTUALIZAR", usuario, nombre_campo="password")
        return Response(MeSerializer(usuario).data)


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
        if self.action == "profiles":
            return UserEntityProfileWriteSerializer
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

    @extend_schema(
        request=UserEntityProfileWriteSerializer,
        responses=UserEntityProfileWriteReadSerializer(many=True),
    )
    @action(detail=True, methods=["get", "post", "delete"], url_path="profiles")
    def profiles(self, request, pk=None):
        """Gestiona el alcance por objeto (`UserEntityProfile`) del usuario objetivo.

        - GET: lista los perfiles del usuario; por defecto solo los activos,
          salvo ``?incluir_inactivos=true``.
        - POST: otorga/reactiva de forma idempotente el acceso a una o varias
          entidades bajo un rol (una fila por cada id de ``ids``).
        - DELETE: da de baja lógica (``activo=False``) un perfil concreto indicado
          por ``profile_id`` (query param o body).
        """
        from apps.convenios.models import UserEntityProfile

        usuario = self.get_object()

        if request.method == "GET":
            perfiles = UserEntityProfile.objects.filter(
                usuario=usuario
            ).select_related("tipo_contenido", "grupo")
            incluir_inactivos = (
                request.query_params.get("incluir_inactivos", "").lower() == "true"
            )
            if not incluir_inactivos:
                perfiles = perfiles.filter(activo=True)
            datos = UserEntityProfileWriteReadSerializer(perfiles, many=True).data
            return Response(datos)

        if request.method == "POST":
            ser = UserEntityProfileWriteSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            tipo_contenido = ser.validated_data["tipo_contenido"]
            grupo = ser.validated_data["rol"]
            ids = ser.validated_data["ids"]
            perfiles = []
            with transaction.atomic():
                for id_objeto in ids:
                    perfil, creado = UserEntityProfile.objects.get_or_create(
                        usuario=usuario,
                        tipo_contenido=tipo_contenido,
                        id_objeto=id_objeto,
                        grupo=grupo,
                        defaults={"activo": True},
                    )
                    if creado:
                        registrar_auditoria(request.user, "CREAR", perfil)
                    elif not perfil.activo:
                        perfil.activo = True
                        perfil.save(update_fields=["activo"])
                        registrar_auditoria(
                            request.user,
                            "ACTIVAR",
                            perfil,
                            nombre_campo="activo",
                            valor_anterior=False,
                            valor_nuevo=True,
                        )
                    perfiles.append(perfil)
            datos = UserEntityProfileWriteReadSerializer(perfiles, many=True).data
            return Response(datos, status=status.HTTP_201_CREATED)

        # DELETE: baja lógica de un perfil concreto.
        profile_id = request.query_params.get("profile_id") or request.data.get(
            "profile_id"
        )
        if profile_id is None:
            return Response(
                {"profile_id": ["Debe indicar el identificador del perfil a revocar."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            perfil = UserEntityProfile.objects.get(pk=profile_id, usuario=usuario)
        except (UserEntityProfile.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detalle": "El perfil indicado no pertenece al usuario."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if perfil.activo:
            with transaction.atomic():
                perfil.activo = False
                perfil.save(update_fields=["activo"])
                registrar_auditoria(
                    request.user,
                    "DESACTIVAR",
                    perfil,
                    nombre_campo="activo",
                    valor_anterior=True,
                    valor_nuevo=False,
                )
        return Response(status=status.HTTP_204_NO_CONTENT)


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


class ContentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de `ContentType` de Django (solo lectura) para selectores del frontend.

    Paginado y con `?search=` (por `app_label`/`model`), compatible con el combobox
    genérico. Alimenta el selector `content_types[]` del CRUD de `calendar-activities`
    e interpreta `modulos_habilitados`/`modulos_bloqueados` de `/auth/me/`. El
    `verbose_name` es el nombre legible del modelo (fallback a `ct.name` si es huérfano).
    """

    queryset = ContentType.objects.all().order_by("app_label", "model")
    serializer_class = ContentTypeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["app_label"]
    search_fields = ["app_label", "model"]
    ordering_fields = ["app_label", "model", "id"]
    ordering = ["app_label", "model"]


class AssignableEntityTypeView(APIView):
    """Lista los tipos de entidad elegibles para asignar un perfil de usuario (T11).

    Alimenta el selector «Tipo de entidad» del alta de perfiles institucionales
    (`GET/POST /api/v1/users/{id}/profiles/`). Cada item expone el `tipo_entidad`
    (nombre de modelo en minúscula) que el frontend reenvía tal cual en el POST de
    perfiles, junto con una etiqueta legible en español (`label`). Comparte la
    allowlist `ASSIGNABLE_PROFILE_MODELS` con la validación de escritura (T10), de
    modo que el catálogo ofrecido y el conjunto aceptado no pueden divergir.
    """

    permission_classes = [IsSuperUser]

    @extend_schema(
        responses=AssignableEntityTypeSerializer(many=True),
        summary="Tipos de entidad asignables a perfiles",
        description=(
            "Lista los tipos de entidad institucional sobre los que se puede otorgar "
            "un perfil (scope por objeto) a un usuario. El campo `tipo_entidad` es el "
            "valor que espera el POST de perfiles; `label` es la etiqueta legible en "
            "español (verbose_name del modelo). Restringido a superadministrador."
        ),
        tags=["common"],
    )
    def get(self, request):
        cts = ContentType.objects.get_for_models(*ASSIGNABLE_PROFILE_MODELS)
        data = [
            {
                "id": ct.id,
                "tipo_entidad": ct.model,
                "label": modelo._meta.verbose_name,
                "app_label": ct.app_label,
            }
            for modelo, ct in cts.items()
        ]
        data.sort(key=lambda item: item["label"])
        return Response(AssignableEntityTypeSerializer(data, many=True).data)
