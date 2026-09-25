"""Pruebas de los permisos transversales: alcance institucional, superusuario,
miembro institucional, gate temporal de módulo y scope por objeto."""

from datetime import timedelta
from types import SimpleNamespace

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory

from apps.common import permissions
from apps.common.permissions import (
    HasEntityScope,
    IsInstitutionalMember,
    IsModuleEnabled,
    IsSuperUser,
    exigir_ambito,
)
from apps.common.tests.factories import crear_grupo, crear_usuario
from apps.convenios.models import Conapres, UserEntityProfile


class ExigirAmbitoTests(TestCase):
    """``exigir_ambito`` — escritura cross-tenant."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo = crear_grupo("Universidad")
        cls.entidad = Conapres.objects.create(nombre="Entidad A")
        cls.ct = ContentType.objects.get_for_model(Conapres)
        cls.user = crear_usuario(username="ea", grupos=["Universidad"])
        UserEntityProfile.objects.create(
            usuario=cls.user, tipo_contenido=cls.ct, id_objeto=str(cls.entidad.pk),
            grupo=cls.grupo, activo=True,
        )

    def test_superusuario_exento(self):
        # Happy: superusuario no se restringe.
        su = crear_usuario(username="su", email="su@renads.test", is_superuser=True)
        # No debe lanzar aunque la entidad no esté en su ámbito.
        exigir_ambito(su, self.ct.id, "999")

    def test_admin_renads_exento(self):
        # Happy: rol Administrador RENADS exento.
        admin = crear_usuario(username="adm", email="adm@renads.test",
                              grupos=["Administrador RENADS"])
        exigir_ambito(admin, self.ct.id, "999")

    def test_dentro_de_ambito(self):
        # Happy: usuario con perfil en la entidad no es bloqueado.
        exigir_ambito(self.user, self.ct.id, str(self.entidad.pk))

    def test_fuera_de_ambito_deniega(self):
        # Unhappy: entidad fuera del ámbito → PermissionDenied.
        with self.assertRaises(PermissionDenied):
            exigir_ambito(self.user, self.ct.id, "12345")


class IsSuperUserTests(TestCase):
    """Permiso ``IsSuperUser``."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.perm = IsSuperUser()

    def test_superusuario_permitido(self):
        req = self.factory.get("/")
        req.user = crear_usuario(username="s1", is_superuser=True)
        self.assertTrue(self.perm.has_permission(req, None))

    def test_usuario_normal_denegado(self):
        req = self.factory.get("/")
        req.user = crear_usuario(username="n1", email="n1@renads.test")
        self.assertFalse(self.perm.has_permission(req, None))

    def test_anonimo_denegado(self):
        # Edge: usuario no autenticado.
        req = self.factory.get("/")
        req.user = SimpleNamespace(is_authenticated=False, is_superuser=False)
        self.assertFalse(self.perm.has_permission(req, None))


