"""Serializers transversales: JWT con claims de roles, datos del usuario actual
y administración de usuarios, grupos (roles) y permisos (solo superadministrador)."""

from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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
        return token

    def validate(self, attrs):
        """Enriquece el body de la respuesta de login con datos de identidad."""
        data = super().validate(attrs)
        data["es_superusuario"] = self.user.is_superuser
        data["nombre"] = self.user.get_full_name() or self.user.get_username()
        data["grupos"] = list(self.user.groups.values_list("name", flat=True))
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
    grupos = serializers.SerializerMethodField()
    perfiles = serializers.SerializerMethodField()

    def get_nombre(self, obj) -> str:
        return obj.get_full_name() or obj.get_username()

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
