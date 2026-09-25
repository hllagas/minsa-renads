"""Pruebas de los modelos transversales: ``UserSecurity``, ``UserProfile`` y el
helper ``debe_cambiar_password``."""

from django.db import IntegrityError
from django.test import TestCase

from apps.common.models import UserProfile, UserSecurity, debe_cambiar_password
from apps.common.tests.factories import crear_cargo, crear_unidad_organica, crear_usuario


class UserSecurityModelTests(TestCase):
    """Modelo de ajustes de seguridad por usuario."""

    @classmethod
    def setUpTestData(cls):
        cls.user = crear_usuario(username="12345678")

    def test_creacion_con_defaults(self):
        # Happy: se crea con los valores por defecto esperados.
        seguridad = UserSecurity.objects.create(usuario=self.user)
        self.assertFalse(seguridad.debe_cambiar_password)
        self.assertFalse(seguridad.two_factor_enabled)
        self.assertEqual(seguridad.two_factor_method, "")
        self.assertEqual(seguridad.totp_secret, "")
        self.assertIsNone(seguridad.otp_expires_at)

    def test_relacion_uno_a_uno_unica(self):
        # Unhappy: no puede haber dos registros de seguridad para el mismo usuario.
        UserSecurity.objects.create(usuario=self.user)
        with self.assertRaises(IntegrityError):
            UserSecurity.objects.create(usuario=self.user)


class UserProfileModelTests(TestCase):
    """Modelo de perfil de usuario (todos los campos obligatorios; str)."""

    @classmethod
    def setUpTestData(cls):
        cls.unidad = crear_unidad_organica()
        cls.cargo = crear_cargo(unidad=cls.unidad)

    def _crear_perfil(self, user, numero="99887766", telefono="987654321"):
        return UserProfile.objects.create(
            usuario=user,
            tipo_documento="DNI",
            numero_documento=numero,
            telefono=telefono,
            unidad_organica=self.unidad,
            cargo=self.cargo,
        )

    def test_str_usa_nombre_completo(self):
        # Happy: __str__ compone first_name + last_name de auth_user.
        user = crear_usuario(username="p1", first_name="Ana", last_name="Diaz Gil")
        perfil = self._crear_perfil(user)
        self.assertEqual(str(perfil), "Ana Diaz Gil")

    def test_str_fallback_a_username(self):
        # Edge: sin nombre ni apellidos, cae al username.
        user = crear_usuario(username="solouser", first_name="", last_name="")
        perfil = self._crear_perfil(user, numero="11112222", telefono="911112222")
        self.assertEqual(str(perfil), "solouser")

    def test_numero_documento_unico(self):
        # Unhappy: numero_documento es único.
        u1 = crear_usuario(username="u1")
        u2 = crear_usuario(username="u2", email="u2@renads.test")
        self._crear_perfil(u1, numero="55556666", telefono="955556666")
        with self.assertRaises(IntegrityError):
            self._crear_perfil(u2, numero="55556666", telefono="900001111")

    def test_telefono_unico(self):
        # Unhappy: telefono es único.
        u1 = crear_usuario(username="u3")
        u2 = crear_usuario(username="u4", email="u4@renads.test")
        self._crear_perfil(u1, numero="70001111", telefono="970001111")
        with self.assertRaises(IntegrityError):
            self._crear_perfil(u2, numero="70002222", telefono="970001111")


class DebeCambiarPasswordHelperTests(TestCase):
    """Helper ``debe_cambiar_password`` a nivel de módulo."""

    @classmethod
    def setUpTestData(cls):
        cls.user = crear_usuario(username="dcp")

    def test_sin_registro_seguridad_devuelve_false(self):
        # Edge: usuario sin UserSecurity → False por defecto.
        self.assertFalse(debe_cambiar_password(self.user))

    def test_flag_activo_devuelve_true(self):
        # Happy: flag en True.
        UserSecurity.objects.create(usuario=self.user, debe_cambiar_password=True)
        self.assertTrue(debe_cambiar_password(self.user))

    def test_flag_inactivo_devuelve_false(self):
        # Unhappy/edge: flag en False.
        user = crear_usuario(username="dcp2", email="dcp2@renads.test")
        UserSecurity.objects.create(usuario=user, debe_cambiar_password=False)
        self.assertFalse(debe_cambiar_password(user))
