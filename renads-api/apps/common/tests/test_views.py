"""Pruebas de las vistas/endpoints transversales vía DRF ``APIClient``.

El email usa el backend locmem; el storage/2FA externo no se contacta. Los usuarios,
grupos y perfiles se construyen por ORM.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission, User
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.models import UserProfile, UserSecurity
from apps.common.tests.factories import (
    crear_cargo,
    crear_grupo,
    crear_unidad_organica,
    crear_usuario,
)
from apps.convenios.models import Conapres, UserEntityProfile


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FORCE_EMAIL_2FA=False,
)
class LoginTests(APITestCase):
    """``POST /api/v1/auth/token/`` — login JWT + gate de caducidad + 2FA."""

    def setUp(self):
        self.url = reverse("token_obtain_pair")
        self.user = crear_usuario(username="10000001", email="login@renads.test",
                                 password="ClaveActiva9!")
        # Password recién cambiada → no expirada.
        UserSecurity.objects.create(usuario=self.user, password_changed_at=timezone.now())
        mail.outbox = []

    def test_login_ok_devuelve_jwt(self):
        # Happy: credenciales válidas y sin 2FA → JWT completo.
        resp = self.client.post(self.url, {"username": "10000001", "password": "ClaveActiva9!"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertEqual(resp.data["token_type"], "bearer")

    def test_login_credenciales_invalidas(self):
        # Unhappy: contraseña incorrecta → 401.
        resp = self.client.post(self.url, {"username": "10000001", "password": "mala"})
        self.assertEqual(resp.status_code, 401)

    def test_login_password_expirada(self):
        # Unhappy: password nunca cambiada → 401 PASSWORD_EXPIRADO.
        u = crear_usuario(username="10000002", email="exp@renads.test", password="Clave9!xx")
        UserSecurity.objects.create(usuario=u, password_changed_at=None)
        resp = self.client.post(self.url, {"username": "10000002", "password": "Clave9!xx"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data.get("code"), "PASSWORD_EXPIRADO")

    def test_login_con_2fa_email_devuelve_session_token(self):
        # Edge: usuario con 2FA EMAIL activo → session_token diferido.
        self.user.seguridad.two_factor_enabled = True
        self.user.seguridad.two_factor_method = "EMAIL"
        self.user.seguridad.save()
        resp = self.client.post(self.url, {"username": "10000001", "password": "ClaveActiva9!"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("requires_2fa"))
        self.assertIn("session_token", resp.data)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                   FORCE_EMAIL_2FA=True)
class LoginForceEmail2faTests(APITestCase):
    """Login con ``FORCE_EMAIL_2FA=True`` (obligatorio para todos)."""

    def setUp(self):
        self.url = reverse("token_obtain_pair")
        self.user = crear_usuario(username="10000003", email="force@renads.test",
                                 password="ClaveForce9!")
        UserSecurity.objects.create(usuario=self.user, password_changed_at=timezone.now())
        mail.outbox = []

    def test_login_fuerza_otp_email(self):
        # Happy: siempre pide OTP por correo.
        resp = self.client.post(self.url, {"username": "10000003", "password": "ClaveForce9!"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["requires_2fa"])
        self.assertEqual(resp.data["method"], "EMAIL")

    def test_login_sin_correo_falla(self):
        # Unhappy: usuario sin correo con force email → 400.
        u = crear_usuario(username="10000004", email="", password="ClaveSin9!")
        UserSecurity.objects.create(usuario=u, password_changed_at=timezone.now())
        resp = self.client.post(self.url, {"username": "10000004", "password": "ClaveSin9!"})
        self.assertEqual(resp.status_code, 400)


class MeViewTests(APITestCase):
    """``GET /api/v1/auth/me/`` y cambio de contraseña propia."""

    def setUp(self):
        self.user = crear_usuario(username="10000005", email="me@renads.test",
                                 password="ClaveMe9!x")

    def test_me_requiere_autenticacion(self):
        # Unhappy: sin token → 401.
        resp = self.client.get(reverse("me"))
        self.assertEqual(resp.status_code, 401)

    def test_me_autenticado(self):
        # Happy: devuelve identidad del usuario.
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("me"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["username"], "10000005")

    def test_cambiar_password_ok(self):
        # Happy: cambia la propia contraseña y limpia el flag.
        UserSecurity.objects.create(usuario=self.user, debe_cambiar_password=True)
        self.client.force_authenticate(self.user)
        resp = self.client.post(reverse("me-cambiar-password"), {
            "password_actual": "ClaveMe9!x", "password_nueva": "ClaveNueva9!x",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ClaveNueva9!x"))
        self.assertFalse(self.user.seguridad.debe_cambiar_password)

    def test_cambiar_password_actual_incorrecta(self):
        # Unhappy: contraseña actual incorrecta → 400.
        self.client.force_authenticate(self.user)
        resp = self.client.post(reverse("me-cambiar-password"), {
            "password_actual": "mala", "password_nueva": "ClaveNueva9!x",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("password_actual", resp.data)


class UserViewSetTests(APITestCase):
    """CRUD de usuarios (solo superadministrador)."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = crear_usuario(username="super", email="super@renads.test",
                                     is_superuser=True)
        cls.unidad = crear_unidad_organica()
        cls.cargo = crear_cargo(unidad=cls.unidad)

    def setUp(self):
        self.client.force_authenticate(self.superuser)

    def test_no_super_denegado(self):
        # Unhappy: usuario normal no puede listar usuarios.
        normal = crear_usuario(username="10000010", email="n@renads.test")
        self.client.force_authenticate(normal)
        resp = self.client.get(reverse("user-list"))
        self.assertEqual(resp.status_code, 403)

    def test_crear_usuario_no_super(self):
        # Happy: crea usuario no-super con perfil y devuelve password_generada.
        resp = self.client.post(reverse("user-list"), {
            "email": "creado@renads.test", "first_name": "Cre", "last_name": "Ado Test",
            "tipo_documento": "DNI", "numero_documento": "55550001",
            "telefono": "955550001", "unidad_organica": self.unidad.pk,
            "cargo": self.cargo.pk,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["username"], "55550001")
        self.assertIsNotNone(resp.data["password_generada"])

    def test_crear_usuario_faltan_campos(self):
        # Unhappy: no-super sin campos obligatorios → 400.
        resp = self.client.post(reverse("user-list"), {"email": "x@renads.test"},
                                format="json")
        self.assertEqual(resp.status_code, 400)

    def test_destroy_desactiva(self):
        # Happy: DELETE desactiva (no borra).
        objetivo = crear_usuario(username="10000011", email="del@renads.test")
        resp = self.client.delete(reverse("user-detail", args=[objetivo.pk]))
        self.assertEqual(resp.status_code, 204)
        objetivo.refresh_from_db()
        self.assertFalse(objetivo.is_active)

    def test_set_password(self):
        # Happy: acción set-password cambia la clave.
        objetivo = crear_usuario(username="10000012", email="sp@renads.test")
        resp = self.client.post(reverse("user-set-password", args=[objetivo.pk]),
                                {"password": "ClaveReset9!x"})
        self.assertEqual(resp.status_code, 200)
        objetivo.refresh_from_db()
        self.assertTrue(objetivo.check_password("ClaveReset9!x"))

    def test_profiles_get_post_delete(self):
        # Happy: alta, listado y baja de alcance por objeto.
        objetivo = crear_usuario(username="10000013", email="pf@renads.test")
        grupo = crear_grupo("Universidad")
        entidad = Conapres.objects.create(nombre="Conapres PF")
        url = reverse("user-profiles", args=[objetivo.pk])
        # POST: otorga.
        resp = self.client.post(url, {
            "rol": grupo.id, "tipo_entidad": "conapres", "ids": [str(entidad.pk)],
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        # GET: lista solo activos.
        resp = self.client.get(url)
        self.assertEqual(len(resp.data), 1)
        perfil_id = resp.data[0]["id"]
        # DELETE: baja lógica.
        resp = self.client.delete(url + f"?profile_id={perfil_id}")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(UserEntityProfile.objects.get(pk=perfil_id).activo)

    def test_profiles_delete_sin_id(self):
        # Unhappy: DELETE sin profile_id → 400.
        objetivo = crear_usuario(username="10000014", email="pf2@renads.test")
        resp = self.client.delete(reverse("user-profiles", args=[objetivo.pk]))
        self.assertEqual(resp.status_code, 400)

    def test_profiles_post_idempotente_reactiva(self):
        # Edge: re-POST reactiva un perfil dado de baja.
        objetivo = crear_usuario(username="10000015", email="pf3@renads.test")
        grupo = crear_grupo("Universidad")
        entidad = Conapres.objects.create(nombre="Conapres Re")
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Conapres)
        perfil = UserEntityProfile.objects.create(
            usuario=objetivo, tipo_contenido=ct, id_objeto=str(entidad.pk),
            grupo=grupo, activo=False,
        )
        url = reverse("user-profiles", args=[objetivo.pk])
        resp = self.client.post(url, {
            "rol": grupo.id, "tipo_entidad": "conapres", "ids": [str(entidad.pk)],
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        perfil.refresh_from_db()
        self.assertTrue(perfil.activo)


class GroupViewSetTests(APITestCase):
    """CRUD de grupos (roles)."""

    def setUp(self):
        self.superuser = crear_usuario(username="gsuper", email="gsuper@renads.test",
                                      is_superuser=True)
        self.client.force_authenticate(self.superuser)

    def test_crear_grupo(self):
        resp = self.client.post(reverse("group-list"), {"name": "Rol X"}, format="json")
        self.assertEqual(resp.status_code, 201)

    def test_eliminar_grupo(self):
        grupo = crear_grupo("Rol Borrable")
        resp = self.client.delete(reverse("group-detail", args=[grupo.pk]))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Group.objects.filter(pk=grupo.pk).exists())


class PermissionViewSetTests(APITestCase):
    """Catálogo de permisos (solo lectura, superadministrador)."""

    def setUp(self):
        self.superuser = crear_usuario(username="psuper", email="psuper@renads.test",
                                      is_superuser=True)

    def test_listar_permisos(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.get(reverse("permission-list"))
        self.assertEqual(resp.status_code, 200)

    def test_no_super_denegado(self):
        normal = crear_usuario(username="10000020", email="pn@renads.test")
        self.client.force_authenticate(normal)
        resp = self.client.get(reverse("permission-list"))
        self.assertEqual(resp.status_code, 403)


class ContentTypeViewSetTests(APITestCase):
    """Catálogo de ContentType (solo lectura, autenticado)."""

    def test_requiere_autenticacion(self):
        resp = self.client.get(reverse("content-type-list"))
        self.assertEqual(resp.status_code, 401)

    def test_listar_autenticado(self):
        user = crear_usuario(username="10000021", email="ct@renads.test")
        self.client.force_authenticate(user)
        resp = self.client.get(reverse("content-type-list"))
        self.assertEqual(resp.status_code, 200)


class AssignableEntityTypeViewTests(APITestCase):
    """Lookup de tipos de entidad asignables (superadministrador)."""

    def test_lista_para_super(self):
        su = crear_usuario(username="aesuper", email="aesuper@renads.test", is_superuser=True)
        self.client.force_authenticate(su)
        resp = self.client.get(reverse("profile-entity-types"))
        self.assertEqual(resp.status_code, 200)
        modelos = {item["tipo_entidad"] for item in resp.data}
        self.assertIn("conapres", modelos)

    def test_no_super_denegado(self):
        normal = crear_usuario(username="10000022", email="ae@renads.test")
        self.client.force_authenticate(normal)
        resp = self.client.get(reverse("profile-entity-types"))
        self.assertEqual(resp.status_code, 403)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetViewTests(APITestCase):
    """Flujo público de recuperación de contraseña."""

    def setUp(self):
        self.user = crear_usuario(username="10000030", email="reset@renads.test",
                                 password="ClaveVieja9!x")
        mail.outbox = []

    def test_request_siempre_200(self):
        # Happy/edge: siempre 200 aunque el usuario no exista (anti-enumeración).
        resp = self.client.post(reverse("password-reset-request"), {"username": "noexiste"})
        self.assertEqual(resp.status_code, 200)

    def test_request_envia_otp(self):
        # Happy: usuario válido → envía OTP.
        resp = self.client.post(reverse("password-reset-request"), {"username": "10000030"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_request_rate_limit_429(self):
        # Unhappy: segunda solicitud inmediata → 429.
        self.client.post(reverse("password-reset-request"), {"username": "10000030"})
        resp = self.client.post(reverse("password-reset-request"), {"username": "10000030"})
        self.assertEqual(resp.status_code, 429)

    def test_confirm_ok(self):
        # Happy: OTP válido + contraseña fuerte → 200.
        sec = UserSecurity.objects.create(usuario=self.user)
        with patch("apps.common.services.secrets.randbelow", return_value=246810):
            from apps.common.services import generar_otp_email
            generar_otp_email(sec)
        resp = self.client.post(reverse("password-reset-confirm"), {
            "username": "10000030", "otp_code": "246810",
            "password_nueva": "ClaveNuevaFuerte9!",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ClaveNuevaFuerte9!"))

    def test_confirm_otp_invalido(self):
        # Unhappy: OTP inválido → 400.
        UserSecurity.objects.create(usuario=self.user)
        resp = self.client.post(reverse("password-reset-confirm"), {
            "username": "10000030", "otp_code": "000000",
            "password_nueva": "ClaveNuevaFuerte9!",
        })
        self.assertEqual(resp.status_code, 400)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                   FORCE_EMAIL_2FA=False)
class TwoFactorVerifyViewTests(APITestCase):
    """``POST /api/v1/auth/2fa/verify/`` — intercambio session_token → JWT."""

    def setUp(self):
        self.user = crear_usuario(username="10000040", email="2fa@renads.test",
                                 password="Clave2fa9!x")
        self.sec = UserSecurity.objects.create(
            usuario=self.user, two_factor_enabled=True, two_factor_method="EMAIL",
        )
        mail.outbox = []

    def test_verify_email_ok(self):
        # Happy: OTP de correo válido → devuelve JWT.
        from apps.common.services import generar_otp_email, generar_session_token
        with patch("apps.common.services.secrets.randbelow", return_value=135790):
            generar_otp_email(self.sec)
        token = generar_session_token(self.user)
        resp = self.client.post(reverse("2fa-verify"), {
            "session_token": token, "otp_code": "135790",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)

    def test_verify_otp_invalido(self):
        # Unhappy: OTP incorrecto → 401.
        from apps.common.services import generar_otp_email, generar_session_token
        with patch("apps.common.services.secrets.randbelow", return_value=111111):
            generar_otp_email(self.sec)
        token = generar_session_token(self.user)
        resp = self.client.post(reverse("2fa-verify"), {
            "session_token": token, "otp_code": "000000",
        })
        self.assertEqual(resp.status_code, 401)

    def test_verify_session_token_invalido(self):
        # Unhappy: session_token basura → AuthenticationFailed (401).
        resp = self.client.post(reverse("2fa-verify"), {
            "session_token": "basura", "otp_code": "135790",
        })
        self.assertEqual(resp.status_code, 401)


class TotpSetupViewTests(APITestCase):
    """``POST /api/v1/auth/2fa/setup/totp/`` y confirmación."""

    def setUp(self):
        self.user = crear_usuario(username="10000041", email="totp@renads.test",
                                 password="ClaveTotp9!x")
        self.client.force_authenticate(self.user)

    def test_setup_devuelve_uri_y_secret(self):
        # Happy: genera secreto y URI de aprovisionamiento.
        resp = self.client.post(reverse("2fa-setup-totp"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("otpauth_uri", resp.data)
        self.assertIn("secret", resp.data)

    def test_confirm_activa_totp(self):
        # Happy: confirma con código válido → activa TOTP.
        import pyotp
        self.client.post(reverse("2fa-setup-totp"))
        secret = UserSecurity.objects.get(usuario=self.user).totp_secret
        codigo = pyotp.TOTP(secret).now()
        resp = self.client.post(reverse("2fa-confirm-totp"), {"otp_code": codigo})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(UserSecurity.objects.get(usuario=self.user).two_factor_enabled)

    def test_confirm_sin_setup_previo(self):
        # Unhappy: confirmar sin haber hecho setup → 400.
        u = crear_usuario(username="10000042", email="totp2@renads.test")
        self.client.force_authenticate(u)
        resp = self.client.post(reverse("2fa-confirm-totp"), {"otp_code": "123456"})
        self.assertEqual(resp.status_code, 400)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TwoFactorSetupEmailAndDisableTests(APITestCase):
    """Activación 2FA por email y desactivación con doble verificación."""

    def setUp(self):
        self.user = crear_usuario(username="10000043", email="2fae@renads.test",
                                 password="Clave2fae9!x")
        self.client.force_authenticate(self.user)
        mail.outbox = []

    def test_setup_email_ok(self):
        # Happy: activa EMAIL verificando la contraseña.
        resp = self.client.post(reverse("2fa-setup-email"), {"password": "Clave2fae9!x"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(UserSecurity.objects.get(usuario=self.user).two_factor_enabled)

    def test_setup_email_password_incorrecta(self):
        # Unhappy: contraseña incorrecta → 400.
        resp = self.client.post(reverse("2fa-setup-email"), {"password": "mala"})
        self.assertEqual(resp.status_code, 400)

    def test_disable_email_genera_otp_primero(self):
        # Edge: EMAIL sin OTP en curso → primero envía OTP (200 con instrucciones).
        UserSecurity.objects.create(usuario=self.user, two_factor_enabled=True,
                                    two_factor_method="EMAIL") if not hasattr(
            self.user, "seguridad") else None
        sec = UserSecurity.objects.get(usuario=self.user)
        sec.two_factor_enabled = True
        sec.two_factor_method = "EMAIL"
        sec.otp_code = ""
        sec.save()
        # El serializer exige otp_code no vacío; en la primera llamada aún no hay
        # OTP en BD, así que el valor enviado es irrelevante: la vista genera y envía
        # uno nuevo y responde con instrucciones (200).
        resp = self.client.delete(reverse("2fa-disable"), {
            "password": "Clave2fae9!x", "otp_code": "000000",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_disable_sin_2fa_activo(self):
        # Unhappy: 2FA no activo → 400.
        resp = self.client.delete(reverse("2fa-disable"), {
            "password": "Clave2fae9!x", "otp_code": "123456",
        }, format="json")
        self.assertEqual(resp.status_code, 400)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TwoFactorResendViewTests(APITestCase):
    """``POST /api/v1/auth/2fa/resend-otp/`` — reenvío con rate-limit."""

    def setUp(self):
        self.user = crear_usuario(username="10000044", email="resend@renads.test",
                                 password="ClaveRes9!x")
        self.sec = UserSecurity.objects.create(
            usuario=self.user, two_factor_enabled=True, two_factor_method="EMAIL",
        )
        mail.outbox = []

    def test_resend_ok(self):
        # Happy: sin OTP en curso → reenvía.
        from apps.common.services import generar_session_token
        token = generar_session_token(self.user)
        resp = self.client.post(reverse("2fa-resend-otp"), {"session_token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_rate_limit(self):
        # Unhappy: OTP recién enviado → 429.
        from apps.common.services import generar_otp_email, generar_session_token
        generar_otp_email(self.sec)
        token = generar_session_token(self.user)
        resp = self.client.post(reverse("2fa-resend-otp"), {"session_token": token})
        self.assertEqual(resp.status_code, 429)

    def test_resend_metodo_no_email(self):
        # Unhappy: método distinto de EMAIL → 400.
        self.sec.two_factor_method = "TOTP"
        self.sec.save()
        from apps.common.services import generar_session_token
        token = generar_session_token(self.user)
        resp = self.client.post(reverse("2fa-resend-otp"), {"session_token": token})
        self.assertEqual(resp.status_code, 400)
