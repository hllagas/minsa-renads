"""Pruebas de los serializers transversales: claims JWT, /me, perfil, alta/edición
de usuarios, grupos, content types y alcance por objeto."""

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.common import serializers as ser
from apps.common.models import UserProfile, UserSecurity
from apps.common.serializers import (
    ContentTypeSerializer,
    CustomTokenObtainPairSerializer,
    GroupSerializer,
    MeSerializer,
    UserCreateSerializer,
    UserEntityProfileWriteSerializer,
    UserProfileReadSerializer,
    UserUpdateSerializer,
    _nombre_usuario,
    _validar_password,
)
from apps.common.tests.factories import (
    crear_cargo,
    crear_grupo,
    crear_unidad_organica,
    crear_usuario,
)
from apps.convenios.models import Conapres


class NombreUsuarioTests(TestCase):
    """Helper ``_nombre_usuario`` (R-7)."""

    def test_usa_nombre_completo(self):
        user = crear_usuario(username="nu", first_name="Ana", last_name="Diaz Gil")
        self.assertEqual(_nombre_usuario(user), "Ana Diaz Gil")

    def test_fallback_a_username(self):
        user = crear_usuario(username="nu2", email="nu2@renads.test",
                             first_name="", last_name="")
        self.assertEqual(_nombre_usuario(user), "nu2")


class ValidarPasswordTests(TestCase):
    """Helper ``_validar_password``."""

    def test_password_debil_lanza(self):
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            _validar_password("123")

    def test_password_fuerte_pasa(self):
        self.assertEqual(_validar_password("ClaveFuerte9!x"), "ClaveFuerte9!x")


class CustomTokenClaimsTests(TestCase):
    """Claims agregados por ``CustomTokenObtainPairSerializer.get_token``."""

    def test_claims_incluyen_roles_y_nombre(self):
        user = crear_usuario(username="tok", first_name="Leo", last_name="Ruiz Paz",
                            grupos=["Universidad"])
        UserSecurity.objects.create(usuario=user, debe_cambiar_password=True)
        token = CustomTokenObtainPairSerializer.get_token(user)
        self.assertEqual(token["nombre"], "Leo Ruiz Paz")
        self.assertIn("Universidad", token["grupos"])
        self.assertFalse(token["es_superusuario"])
        self.assertTrue(token["debe_cambiar_password"])


class MeSerializerTests(TestCase):
    """``MeSerializer`` — identidad, roles, perfiles y estado de módulos."""

    @classmethod
    def setUpTestData(cls):
        cls.unidad = crear_unidad_organica()
        cls.cargo = crear_cargo(unidad=cls.unidad)

    def test_datos_basicos_sin_perfil(self):
        # Edge: usuario sin perfil ni seguridad.
        user = crear_usuario(username="me-a", email="mea@renads.test")
        data = MeSerializer(user).data
        self.assertEqual(data["username"], "me-a")
        self.assertIsNone(data["perfil"])
        self.assertFalse(data["two_factor_enabled"])
        self.assertEqual(data["two_factor_method"], "")
        self.assertEqual(data["modulos_habilitados"], [])
        self.assertEqual(data["modulos_bloqueados"], [])

    def test_con_perfil_y_2fa(self):
        # Happy: expone perfil y estado 2FA.
        user = crear_usuario(username="88776655", email="meb@renads.test",
                            first_name="Sara", last_name="Mora Leon")
        UserProfile.objects.create(
            usuario=user, tipo_documento="DNI", numero_documento="88776655",
            telefono="988776655", unidad_organica=self.unidad, cargo=self.cargo,
        )
        UserSecurity.objects.create(usuario=user, two_factor_enabled=True,
                                    two_factor_method="EMAIL")
        data = MeSerializer(user).data
        self.assertEqual(data["nombre"], "Sara Mora Leon")
        self.assertIsNotNone(data["perfil"])
        self.assertEqual(data["perfil"]["numero_documento"], "88776655")
        self.assertTrue(data["two_factor_enabled"])
        self.assertEqual(data["two_factor_method"], "EMAIL")


