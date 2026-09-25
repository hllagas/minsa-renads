"""Pruebas de permisos del módulo Internados (IsUniversityOrReadOnly, InternshipScope)."""

from types import SimpleNamespace

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.internados.permissions import InternshipScope, IsUniversityOrReadOnly
from apps.internados.tests import factories as f


class IsUniversityOrReadOnlyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rf = APIRequestFactory()

    def _perm(self, user, method="POST", action=None):
        request = getattr(self.rf, method.lower())("/")
        request.user = user
        view = SimpleNamespace(action=action)
        return IsUniversityOrReadOnly().has_permission(request, view)

    def test_no_autenticado_denegado(self):
        request = self.rf.get("/")
        request.user = SimpleNamespace(is_authenticated=False)
        self.assertFalse(IsUniversityOrReadOnly().has_permission(request, SimpleNamespace()))

    def test_lectura_libre_para_autenticado(self):
        user = f.crear_usuario("perm_read")
        self.assertTrue(self._perm(user, method="GET"))

    def test_escritura_universidad_permitida(self):
        user = f.crear_usuario("perm_uni", grupos=["Universidad"])
        self.assertTrue(self._perm(user, method="POST"))

    def test_escritura_denegada_a_rol_ajeno(self):
        user = f.crear_usuario("perm_otro", grupos=["CONAPRES"])
        self.assertFalse(self._perm(user, method="POST"))

    def test_interno_puede_annex_upload(self):
        # RN-22: el interno solo puede las acciones de adjunto.
        user = f.crear_usuario("perm_int", grupos=["Interno"])
        self.assertTrue(self._perm(user, method="POST", action="annex_upload"))

    def test_interno_no_puede_crear(self):
        user = f.crear_usuario("perm_int2", grupos=["Interno"])
        self.assertFalse(self._perm(user, method="POST", action="create"))


class InternshipScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("scope_admin", is_superuser=True)
        cls.uni = f.crear_universidad("USC", "SC")
        cls.internado = f.crear_internado(
            creado_por=cls.admin,
            estudiante=f.crear_estudiante(creado_por=cls.admin, universidad=cls.uni,
                                          numero_documento="60000001"),
        )
        cls.rf = APIRequestFactory()

    def _check(self, user, obj):
        request = self.rf.get("/")
        request.user = user
        return InternshipScope().has_object_permission(request, SimpleNamespace(), obj)

    def test_superusuario_pasa(self):
        self.assertTrue(self._check(self.admin, self.internado))

    def test_sin_perfil_denegado(self):
        user = f.crear_usuario("scope_nada")
        self.assertFalse(self._check(user, self.internado))

    def test_universidad_en_ambito_permitido(self):
        user = f.crear_usuario("scope_uni")
        f.dar_ambito(user, self.uni, "Universidad")
        self.assertTrue(self._check(user, self.internado))

    def test_resuelve_internado_desde_rotacion(self):
        # InternshipScope resuelve el internado si el obj es una Rotation.
        rot = SimpleNamespace(interno=self.internado)
        user = f.crear_usuario("scope_rot")
        f.dar_ambito(user, self.uni, "Universidad")
        # No es Internship → toma obj.interno.
        request = self.rf.get("/")
        request.user = user
        self.assertTrue(InternshipScope().has_object_permission(request, SimpleNamespace(), rot))
