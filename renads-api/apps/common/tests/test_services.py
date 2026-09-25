"""Pruebas de los services transversales: auditoría, documentos versionados, 2FA,
gestión de contraseñas y perfil de usuario."""

import hashlib
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from apps.common import services
from apps.common.models import UserProfile, UserSecurity
from apps.common.tests.factories import (
    crear_cargo,
    crear_unidad_organica,
    crear_usuario,
)
from apps.convenios.models import AuditLog, Document


class RegistrarAuditoriaTests(TestCase):
    """``registrar_auditoria`` (RNF-AUD-01/02)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = crear_usuario(username="aud")
        cls.grupo_obj = crear_unidad_organica()

    def test_registra_con_usuario_autenticado(self):
        # Happy: registra la operación con usuario válido.
        log = services.registrar_auditoria(self.user, "CREAR", self.grupo_obj)
        self.assertEqual(log.accion, "CREAR")
        self.assertEqual(log.usuario, self.user)
        # id_objeto es CharField; se compara normalizando a str (código RENIPRESS o pk).
        self.assertEqual(str(log.id_objeto), str(self.grupo_obj.pk))

    def test_usuario_no_autenticado_queda_nulo(self):
        # Unhappy: un usuario sin is_authenticated se persiste como NULL.
        class Anon:
            is_authenticated = False

        log = services.registrar_auditoria(Anon(), "CREAR", self.grupo_obj)
        self.assertIsNone(log.usuario)

    def test_valores_none_se_normalizan_a_cadena_vacia(self):
        # Edge: valor_anterior/nuevo None → "".
        log = services.registrar_auditoria(
            self.user, "ACTUALIZAR", self.grupo_obj,
            nombre_campo="nombre", valor_anterior=None, valor_nuevo=None,
        )
        self.assertEqual(log.valor_anterior, "")
        self.assertEqual(log.valor_nuevo, "")


class AdjuntarDocumentoTests(TestCase):
    """``adjuntar_documento`` — versionado por (objeto, documento_anexo)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = crear_usuario(username="doc")
        # Objeto destino: reutilizamos un User como objeto genérico (tiene pk entero).
        cls.objeto = crear_usuario(username="objeto-destino", email="obj@renads.test")
        from apps.internados.models import AnnexDocument

        cls.anexo = AnnexDocument.objects.create(
            codigo="DJ-VERACIDAD", nombre="DJ Veracidad", tipo_actor="INTERNO"
        )
        cls.anexo2 = AnnexDocument.objects.create(
            codigo="DJ-SALUD", nombre="DJ Salud", tipo_actor="INTERNO"
        )

    def test_primera_version(self):
        # Happy: primer documento → versión 1, estado ACTIVO, sin anterior.
        doc = services.adjuntar_documento(
            self.objeto, referencia_externa="ref/1.pdf",
            usuario=self.user, documento_anexo=self.anexo,
        )
        self.assertEqual(doc.version, 1)
        self.assertEqual(doc.estado, "ACTIVO")
        self.assertIsNone(doc.version_anterior)
        self.assertTrue(AuditLog.objects.filter(accion="CREAR").exists())

    def test_versionado_reemplaza_anterior(self):
        # Happy: segundo documento incrementa versión y reemplaza el anterior.
        doc1 = services.adjuntar_documento(
            self.objeto, referencia_externa="ref/1.pdf",
            usuario=self.user, documento_anexo=self.anexo,
        )
        doc2 = services.adjuntar_documento(
            self.objeto, referencia_externa="ref/2.pdf",
            usuario=self.user, documento_anexo=self.anexo,
        )
        doc1.refresh_from_db()
        self.assertEqual(doc2.version, 2)
        self.assertEqual(doc2.version_anterior_id, doc1.id)
        self.assertEqual(doc1.estado, "REEMPLAZADO")

    def test_cadenas_independientes_por_anexo(self):
        # Edge: cada documento_anexo mantiene su propia cadena de versiones.
        d_a = services.adjuntar_documento(
            self.objeto, referencia_externa="a.pdf",
            usuario=self.user, documento_anexo=self.anexo,
        )
        d_b = services.adjuntar_documento(
            self.objeto, referencia_externa="b.pdf",
            usuario=self.user, documento_anexo=self.anexo2,
        )
        self.assertEqual(d_a.version, 1)
        self.assertEqual(d_b.version, 1)