class ContentTypeSerializerTests(TestCase):
    """``ContentTypeSerializer`` — verbose_name legible."""

    def test_verbose_name_de_modelo_valido(self):
        ct = ContentType.objects.get_for_model(Conapres)
        data = ContentTypeSerializer(ct).data
        self.assertEqual(data["model"], "conapres")
        self.assertTrue(data["verbose_name"])


class UserCreateSerializerValidateTests(TestCase):
    """Validación condicional de ``UserCreateSerializer`` (RN-username)."""

    @classmethod
    def setUpTestData(cls):
        cls.unidad = crear_unidad_organica()
        cls.cargo = crear_cargo(unidad=cls.unidad)

    def _payload_no_super(self, **overrides):
        base = {
            "email": "nuevo@renads.test",
            "first_name": "Nuevo",
            "last_name": "Usuario Test",
            "tipo_documento": "DNI",
            "numero_documento": "44445555",
            "telefono": "944445555",
            "unidad_organica": self.unidad.pk,
            "cargo": self.cargo.pk,
        }
        base.update(overrides)
        return base

    def test_no_super_valido(self):
        # Happy: no-super con todos los campos → válido.
        s = UserCreateSerializer(data=self._payload_no_super())
        self.assertTrue(s.is_valid(), s.errors)

    def test_no_super_faltan_campos_obligatorios(self):
        # Unhappy: no-super sin first_name/perfil → errores por campo.
        s = UserCreateSerializer(data={"email": "x@renads.test"})
        self.assertFalse(s.is_valid())
        self.assertIn("first_name", s.errors)
        self.assertIn("numero_documento", s.errors)

    def test_super_sin_username_falla(self):
        # Unhappy: superusuario sin username → error.
        s = UserCreateSerializer(data={"email": "su@renads.test", "is_superuser": True})
        self.assertFalse(s.is_valid())
        self.assertIn("username", s.errors)

    def test_super_con_username_valido(self):
        # Happy: superusuario con username y sin perfil → válido.
        s = UserCreateSerializer(data={
            "email": "su2@renads.test", "is_superuser": True, "username": "rootx",
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_super_username_duplicado(self):
        # Unhappy: superusuario con username ya existente → error.
        crear_usuario(username="dup", email="dup@renads.test", is_superuser=True)
        s = UserCreateSerializer(data={
            "email": "su3@renads.test", "is_superuser": True, "username": "dup",
        })
        self.assertFalse(s.is_valid())
        self.assertIn("username", s.errors)

    def test_create_no_super_persiste_username_del_documento(self):
        # Happy: create de no-super → username = numero_documento y perfil creado.
        s = UserCreateSerializer(data=self._payload_no_super(numero_documento="66667777",
                                                             telefono="966667777"))
        self.assertTrue(s.is_valid(), s.errors)
        user = s.save()
        self.assertEqual(user.username, "66667777")
        self.assertTrue(UserProfile.objects.filter(usuario=user).exists())
        self.assertIsNotNone(getattr(user, "_password_generada", None))


class UserUpdateSerializerTests(TestCase):
    """``UserUpdateSerializer`` — PATCH parcial y update de perfil."""

    @classmethod
    def setUpTestData(cls):
        cls.unidad = crear_unidad_organica()
        cls.cargo = crear_cargo(unidad=cls.unidad)

    def test_update_email_y_perfil(self):
        # Happy: actualiza email y teléfono del perfil.
        user = crear_usuario(username="77778888", email="up@renads.test",
                            first_name="Up", last_name="User Test")
        UserProfile.objects.create(
            usuario=user, tipo_documento="DNI", numero_documento="77778888",
            telefono="977778888", unidad_organica=self.unidad, cargo=self.cargo,
        )
        s = UserUpdateSerializer(user, data={
            "email": "nuevo-up@renads.test", "telefono": "900000001",
        }, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        user.refresh_from_db()
        self.assertEqual(user.email, "nuevo-up@renads.test")
        self.assertEqual(user.perfil.telefono, "900000001")

    def test_telefono_en_blanco_rechazado(self):
        # Unhappy: teléfono en blanco cuando se envía → error (allow_blank=False).
        user = crear_usuario(username="ub", email="ub@renads.test")
        s = UserUpdateSerializer(user, data={"email": "ub@renads.test", "telefono": ""},
                                 partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn("telefono", s.errors)


class GroupSerializerTests(TestCase):
    """``GroupSerializer`` — CRUD de roles con permisos."""

    def test_create_con_permisos(self):
        from django.contrib.auth.models import Permission
        perm = Permission.objects.first()
        s = GroupSerializer(data={"name": "Rol Nuevo", "permissions": [perm.id]})
        self.assertTrue(s.is_valid(), s.errors)
        grupo = s.save()
        self.assertEqual(grupo.name, "Rol Nuevo")
        self.assertIn(perm, grupo.permissions.all())

    def test_update_reemplaza_permisos(self):
        from django.contrib.auth.models import Permission
        grupo = crear_grupo("Rol A")
        perms = list(Permission.objects.all()[:2])
        grupo.permissions.set([perms[0]])
        s = GroupSerializer(grupo, data={"name": "Rol A", "permissions": [perms[1].id]},
                            partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.assertEqual(list(grupo.permissions.all()), [perms[1]])


class UserProfileReadSerializerTests(TestCase):
    """``UserProfileReadSerializer`` — detalles legibles."""

    def test_detalles_de_unidad_y_cargo(self):
        unidad = crear_unidad_organica(nombre="Unidad Legible")
        cargo = crear_cargo(unidad=unidad, nombre="Cargo Legible")
        user = crear_usuario(username="pr", email="pr@renads.test")
        perfil = UserProfile.objects.create(
            usuario=user, tipo_documento="DNI", numero_documento="12121212",
            telefono="912121212", unidad_organica=unidad, cargo=cargo,
        )
        data = UserProfileReadSerializer(perfil).data
        self.assertEqual(data["unidad_organica_detalle"], "Unidad Legible")
        self.assertEqual(data["cargo_detalle"], "Cargo Legible")


class UserEntityProfileWriteSerializerTests(TestCase):
    """``UserEntityProfileWriteSerializer`` — otorgamiento de alcance por objeto."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo = crear_grupo("Universidad")
        cls.entidad = Conapres.objects.create(nombre="Conapres Uno")

    def test_valido(self):
        # Happy: tipo_entidad asignable e ids existentes → válido.
        s = UserEntityProfileWriteSerializer(data={
            "rol": self.grupo.id, "tipo_entidad": "conapres",
            "ids": [str(self.entidad.pk)],
        })
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["tipo_contenido"].model, "conapres")

    def test_tipo_entidad_no_asignable(self):
        # Unhappy: tipo fuera de la allowlist → error.
        s = UserEntityProfileWriteSerializer(data={
            "rol": self.grupo.id, "tipo_entidad": "auditlog", "ids": ["1"],
        })
        self.assertFalse(s.is_valid())
        self.assertIn("tipo_entidad", s.errors)

    def test_ids_inexistentes(self):
        # Unhappy: ids que no existen → error en ids.
        s = UserEntityProfileWriteSerializer(data={
            "rol": self.grupo.id, "tipo_entidad": "conapres", "ids": ["999999"],
        })
        self.assertFalse(s.is_valid())
        self.assertIn("ids", s.errors)

    def test_ids_vacio_rechazado(self):
        # Edge: lista vacía no permitida.
        s = UserEntityProfileWriteSerializer(data={
            "rol": self.grupo.id, "tipo_entidad": "conapres", "ids": [],
        })
        self.assertFalse(s.is_valid())
