"""Pruebas de los permisos del módulo Convenios (roles y alcance institucional)."""

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.convenios.models import ConventionParticipant
from apps.convenios.permissions import (
    ConventionScope,
    IsAdminRole,
    IsAdminRoleOrReadOnly,
    IsConapresOrReadOnly,
    IsRegionalOrganOrReadOnly,
    exigir_roles,
    _es_admin,
    _en_grupo,
)
from apps.convenios.tests import factories as f
from django.contrib.contenttypes.models import ContentType


class _Req:
    """Petición mínima con user y method para los permisos a nivel de vista."""

    def __init__(self, user, method="GET"):
        self.user = user
        self.method = method


class HelperTests(TestCase):
    def test_es_admin_superusuario_y_grupo(self):
        # Happy: superusuario y miembro del grupo Administrador RENADS son admin.
        self.assertTrue(_es_admin(f.crear_usuario("h_super", is_superuser=True)))
        self.assertTrue(_es_admin(f.crear_usuario("h_admin", grupos=["Administrador RENADS"])))

    def test_es_admin_falso_para_otro_rol(self):
        # Unhappy: un usuario común no es admin.
        self.assertFalse(_es_admin(f.crear_usuario("h_comun")))

    def test_en_grupo(self):
        u = f.crear_usuario("h_conapres", grupos=["CONAPRES"])
        self.assertTrue(_en_grupo(u, "CONAPRES"))
        self.assertFalse(_en_grupo(u, "Gobierno Regional"))


class RolePermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("p_admin", grupos=["Administrador RENADS"])
        cls.conapres = f.crear_usuario("p_conapres", grupos=["CONAPRES"])
        cls.gore = f.crear_usuario("p_gore", grupos=["Gobierno Regional"])
        cls.comun = f.crear_usuario("p_comun")

    def test_is_admin_role(self):
        perm = IsAdminRole()
        self.assertTrue(perm.has_permission(_Req(self.admin, "POST"), None))
        self.assertFalse(perm.has_permission(_Req(self.comun, "POST"), None))

    def test_is_admin_role_or_read_only(self):
        perm = IsAdminRoleOrReadOnly()
        # Lectura permitida a cualquier autenticado.
        self.assertTrue(perm.has_permission(_Req(self.comun, "GET"), None))
        # Escritura solo admin.
        self.assertFalse(perm.has_permission(_Req(self.comun, "POST"), None))
        self.assertTrue(perm.has_permission(_Req(self.admin, "POST"), None))

    def test_is_conapres_or_read_only(self):
        perm = IsConapresOrReadOnly()
        self.assertTrue(perm.has_permission(_Req(self.comun, "GET"), None))
        self.assertFalse(perm.has_permission(_Req(self.comun, "POST"), None))
        self.assertTrue(perm.has_permission(_Req(self.conapres, "POST"), None))

    def test_is_regional_organ_or_read_only(self):
        perm = IsRegionalOrganOrReadOnly()
        self.assertTrue(perm.has_permission(_Req(self.comun, "GET"), None))
        self.assertFalse(perm.has_permission(_Req(self.comun, "POST"), None))
        self.assertTrue(perm.has_permission(_Req(self.gore, "POST"), None))

    def test_read_only_perms_deniegan_no_autenticado(self):
        # Unhappy: usuario no autenticado no pasa (ni siquiera lectura).
        class Anon:
            is_authenticated = False
            is_superuser = False
        perm = IsConapresOrReadOnly()
        self.assertFalse(perm.has_permission(_Req(Anon(), "GET"), None))


class ExigirRolesTests(TestCase):
    def setUp(self):
        self.rf = APIRequestFactory()

    def _request(self, user):
        request = self.rf.post("/x/")
        force_authenticate(request, user=user)
        request.user = user
        return request

    def test_superusuario_pasa(self):
        req = self._request(f.crear_usuario("er_super", is_superuser=True))
        exigir_roles(req, "DIGEP")  # no lanza

    def test_rol_correcto_pasa(self):
        req = self._request(f.crear_usuario("er_digep", grupos=["DIGEP"]))
        exigir_roles(req, "DIGEP", "CONAPRES")  # no lanza

    def test_rol_incorrecto_lanza(self):
        req = self._request(f.crear_usuario("er_otro", grupos=["Universidad"]))
        with self.assertRaises(PermissionDenied):
            exigir_roles(req, "DIGEP")


class ConventionScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("cs_admin", is_superuser=True)
        cls.uni = f.crear_universidad("Uni Scope", "USC")
        cls.otra = f.crear_universidad("Otra Scope", "OSC")
        cls.usuario = f.crear_usuario("cs_uni", grupos=["Universidad"])
        f.dar_ambito(cls.usuario, cls.uni, "Universidad")
        cls.conv_propio = f.crear_convenio(creado_por=cls.admin, universidad=cls.uni,
                                           solicitante=cls.uni)
        cls.conv_ajeno = f.crear_convenio(creado_por=cls.admin, universidad=cls.otra,
                                          solicitante=cls.otra)

    def test_superusuario_pasa_siempre(self):
        perm = ConventionScope()
        self.assertTrue(perm.has_object_permission(_Req(self.admin), None, self.conv_ajeno))

    def test_solicitante_en_ambito_via_participante(self):
        # Aunque no sea solicitante, si su entidad participa accede al objeto.
        ct = ContentType.objects.get_for_model(type(self.uni))
        ConventionParticipant.objects.create(
            convenio=self.conv_propio, tipo_contenido=ct, id_objeto=self.uni.id,
        )
        perm = ConventionScope()
        self.assertTrue(
            perm.has_object_permission(_Req(self.usuario), None, self.conv_propio)
        )

    def test_solicitante_puro_pasa(self):
        # El solicitante puro (sin fila de participante) pasa el gate de objeto,
        # coherente con `convenios_visibles`: la comparación normaliza el id a str
        # (`solicitante_id_objeto` es int y `entidades_del_usuario` devuelve str).
        perm = ConventionScope()
        self.assertTrue(
            perm.has_object_permission(_Req(self.usuario), None, self.conv_propio)
        )

    def test_fuera_de_ambito_deniega(self):
        # Unhappy: convenio de otra universidad, fuera del ámbito.
        perm = ConventionScope()
        self.assertFalse(
            perm.has_object_permission(_Req(self.usuario), None, self.conv_ajeno)
        )

    def test_participante_pasa(self):
        # Edge: aunque no sea solicitante, si su entidad participa accede.
        ct = ContentType.objects.get_for_model(type(self.uni))
        ConventionParticipant.objects.create(
            convenio=self.conv_ajeno, tipo_contenido=ct, id_objeto=self.uni.id,
        )
        perm = ConventionScope()
        self.assertTrue(
            perm.has_object_permission(_Req(self.usuario), None, self.conv_ajeno)
        )

    def test_sin_perfiles_deniega(self):
        sin = f.crear_usuario("cs_sin")
        perm = ConventionScope()
        self.assertFalse(
            perm.has_object_permission(_Req(sin), None, self.conv_propio)
        )