class SessionTokenTests(TestCase):
    """JWT de sesión diferida 2FA (``generar_session_token`` / ``validar_session_token``)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = crear_usuario(username="st")

    def test_roundtrip_valido(self):
        # Happy: el token generado se valida y devuelve el mismo usuario.
        token = services.generar_session_token(self.user)
        usuario = services.validar_session_token(token)
        self.assertEqual(usuario.pk, self.user.pk)

    def test_token_malformado(self):
        # Unhappy: token basura → SESSION_INVALIDA.
        with self.assertRaises(AuthenticationFailed) as ctx:
            services.validar_session_token("no-es-un-token")
        self.assertEqual(ctx.exception.detail.code, "SESSION_INVALIDA")

    def test_token_expirado(self):
        # Unhappy: token expirado → SESSION_EXPIRADA.
        import datetime as dt

        import jwt
        from django.conf import settings

        payload = {
            "sub": str(self.user.pk),
            "scope": "2fa_pending",
            "exp": dt.datetime.utcnow() - dt.timedelta(minutes=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        with self.assertRaises(AuthenticationFailed) as ctx:
            services.validar_session_token(token)
        self.assertEqual(ctx.exception.detail.code, "SESSION_EXPIRADA")

    def test_scope_incorrecto(self):
        # Unhappy: scope distinto de 2fa_pending → SESSION_INVALIDA.
        import datetime as dt

        import jwt
        from django.conf import settings

        payload = {
            "sub": str(self.user.pk),
            "scope": "otro",
            "exp": dt.datetime.utcnow() + dt.timedelta(minutes=5),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        with self.assertRaises(AuthenticationFailed) as ctx:
            services.validar_session_token(token)
        self.assertEqual(ctx.exception.detail.code, "SESSION_INVALIDA")

    def test_usuario_inactivo(self):
        # Edge: usuario inactivo → SESSION_INVALIDA.
        inactivo = crear_usuario(username="inact", email="inact@renads.test")
        token = services.generar_session_token(inactivo)
        inactivo.is_active = False
        inactivo.save(update_fields=["is_active"])
        with self.assertRaises(AuthenticationFailed) as ctx:
            services.validar_session_token(token)
        self.assertEqual(ctx.exception.detail.code, "SESSION_INVALIDA")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class OtpEmailTests(TestCase):
    """OTP por correo: generación, validación y rate-limit."""

    @classmethod
    def setUpTestData(cls):
        cls.user = crear_usuario(username="otp", email="otp@renads.test")

    def setUp(self):
        self.sec = UserSecurity.objects.create(usuario=self.user)
        mail.outbox = []

    def test_generar_otp_envia_correo_y_guarda_hash(self):
        # Happy: genera OTP, hashea, guarda y envía correo.
        with patch("apps.common.services.secrets.randbelow", return_value=123456):
            services.generar_otp_email(self.sec)
        self.sec.refresh_from_db()
        esperado = hashlib.sha256("123456".encode()).hexdigest()
        self.assertEqual(self.sec.otp_code, esperado)
        self.assertIsNotNone(self.sec.otp_expires_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("123456", self.sec.otp_code)  # no se guarda en claro

    def test_validar_otp_correcto_limpia_campos(self):
        # Happy: código correcto → True y limpia campos.
        with patch("apps.common.services.secrets.randbelow", return_value=222333):
            services.generar_otp_email(self.sec)
        self.assertTrue(services.validar_otp_email(self.sec, "222333"))
        self.sec.refresh_from_db()
        self.assertEqual(self.sec.otp_code, "")
        self.assertIsNone(self.sec.otp_expires_at)

    def test_validar_otp_incorrecto(self):
        # Unhappy: código incorrecto → False.
        with patch("apps.common.services.secrets.randbelow", return_value=444555):
            services.generar_otp_email(self.sec)
        self.assertFalse(services.validar_otp_email(self.sec, "000000"))

    def test_validar_otp_sin_otp_pendiente(self):
        # Edge: sin OTP en curso → False.
        self.assertFalse(services.validar_otp_email(self.sec, "123456"))

    def test_validar_otp_expirado(self):
        # Edge: OTP expirado → False.
        with patch("apps.common.services.secrets.randbelow", return_value=555666):
            services.generar_otp_email(self.sec)
        self.sec.otp_expires_at = timezone.now() - timedelta(seconds=1)
        self.sec.save(update_fields=["otp_expires_at"])
        self.assertFalse(services.validar_otp_email(self.sec, "555666"))

    def test_puede_reenviar_sin_otp(self):
        # Happy: sin OTP en curso siempre se puede reenviar.
        self.assertTrue(services.puede_reenviar_otp(self.sec))

    def test_puede_reenviar_recien_enviado(self):
        # Unhappy: OTP recién enviado (dentro del minuto) → False.
        with patch("apps.common.services.secrets.randbelow", return_value=1):
            services.generar_otp_email(self.sec)
        self.assertFalse(services.puede_reenviar_otp(self.sec))

    def test_puede_reenviar_tras_pasar_un_minuto(self):
        # Edge: pasado más de 1 minuto desde el envío → True.
        with patch("apps.common.services.secrets.randbelow", return_value=1):
            services.generar_otp_email(self.sec)
        # Adelanta el reloj: deja el OTP a punto de expirar (más de 1 min transcurrido).
        self.sec.otp_expires_at = timezone.now() + timedelta(seconds=30)
        self.sec.save(update_fields=["otp_expires_at"])
        self.assertTrue(services.puede_reenviar_otp(self.sec))


class TotpEmail2faActivacionTests(TestCase):
    """Activación/desactivación de 2FA (TOTP y EMAIL)."""

    def setUp(self):
        self.user = crear_usuario(username="2fa", email="2fa@renads.test", password="ClaveActual9!")
        self.sec = UserSecurity.objects.create(usuario=self.user)

    def test_activar_totp_sin_secreto(self):
        # Unhappy: sin totp_secret configurado → ValidationError.
        with self.assertRaises(ValidationError):
            services.activar_2fa_totp(self.sec, "000000", self.user)

    def test_activar_totp_codigo_invalido(self):
        # Unhappy: código TOTP inválido → ValidationError.
        import pyotp

        self.sec.totp_secret = pyotp.random_base32()
        self.sec.save(update_fields=["totp_secret"])
        with self.assertRaises(ValidationError):
            services.activar_2fa_totp(self.sec, "000000", self.user)

    def test_activar_totp_ok(self):
        # Happy: código válido → activa TOTP y audita.
        import pyotp

        secret = pyotp.random_base32()
        self.sec.totp_secret = secret
        self.sec.save(update_fields=["totp_secret"])
        codigo = pyotp.TOTP(secret).now()
        services.activar_2fa_totp(self.sec, codigo, self.user)
        self.sec.refresh_from_db()
        self.assertTrue(self.sec.two_factor_enabled)
        self.assertEqual(self.sec.two_factor_method, "TOTP")
        self.assertTrue(AuditLog.objects.filter(accion="ACTIVAR_2FA_TOTP").exists())

    def test_activar_email_password_incorrecta(self):
        # Unhappy: contraseña incorrecta → ValidationError.
        with self.assertRaises(ValidationError):
            services.activar_2fa_email(self.sec, "malaClave", self.user)

    def test_activar_email_ok_limpia_totp(self):
        # Happy: contraseña correcta activa EMAIL y limpia el secreto TOTP.
        self.sec.totp_secret = "SECRETO"
        self.sec.save(update_fields=["totp_secret"])
        services.activar_2fa_email(self.sec, "ClaveActual9!", self.user)
        self.sec.refresh_from_db()
        self.assertTrue(self.sec.two_factor_enabled)
        self.assertEqual(self.sec.two_factor_method, "EMAIL")
        self.assertEqual(self.sec.totp_secret, "")

    def test_desactivar_password_incorrecta(self):
        # Unhappy: contraseña incorrecta → ValidationError.
        self.sec.two_factor_enabled = True
        self.sec.two_factor_method = "EMAIL"
        self.sec.save()
        with self.assertRaises(ValidationError):
            services.desactivar_2fa(self.sec, "mala", "123456", self.user)

    def test_desactivar_totp_ok(self):
        # Happy: desactiva 2FA método TOTP con password + OTP válidos.
        import pyotp

        secret = pyotp.random_base32()
        self.sec.two_factor_enabled = True
        self.sec.two_factor_method = "TOTP"
        self.sec.totp_secret = secret
        self.sec.save()
        codigo = pyotp.TOTP(secret).now()
        services.desactivar_2fa(self.sec, "ClaveActual9!", codigo, self.user)
        self.sec.refresh_from_db()
        self.assertFalse(self.sec.two_factor_enabled)
        self.assertEqual(self.sec.two_factor_method, "")
        self.assertEqual(self.sec.totp_secret, "")

    def test_desactivar_email_otp_invalido(self):
        # Unhappy: método EMAIL con OTP inválido → ValidationError.
        self.sec.two_factor_enabled = True
        self.sec.two_factor_method = "EMAIL"
        self.sec.save()
        with self.assertRaises(ValidationError):
            services.desactivar_2fa(self.sec, "ClaveActual9!", "000000", self.user)


class GenerarPasswordSeguraTests(TestCase):
    """``generar_password_segura`` (R-3)."""

    def test_longitud_y_composicion(self):
        # Happy: 12 caracteres con al menos una de cada clase requerida.
        pw = services.generar_password_segura()
        self.assertEqual(len(pw), 12)
        self.assertTrue(any(c.islower() for c in pw))
        self.assertTrue(any(c.isupper() for c in pw))
        self.assertTrue(any(c.isdigit() for c in pw))
        self.assertTrue(any(c in "!@#$%^&*" for c in pw))

    def test_no_deterministico(self):
        # Edge: dos generaciones distintas (probabilísticamente).
        self.assertNotEqual(
            services.generar_password_segura(), services.generar_password_segura()
        )


class CrearUsuarioConPerfilTests(TestCase):
    """``crear_usuario_con_perfil`` (R-5, RN-username)."""

    @classmethod
    def setUpTestData(cls):
        cls.unidad = crear_unidad_organica()
        cls.cargo = crear_cargo(unidad=cls.unidad)

    def _profile_data(self, numero="87654321", telefono="912345678"):
        return {
            "tipo_documento": "DNI",
            "numero_documento": numero,
            "telefono": telefono,
            "unidad_organica": self.unidad,
            "cargo": self.cargo,
        }

    def test_no_super_username_desde_documento(self):
        # Happy: no-superusuario → username = numero_documento; crea perfil + seguridad.
        user, pw = services.crear_usuario_con_perfil(
            {"email": "a@renads.test", "first_name": "A", "last_name": "B C"},
            [], self._profile_data(numero="87654321"),
        )
        self.assertEqual(user.username, "87654321")
        self.assertTrue(len(pw) >= 12)
        self.assertTrue(UserProfile.objects.filter(usuario=user).exists())
        sec = UserSecurity.objects.get(usuario=user)
        self.assertFalse(sec.debe_cambiar_password)
        self.assertIsNotNone(sec.password_changed_at)

    def test_super_respeta_username_y_sin_perfil(self):
        # Happy: superusuario → username explícito, sin perfil.
        user, _ = services.crear_usuario_con_perfil(
            {"username": "root", "email": "root@renads.test", "is_superuser": True},
            [], {},
        )
        self.assertEqual(user.username, "root")
        self.assertFalse(UserProfile.objects.filter(usuario=user).exists())

    def test_password_explicita_se_respeta(self):
        # Edge: si viene password se usa esa, no se genera.
        user, pw = services.crear_usuario_con_perfil(
            {"email": "pw@renads.test", "first_name": "P", "last_name": "Q",
             "password": "MiClaveFija9!"},
            [], self._profile_data(numero="10101010", telefono="910101010"),
        )
        self.assertEqual(pw, "MiClaveFija9!")
        self.assertTrue(user.check_password("MiClaveFija9!"))


class ActualizarPerfilUsuarioTests(TestCase):
    """``actualizar_perfil_usuario`` (R-8/R-9)."""

    @classmethod
    def setUpTestData(cls):
        cls.unidad = crear_unidad_organica()
        cls.cargo = crear_cargo(unidad=cls.unidad)

    def _crear_con_perfil(self, username="p"):
        user = crear_usuario(username=username, email=f"{username}@renads.test")
        UserProfile.objects.create(
            usuario=user, tipo_documento="DNI", numero_documento=username + "0",
            telefono="9" + username.ljust(8, "0")[:8], unidad_organica=self.unidad,
            cargo=self.cargo,
        )
        return user

    def test_update_parcial_perfil_existente(self):
        # Happy: actualiza solo el teléfono de un perfil existente.
        user = self._crear_con_perfil("aa")
        perfil = services.actualizar_perfil_usuario(user, {"telefono": "999888777"})
        self.assertEqual(perfil.telefono, "999888777")

    def test_sin_perfil_sin_datos_devuelve_none(self):
        # Edge: sin perfil y sin datos → None (no crea perfil vacío).
        user = crear_usuario(username="np", email="np@renads.test")
        self.assertIsNone(services.actualizar_perfil_usuario(user, {}))

    def test_sin_perfil_faltan_campos_obligatorios(self):
        # Unhappy: sin perfil y sin los 5 campos obligatorios → ValidationError.
        user = crear_usuario(username="nf", email="nf@renads.test")
        with self.assertRaises(ValidationError):
            services.actualizar_perfil_usuario(user, {"tipo_documento": "DNI"})

    def test_sin_perfil_con_todos_los_campos_crea(self):
        # Happy: sin perfil pero con los 5 campos obligatorios → crea el perfil.
        user = crear_usuario(username="cc", email="cc@renads.test")
        perfil = services.actualizar_perfil_usuario(user, {
            "tipo_documento": "DNI", "numero_documento": "33334444",
            "telefono": "933334444", "unidad_organica": self.unidad,
            "cargo": self.cargo,
        })
        self.assertIsNotNone(perfil)
        self.assertEqual(perfil.numero_documento, "33334444")

    def test_perfil_existente_sin_datos_devuelve_perfil(self):
        # Edge: perfil existente y profile_data vacío → devuelve el perfil sin cambios.
        user = self._crear_con_perfil("bb")
        perfil = services.actualizar_perfil_usuario(user, {})
        self.assertIsNotNone(perfil)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ResetPasswordTests(TestCase):
    """Flujo de recuperación de contraseña (R-6)."""

    def setUp(self):
        self.user = crear_usuario(username="rp", email="rp@renads.test", password="ClaveVieja9!")
        mail.outbox = []

    def test_solicitar_usuario_inexistente_silencioso(self):
        # Edge: usuario inexistente → no lanza (anti-enumeración), no envía correo.
        services.solicitar_reset_password("noexiste")
        self.assertEqual(len(mail.outbox), 0)

    def test_solicitar_usuario_sin_correo_silencioso(self):
        # Edge: usuario sin correo → no envía.
        u = crear_usuario(username="sinmail", email="")
        services.solicitar_reset_password("sinmail")
        self.assertEqual(len(mail.outbox), 0)

    def test_solicitar_envia_otp(self):
        # Happy: usuario válido con correo → envía OTP.
        services.solicitar_reset_password("rp")
        self.assertEqual(len(mail.outbox), 1)

    def test_solicitar_rate_limit(self):
        # Unhappy: segunda solicitud inmediata → ValidationError (rate-limit).
        services.solicitar_reset_password("rp")
        with self.assertRaises(ValidationError):
            services.solicitar_reset_password("rp")

    def test_confirmar_usuario_inexistente(self):
        # Unhappy: confirmar con usuario inexistente → ValidationError.
        with self.assertRaises(ValidationError):
            services.confirmar_reset_password("noexiste", "123456", "NuevaClave9!")

    def test_confirmar_sin_seguridad(self):
        # Unhappy: usuario sin UserSecurity → ValidationError.
        u = crear_usuario(username="nosec", email="nosec@renads.test")
        with self.assertRaises(ValidationError):
            services.confirmar_reset_password("nosec", "123456", "NuevaClave9!")

    def test_confirmar_otp_invalido(self):
        # Unhappy: OTP inválido → ValidationError.
        UserSecurity.objects.create(usuario=self.user)
        with self.assertRaises(ValidationError):
            services.confirmar_reset_password("rp", "000000", "NuevaClave9!")

    def test_confirmar_ok_cambia_password(self):
        # Happy: OTP válido + contraseña fuerte → cambia password y limpia flags.
        sec = UserSecurity.objects.create(usuario=self.user)
        with patch("apps.common.services.secrets.randbelow", return_value=654321):
            services.generar_otp_email(sec)
        services.confirmar_reset_password("rp", "654321", "NuevaClaveFuerte9!")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NuevaClaveFuerte9!"))
        sec.refresh_from_db()
        self.assertFalse(sec.debe_cambiar_password)

    def test_confirmar_password_debil(self):
        # Unhappy: contraseña débil → ValidationError de los validadores de Django.
        sec = UserSecurity.objects.create(usuario=self.user)
        with patch("apps.common.services.secrets.randbelow", return_value=111222):
            services.generar_otp_email(sec)
        with self.assertRaises(ValidationError):
            services.confirmar_reset_password("rp", "111222", "123")