class IsInstitutionalMemberTests(TestCase):
    """Permiso ``IsInstitutionalMember``."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo = crear_grupo("Universidad")
        cls.entidad = Conapres.objects.create(nombre="Entidad IM")
        cls.ct = ContentType.objects.get_for_model(Conapres)

    def setUp(self):
        self.factory = APIRequestFactory()
        self.perm = IsInstitutionalMember()

    def test_superusuario_pasa(self):
        req = self.factory.get("/")
        req.user = crear_usuario(username="im-su", is_superuser=True)
        self.assertTrue(self.perm.has_permission(req, None))

    def test_con_perfil_pasa(self):
        user = crear_usuario(username="im1", email="im1@renads.test", grupos=["Universidad"])
        UserEntityProfile.objects.create(
            usuario=user, tipo_contenido=self.ct, id_objeto=str(self.entidad.pk),
            grupo=self.grupo, activo=True,
        )
        req = self.factory.get("/")
        req.user = user
        self.assertTrue(self.perm.has_permission(req, None))

    def test_sin_perfil_denegado(self):
        req = self.factory.get("/")
        req.user = crear_usuario(username="im2", email="im2@renads.test")
        self.assertFalse(self.perm.has_permission(req, None))

    def test_anonimo_denegado(self):
        req = self.factory.get("/")
        req.user = SimpleNamespace(is_authenticated=False)
        self.assertFalse(self.perm.has_permission(req, None))


class IsModuleEnabledTests(TestCase):
    """Gate temporal ``IsModuleEnabled`` (RN-26)."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.perm = IsModuleEnabled()

    def _vista(self, module_ct):
        return SimpleNamespace(module_content_type=module_ct)

    def test_vista_sin_atributo_passthrough(self):
        # Edge: vista sin module_content_type → siempre permitido.
        req = self.factory.post("/")
        req.user = crear_usuario(username="me1", email="me1@renads.test")
        self.assertTrue(self.perm.has_permission(req, SimpleNamespace()))

    def test_lectura_siempre_permitida(self):
        # Happy: métodos SAFE no se gatean.
        req = self.factory.get("/")
        req.user = crear_usuario(username="me2", email="me2@renads.test")
        self.assertTrue(self.perm.has_permission(req, self._vista(("calendario", "calendaractivity"))))

    def test_no_autenticado_denegado(self):
        # Unhappy: escritura sin autenticación → False.
        req = self.factory.post("/")
        req.user = SimpleNamespace(is_authenticated=False)
        self.assertFalse(self.perm.has_permission(req, self._vista(("calendario", "calendaractivity"))))

    def test_superusuario_exento(self):
        # Happy: superusuario exento del gate.
        req = self.factory.post("/")
        req.user = crear_usuario(username="me3", is_superuser=True)
        self.assertTrue(self.perm.has_permission(req, self._vista(("calendario", "calendaractivity"))))

    def test_admin_renads_exento(self):
        # Happy: Administrador RENADS exento.
        req = self.factory.post("/")
        req.user = crear_usuario(username="me4", email="me4@renads.test",
                                grupos=["Administrador RENADS"])
        self.assertTrue(self.perm.has_permission(req, self._vista(("calendario", "calendaractivity"))))

    def test_content_type_inexistente_passthrough(self):
        # Edge: content type inexistente → pass-through (nadie lo gobierna).
        req = self.factory.post("/")
        req.user = crear_usuario(username="me5", email="me5@renads.test")
        self.assertTrue(self.perm.has_permission(req, self._vista(("noexiste", "nada"))))

    def test_modulo_gobernado_con_ventana_vigente(self):
        # Happy: módulo con ventana vigente → permitido.
        from apps.calendario.models import CalendarActivity

        ct = ContentType.objects.get_for_model(Conapres)
        act = CalendarActivity.objects.create(
            nombre="Ventana abierta", fecha_inicio=timezone.now().date() - timedelta(days=1),
            fecha_fin=None, controla_acceso=True, activo=True,
        )
        act.content_types.add(ct)
        req = self.factory.post("/")
        req.user = crear_usuario(username="me6", email="me6@renads.test")
        vista = SimpleNamespace(module_content_type=(ct.app_label, ct.model))
        self.assertTrue(self.perm.has_permission(req, vista))

    def test_modulo_gobernado_fuera_de_ventana_deniega(self):
        # Unhappy: módulo gobernado sin ventana vigente → PermissionDenied.
        from apps.calendario.models import CalendarActivity

        ct = ContentType.objects.get_for_model(Conapres)
        act = CalendarActivity.objects.create(
            nombre="Ventana pasada", fecha_inicio=timezone.now().date() - timedelta(days=10),
            fecha_fin=timezone.now().date() - timedelta(days=5),
            controla_acceso=True, activo=True,
        )
        act.content_types.add(ct)
        req = self.factory.post("/")
        req.user = crear_usuario(username="me7", email="me7@renads.test")
        vista = SimpleNamespace(module_content_type=(ct.app_label, ct.model))
        with self.assertRaises(PermissionDenied):
            self.perm.has_permission(req, vista)


class HasEntityScopeTests(TestCase):
    """Permiso a nivel de objeto ``HasEntityScope``."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo = crear_grupo("Universidad")
        cls.entidad = Conapres.objects.create(nombre="Entidad Scope")
        cls.ct = ContentType.objects.get_for_model(Conapres)
        cls.user = crear_usuario(username="hs", email="hs@renads.test", grupos=["Universidad"])
        UserEntityProfile.objects.create(
            usuario=cls.user, tipo_contenido=cls.ct, id_objeto=str(cls.entidad.pk),
            grupo=cls.grupo, activo=True,
        )

    def setUp(self):
        self.factory = APIRequestFactory()
        self.perm = HasEntityScope()

    def test_superusuario_pasa(self):
        req = self.factory.get("/")
        req.user = crear_usuario(username="hs-su", is_superuser=True)
        self.assertTrue(self.perm.has_object_permission(req, SimpleNamespace(), object()))

    def test_vista_sin_get_entity_reference_pasa(self):
        # Edge: vista sin get_entity_reference → sin restricción.
        req = self.factory.get("/")
        req.user = self.user
        self.assertTrue(self.perm.has_object_permission(req, SimpleNamespace(), object()))

    def test_referencia_none_pasa(self):
        # Edge: get_entity_reference devuelve None → sin restricción.
        req = self.factory.get("/")
        req.user = self.user
        vista = SimpleNamespace(get_entity_reference=lambda obj: None)
        self.assertTrue(self.perm.has_object_permission(req, vista, object()))

    def test_objeto_en_ambito(self):
        # Happy: objeto de la entidad del usuario → permitido.
        req = self.factory.get("/")
        req.user = self.user
        vista = SimpleNamespace(
            get_entity_reference=lambda obj: (self.ct.id, str(self.entidad.pk))
        )
        self.assertTrue(self.perm.has_object_permission(req, vista, object()))

    def test_objeto_fuera_de_ambito(self):
        # Unhappy: objeto de otra entidad → denegado.
        req = self.factory.get("/")
        req.user = self.user
        vista = SimpleNamespace(get_entity_reference=lambda obj: (self.ct.id, "99999"))
        self.assertFalse(self.perm.has_object_permission(req, vista, object()))
