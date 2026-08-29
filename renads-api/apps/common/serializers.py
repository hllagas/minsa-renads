"""Serializers transversales: JWT con claims de roles, datos del usuario actual
y administración de usuarios, grupos (roles) y permisos (solo superadministrador)."""

from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.password_validation import validate_password
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.common.models import debe_cambiar_password as _debe_cambiar_password
from apps.common.selectors import grupos_del_usuario, perfiles_del_usuario


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Agrega los roles, el nombre y la condición de superusuario al token JWT.

    El claim y el campo `es_superusuario` permiten al frontend habilitar u
    ocultar la interfaz de administración de usuarios, roles y permisos.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["nombre"] = user.get_full_name() or user.get_username()
        token["grupos"] = list(user.groups.values_list("name", flat=True))
        token["es_superusuario"] = user.is_superuser
        token["debe_cambiar_password"] = _debe_cambiar_password(user)
        return token

    def validate(self, attrs):
        """Enriquece el body de la respuesta de login con datos de identidad."""
        data = super().validate(attrs)
        data["es_superusuario"] = self.user.is_superuser
        data["nombre"] = self.user.get_full_name() or self.user.get_username()
        data["grupos"] = list(self.user.groups.values_list("name", flat=True))
        data["debe_cambiar_password"] = _debe_cambiar_password(self.user)
        # Alias OAuth2-compatible para que Swagger UI (password flow) auto-configure
        # el Bearer token tras el login desde el diálogo Authorize.
        data["access_token"] = data["access"]
        data["token_type"] = "bearer"
        return data


class UserEntityProfileSerializer(serializers.Serializer):
    """Perfil institucional del usuario (entidad polimórfica + rol)."""

    tipo_entidad = serializers.CharField(source="tipo_contenido.model")
    id_objeto = serializers.IntegerField()
    entidad = serializers.SerializerMethodField()
    rol = serializers.CharField(source="grupo.name")

    def get_entidad(self, obj) -> str:
        return str(obj.entidad) if obj.entidad else ""


class MeSerializer(serializers.Serializer):
    """Datos del usuario autenticado: identidad, roles y perfiles institucionales."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    nombre = serializers.SerializerMethodField()
    es_superusuario = serializers.BooleanField(source="is_superuser")
    debe_cambiar_password = serializers.SerializerMethodField()
    grupos = serializers.SerializerMethodField()
    perfiles = serializers.SerializerMethodField()
    modulos_habilitados = serializers.SerializerMethodField()
    modulos_bloqueados = serializers.SerializerMethodField()

    def get_nombre(self, obj) -> str:
        return obj.get_full_name() or obj.get_username()

    def get_debe_cambiar_password(self, obj) -> bool:
        return _debe_cambiar_password(obj)

    def get_grupos(self, obj) -> list[str]:
        return grupos_del_usuario(obj)

    def get_perfiles(self, obj) -> list[dict]:
        return UserEntityProfileSerializer(perfiles_del_usuario(obj), many=True).data

    def _estado_modulos(self) -> tuple[list[dict], list[dict]]:
        """Calcula (habilitados, bloqueados) según el calendario para `timezone.now()`.

        Deriva del selector de calendario (fuente única temporal). Total 2 queries:
        una agregada del selector (controlados/habilitados) y otra para resolver
        `app_label`/`model` de los CT involucrados; el resultado se cachea en la
        instancia para que los dos `SerializerMethodField` no lo recalculen. Los
        campos reflejan el **estado temporal del módulo**, no la exención del admin:
        para admin/superusuario un módulo fuera de ventana aparece en
        `modulos_bloqueados` aunque el gate (`IsModuleEnabled`) no lo bloquee.
        """
        cache = getattr(self, "_cache_estado_modulos", None)
        if cache is not None:
            return cache

        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone

        from apps.calendario.selectors import (
            content_types_controlados,
            content_types_habilitados,
        )

        now = timezone.now()
        controlados = content_types_controlados(now)
        habilitados = content_types_habilitados(now)
        bloqueados = controlados - habilitados
        involucrados = controlados
        if not involucrados:
            self._cache_estado_modulos: tuple[list[dict], list[dict]] = ([], [])
            return self._cache_estado_modulos
        metadatos = {
            ct.id: (ct.app_label, ct.model)
            for ct in ContentType.objects.filter(id__in=involucrados)
        }

        def _fila(ct_id: int) -> dict:
            app_label, model = metadatos.get(ct_id, ("", ""))
            return {"app_label": app_label, "model": model, "content_type_id": ct_id}

        self._cache_estado_modulos = (
            [_fila(ct_id) for ct_id in habilitados],
            [_fila(ct_id) for ct_id in bloqueados],
        )
        return self._cache_estado_modulos

    def get_modulos_habilitados(self, obj) -> list[dict]:
        habilitados, _ = self._estado_modulos()
        return habilitados

    def get_modulos_bloqueados(self, obj) -> list[dict]:
        _, bloqueados = self._estado_modulos()
        return bloqueados


# --- Administración de usuarios, grupos y permisos (solo superadministrador) ---


def _validar_password(value: str) -> str:
    """Aplica los validadores de contraseña de Django y traduce los errores a DRF."""
    try:
        validate_password(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return value


class GroupBriefSerializer(serializers.ModelSerializer):
    """Detalle reducido de un grupo (rol) para mostrar nombres legibles en la UI."""

    class Meta:
        model = Group
        fields = ["id", "name"]


class ContentTypeSerializer(serializers.Serializer):
    """Tipo de contenido (`ContentType`) de Django, para poblar selectores del frontend.

    Serializa instancias de `ContentType`. El frontend usa esta lista (paginada,
    con `?search=`) para el selector `content_types[]` del CRUD de `calendar-activities`
    y para interpretar `modulos_habilitados`/`modulos_bloqueados` de `/auth/me/`.
    """

    id = serializers.IntegerField(read_only=True, help_text="ID del ContentType")
    app_label = serializers.CharField(read_only=True, help_text="App de Django (p. ej. convenios)")
    model = serializers.CharField(
        read_only=True, help_text="Modelo de Django en minúscula (p. ej. convention)"
    )
    verbose_name = serializers.SerializerMethodField(
        help_text="Nombre legible en español del modelo"
    )

    def get_verbose_name(self, obj) -> str:
        """Nombre legible del modelo; fallback a `ct.name` si el CT es huérfano."""
        modelo = obj.model_class()
        return str(modelo._meta.verbose_name) if modelo is not None else obj.name


class PermissionSerializer(serializers.ModelSerializer):
    """Catálogo de permisos (solo lectura) con el `content_type` desglosado."""

    app_label = serializers.CharField(source="content_type.app_label", read_only=True)
    model = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "content_type", "app_label", "model"]
        read_only_fields = fields


class UserReadSerializer(serializers.ModelSerializer):
    """Lectura de usuarios: nunca expone la contraseña ni su hash."""

    groups_detalle = GroupBriefSerializer(source="groups", many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "groups",
            "groups_detalle",
        ]
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    """Alta de usuarios: contraseña write-only hasheada con `set_password`."""

    password = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="Ya existe un usuario con este correo electrónico.",
            )
        ],
    )
    groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), required=False
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
        ]

    def validate_password(self, value: str) -> str:
        return _validar_password(value)

    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        user.groups.set(groups)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Edición de usuarios. La contraseña se cambia solo por la acción `set-password`."""

    email = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="Ya existe un usuario con este correo electrónico.",
            )
        ],
    )
    groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), required=False
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
        ]

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if groups is not None:
            instance.groups.set(groups)
        return instance


