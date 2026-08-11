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

    def get_nombre(self, obj) -> str:
        return obj.get_full_name() or obj.get_username()

    def get_debe_cambiar_password(self, obj) -> bool:
        return _debe_cambiar_password(obj)

    def get_grupos(self, obj) -> list[str]:
        return grupos_del_usuario(obj)

    def get_perfiles(self, obj) -> list[dict]:
        return UserEntityProfileSerializer(perfiles_del_usuario(obj), many=True).data


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

# Apps admitidas para resolver el `ContentType` por nombre de modelo, evitando
# ambigüedad de nombres entre distintas apps del proyecto.
APPS_ENTIDADES_ADMITIDAS = ("convenios", "internados", "actividades")


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
        """Resuelve el `ContentType` por nombre de modelo, acotado a las apps admitidas."""
        modelo = value.strip().lower()
        content_type = ContentType.objects.filter(
            app_label__in=APPS_ENTIDADES_ADMITIDAS, model=modelo
        ).first()
        if content_type is None:
            raise serializers.ValidationError(
                "El tipo de entidad indicado no es válido."
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
