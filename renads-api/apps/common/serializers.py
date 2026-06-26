"""Serializers transversales: JWT con claims de roles y datos del usuario actual."""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.common.selectors import grupos_del_usuario, perfiles_del_usuario


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Agrega los roles y el nombre del usuario a los claims del token JWT."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["nombre"] = user.get_full_name() or user.get_username()
        token["grupos"] = list(user.groups.values_list("name", flat=True))
        return token


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