class SetPasswordSerializer(serializers.Serializer):
    """Cambio de contraseña: valida la fortaleza con los validadores de Django."""

    password = serializers.CharField(write_only=True, required=True)

    def validate_password(self, value: str) -> str:
        return _validar_password(value)


class ChangeOwnPasswordSerializer(serializers.Serializer):
    """Cambio de la propia contraseña: exige la clave actual y valida la nueva.

    Usada por el interno para reemplazar su contraseña temporal (RN-22): al hacerlo
    se limpia el flag ``debe_cambiar_password``.
    """

    password_actual = serializers.CharField(write_only=True, required=True)
    password_nueva = serializers.CharField(write_only=True, required=True)

    def validate_password_nueva(self, value: str) -> str:
        return _validar_password(value)


class GroupSerializer(serializers.ModelSerializer):
    """CRUD de grupos (roles) con asignación de permisos por PK."""

    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )
    permissions_detalle = PermissionSerializer(
        source="permissions", many=True, read_only=True
    )

    class Meta:
        model = Group
        fields = ["id", "name", "permissions", "permissions_detalle"]

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        group = Group.objects.create(**validated_data)
        group.permissions.set(permissions)
        return group

    def update(self, instance, validated_data):
        permissions = validated_data.pop("permissions", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if permissions is not None:
            instance.permissions.set(permissions)
        return instance


# --- Escritura del alcance por objeto (UserEntityProfile, T10) ---

# Import puntual de los modelos institucionales (mismo patrón cross-app que ya usa
# `apps.common.selectors` con `UserEntityProfile`). Necesarios para la allowlist.
from apps.convenios.models import (  # noqa: E402
    Conapres,
    ExecutingUnit,
    Ipress,
    OrganDirectory,
    RegionalGovernment,
    University,
)
from apps.internados.models import Student  # noqa: E402

# Allowlist de entidades institucionales sobre las que tiene sentido otorgar
# alcance (scope por objeto) a un usuario. **Fuente única** compartida por el
# lookup de tipos de entidad asignables (T11, `AssignableEntityTypeView`) y por la
# validación de escritura de perfiles (T10, `UserEntityProfileWriteSerializer`):
# así el catálogo que ofrece el lookup y el conjunto que acepta el POST de perfiles
# no pueden divergir. No incluye modelos no institucionales (documentos, auditoría,
# catálogos, historial) ni entidades de la app `actividades` (no hay rol cuyo
# alcance sea una actividad).
ASSIGNABLE_PROFILE_MODELS = (
    University,
    Ipress,
    RegionalGovernment,
    OrganDirectory,
    ExecutingUnit,
    Conapres,
    Student,
)


class UserEntityProfileWriteSerializer(serializers.Serializer):
    """Entrada para otorgar a un usuario acceso a una o varias entidades bajo un rol.

    Payload genérico ``{ "rol": <group_id>, "tipo_entidad": "university",
    "ids": [3, 7] }``. El vínculo del modelo es polimórfico
    (``tipo_contenido`` → ``ContentType``), por lo que el mismo endpoint sirve
    para cualquier entidad admitida (universidades, IPRESS, sedes, etc.).
    """

    rol = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        required=True,
        error_messages={
            "does_not_exist": "El rol indicado no existe.",
            "required": "El rol es obligatorio.",
        },
        help_text="Identificador (PK) del rol (Group) a otorgar.",
    )
    tipo_entidad = serializers.CharField(
        required=True,
        help_text="Nombre del modelo de la entidad en minúscula (p. ej. 'university').",
    )
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        required=True,
        help_text="Lista de identificadores (PK) de las entidades a otorgar.",
    )

    def validate_tipo_entidad(self, value: str) -> str:
        """Resuelve el `ContentType` validándolo contra la allowlist de perfiles.

        Solo se aceptan los modelos de ``ASSIGNABLE_PROFILE_MODELS`` (misma fuente
        única que consume el lookup de T11), evitando otorgar alcance sobre modelos
        no institucionales (documentos, auditoría, catálogos, etc.).
        """
        modelo = value.strip().lower()
        cts_admitidos = ContentType.objects.get_for_models(*ASSIGNABLE_PROFILE_MODELS)
        content_type = next(
            (ct for ct in cts_admitidos.values() if ct.model == modelo), None
        )
        if content_type is None:
            raise serializers.ValidationError(
                "El tipo de entidad indicado no es válido o no es asignable a un perfil."
            )
        # Se conserva el ContentType resuelto para reutilizarlo en `validate`.
        self._content_type = content_type
        return modelo

    def validate(self, attrs):
        """Verifica que cada id de `ids` exista en el modelo resuelto por el tipo de entidad."""
        content_type = getattr(self, "_content_type", None)
        ids = attrs.get("ids")
        # Si `tipo_entidad`/`ids` no validaron, DRF ya acumuló su error; se aborta.
        if content_type is None or not ids:
            return attrs
        modelo = content_type.model_class()
        existentes = set(
            modelo.objects.filter(pk__in=ids).values_list("pk", flat=True)
        )
        faltantes = [pk for pk in ids if pk not in existentes]
        if faltantes:
            listado = ", ".join(str(pk) for pk in faltantes)
            raise serializers.ValidationError(
                {
                    "ids": [
                        "No existen entidades del tipo indicado con los "
                        f"siguientes identificadores: {listado}."
                    ]
                }
            )
        attrs["tipo_contenido"] = content_type
        return attrs


class UserEntityProfileWriteReadSerializer(UserEntityProfileSerializer):
    """Salida de la gestión de perfiles: forma de lectura más `id` y `activo`.

    Reutiliza los 4 campos publicados por ``UserEntityProfileSerializer``
    (``tipo_entidad``, ``id_objeto``, ``entidad``, ``rol``) y añade ``id`` (PK del
    perfil) y ``activo`` para permitir la baja lógica y la re-alta.
    """

    id = serializers.IntegerField(read_only=True)
    activo = serializers.BooleanField(read_only=True)


# --- Lookup de tipos de entidad asignables a perfiles (T11) ---


class AssignableEntityTypeSerializer(serializers.Serializer):
    """Tipo de entidad elegible para asignar un perfil de usuario (scope por objeto).

    Alimenta el selector «Tipo de entidad» del alta de perfiles. El campo
    ``tipo_entidad`` es exactamente el string que espera el POST de perfiles (T10);
    ``id`` (ContentType) se expone solo por paridad con el precedente y como dato
    informativo — el frontend debe reenviar ``tipo_entidad``, no ``id``.
    """

    id = serializers.IntegerField(
        help_text="ID del ContentType (informativo; el write usa tipo_entidad)."
    )
    tipo_entidad = serializers.CharField(
        help_text=(
            "Nombre de modelo en minúscula; valor que espera el POST de perfiles "
            "(p. ej. university, student)."
        )
    )
    label = serializers.CharField(
        help_text="Etiqueta legible en español (verbose_name del modelo)."
    )
    app_label = serializers.CharField(
        help_text="App de Django (p. ej. convenios, internados)."
    )
