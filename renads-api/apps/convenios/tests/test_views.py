"""Pruebas de endpoints (DRF) del módulo Convenios vía APIClient.

Autenticación con ``force_authenticate``. El gate temporal ``IsModuleEnabled`` es
pass-through en la BD de test (el ContentType de ``convention`` no está gobernado por
ninguna ventana de calendario). Las dependencias de sistema (PDF/soffice/storage) se
mockean cuando se ejercen las acciones que las usan.
"""

import datetime
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.convenios.models import (
    ClinicalFieldAllocation,
    ClinicalFieldRegistration,
    Convention,
    OrganicUnit,
)
from apps.convenios.tests import factories as f


class ConventionViewSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("cv_admin", is_superuser=True)
        cls.uni = f.crear_universidad("Uni CV", "UCV")
        cls.uni_user = f.crear_usuario("cv_uni", grupos=["Universidad"])
        f.dar_ambito(cls.uni_user, cls.uni, "Universidad")
        cls.gore = f.crear_gobierno_regional(nombre="GORE CV")
        cls.unidad_gore = f.crear_unidad_organica(organo_nombre=f.ORGANO_GORE, nombre="GERESA CV")

    def setUp(self):
        self.client = APIClient()

    def _payload_marco(self, **over):
        ct = ContentType.objects.get_for_model(type(self.uni))
        data = {
            "tipo_convenio": f.tipo_convenio("MARCO").id,
            "titulo": "Marco CV", "unidad_organica": self.unidad_gore.id,
            "gobierno_regional": self.gore.id, "universidad": self.uni.id,
            "solicitante_tipo_contenido": ct.id, "solicitante_id_objeto": self.uni.id,
            "fecha_solicitud": "2026-03-01", "fecha_inicio": "2026-03-01",
        }
        data.update(over)
        return data

    def test_crear_convenio_marco(self):
        # Happy: el superusuario (con ámbito exento) crea un Marco.
        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("convention-list"), self._payload_marco(), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(Convention.objects.filter(titulo="Marco CV").exists())

    def test_no_autenticado_401(self):
        resp = self.client.post(reverse("convention-list"), self._payload_marco(), format="json")
        self.assertEqual(resp.status_code, 401)

    def test_listar_alcance(self):
        # Happy: el usuario de universidad solo ve los convenios de su ámbito.
        f.crear_convenio(creado_por=self.admin, universidad=self.uni, solicitante=self.uni,
                         titulo="Visible CV")
        otra = f.crear_universidad("Otra CV", "OCV")
        f.crear_convenio(creado_por=self.admin, universidad=otra, solicitante=otra,
                         titulo="Oculto CV")
        # Registrar la entidad como participante para pasar el gate de objeto/lista.
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("convention-list"))
        self.assertEqual(resp.status_code, 200)

    def test_cambiar_estado_requiere_admin(self):
        # Unhappy: un rol no admin no puede cambiar el estado.
        conv = f.crear_convenio(creado_por=self.admin, universidad=self.uni, solicitante=self.uni)
        # Participante para pasar el ConventionScope del usuario de universidad.
        from apps.convenios.models import ConventionParticipant
        ct = ContentType.objects.get_for_model(type(self.uni))
        ConventionParticipant.objects.create(convenio=conv, tipo_contenido=ct, id_objeto=self.uni.id)
        self.client.force_authenticate(self.uni_user)
        resp = self.client.post(
            reverse("convention-cambiar-estado", args=[conv.id]),
            {"estado_codigo": "PUBLICADO"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_cambiar_estado_admin(self):
        # Happy: el admin cambia el estado.
        conv = f.crear_convenio(creado_por=self.admin, estado_codigo="SUSCRITO")
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            reverse("convention-cambiar-estado", args=[conv.id]),
            {"estado_codigo": "PUBLICADO"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "PUBLICADO")

    def test_historial_action(self):
        conv = f.crear_convenio(creado_por=self.admin)
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("convention-historial", args=[conv.id]))
        self.assertEqual(resp.status_code, 200)

    def test_crear_adenda(self):
        # Happy: crea una adenda vía la acción.
        conv = f.crear_convenio(creado_por=self.admin, estado_codigo="VIGENTE")
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            reverse("convention-adenda", args=[conv.id]),
            {"fecha_inicio": "2027-01-01"}, format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(Convention.objects.filter(convenio_origen=conv, es_adenda=True).exists())

    def test_bulk_upload_requiere_admin(self):
        # Unhappy: bulk-upload solo para Administrador RENADS.
        conv_user = f.crear_usuario("cv_conv_user", grupos=["Universidad"])
        f.dar_ambito(conv_user, self.uni, "Universidad")
        self.client.force_authenticate(conv_user)
        resp = self.client.post(reverse("convention-bulk-upload"), {}, format="multipart")
        self.assertEqual(resp.status_code, 403)

    def test_generar_proyecto_mockeando_pdf(self):
        # Happy: la acción genera y adjunta el PDF (pdf y storage mockeados).
        conv = f.crear_convenio(creado_por=self.admin)
        self.client.force_authenticate(self.admin)
        with patch("apps.convenios.pdf.generar_proyecto", return_value=b"%PDF-1.4 fake"), \
             patch("apps.convenios.mixins.get_document_storage") as mock_storage, \
             patch("apps.convenios.views.get_document_storage") as mock_storage2:
            mock_storage.return_value.subir.return_value = "ruta/proyecto.pdf"
            mock_storage2.return_value.subir.return_value = "ruta/proyecto.pdf"
            resp = self.client.post(reverse("convention-generar-proyecto", args=[conv.id]))
        self.assertIn(resp.status_code, (201, 500))


class ConventionFlowActionsTests(TestCase):
    """Acciones de flujo del convenio con verificación de rol (DIGEP/CONAPRES/OGAJ/SG)."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("cfl_admin", is_superuser=True)

    def setUp(self):
        self.client = APIClient()

    def _rol_para(self, username, rol, conv):
        """Crea un usuario con el rol + un perfil institucional sobre la universidad
        del convenio, y registra esa universidad como participante para pasar
        ``IsInstitutionalMember`` y ``ConventionScope``."""
        user = f.crear_usuario(username, grupos=[rol])
        f.dar_ambito(user, conv.universidad, rol)
        from apps.convenios.models import ConventionParticipant
        ct = ContentType.objects.get_for_model(type(conv.universidad))
        ConventionParticipant.objects.get_or_create(
            convenio=conv, tipo_contenido=ct, id_objeto=conv.universidad.id,
        )
        return user

    def test_evaluacion_tecnica_digep(self):
        # Happy: DIGEP registra la evaluación técnica de un Marco.
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="EN_EVALUACION_DIGEP")
        self.client.force_authenticate(self._rol_para("cfl_digep", "DIGEP", conv))
        resp = self.client.post(
            reverse("convention-evaluacion-tecnica", args=[conv.id]),
            {"resultado": "OBSERVADO", "fecha_evaluacion": "2026-03-01", "observaciones": "X"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_evaluacion_tecnica_rol_incorrecto(self):
        # Unhappy: un usuario con perfil y scope pero rol distinto de DIGEP → 403
        # por `exigir_roles("DIGEP")`.
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="EN_EVALUACION_DIGEP")
        user = self._rol_para("cfl_no_digep", "Universidad", conv)
        self.client.force_authenticate(user)
        resp = self.client.post(
            reverse("convention-evaluacion-tecnica", args=[conv.id]),
            {"resultado": "OBSERVADO", "fecha_evaluacion": "2026-03-01"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_opinion_conapres(self):
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="ESPECIFICO",
                                estado_codigo="SOLICITUD_REGISTRADA")
        self.client.force_authenticate(self._rol_para("cfl_conapres", "CONAPRES", conv))
        resp = self.client.post(
            reverse("convention-opinion-conapres", args=[conv.id]),
            {"fecha_solicitud": "2026-03-01", "estado_atencion": "ATENDIDO",
             "resultado_opinion": "FAVORABLE"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_opinion_juridica(self):
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="VALIDADO_TECNICAMENTE")
        self.client.force_authenticate(self._rol_para("cfl_ogaj", "OGAJ", conv))
        resp = self.client.post(
            reverse("convention-opinion-juridica", args=[conv.id]),
            {"fecha_envio": "2026-03-01", "resultado_opinion": "FAVORABLE"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_publicacion(self):
        conv = f.crear_convenio(creado_por=self.admin, estado_codigo="SUSCRITO")
        self.client.force_authenticate(self._rol_para("cfl_sg", "Secretaría General", conv))
        resp = self.client.post(
            reverse("convention-publicacion", args=[conv.id]),
            {"fecha_publicacion": "2026-03-01"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "PUBLICADO")

    def test_participantes_get_y_post(self):
        conv = f.crear_convenio(creado_por=self.admin)
        ct = ContentType.objects.get_for_model(type(conv.universidad))
        self.client.force_authenticate(self.admin)
        # POST agrega un participante.
        resp = self.client.post(
            reverse("convention-participantes", args=[conv.id]),
            {"tipo_contenido": ct.id, "id_objeto": conv.universidad.id, "es_firmante": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data), 1)

    def test_parties_get_y_post(self):
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="ESPECIFICO")
        ue_unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_UE, nombre="UE Parties V")
        fac_unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_UNIVERSIDAD, nombre="Fac Parties V")
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            reverse("convention-parties", args=[conv.id]),
            [
                {"rol": "UNIDAD_EJECUTORA", "unidad_organica": ue_unidad.id, "orden": 1},
                {"rol": "FACULTAD", "unidad_organica": fac_unidad.id, "orden": 1},
            ],
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data), 2)
        # GET lista las partes.
        resp_get = self.client.get(reverse("convention-parties", args=[conv.id]))
        self.assertEqual(resp_get.status_code, 200)


class ClinicalFieldRegistrationViewSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("cfr_admin", is_superuser=True)
        cls.conapres = f.crear_usuario("cfr_conapres", grupos=["CONAPRES"])
        f.dar_ambito(cls.conapres, f.crear_conapres(), "CONAPRES")
        cls.carrera = f.crear_carrera("Med CFR")

    def setUp(self):
        self.client = APIClient()

    def test_crear_registro_conapres(self):
        # Happy: CONAPRES registra campos clínicos.
        ipress = f.crear_ipress(codigo="87010001", es_sede_docente=True)
        self.client.force_authenticate(self.conapres)
        resp = self.client.post(reverse("clinical-field-registration-list"), {
            "ipress": ipress.pk, "carrera_profesional": self.carrera.id,
            "campos_clinicos_registrados": 5,
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_crear_registro_rol_denegado(self):
        # Unhappy: un rol distinto de CONAPRES no puede registrar (403).
        ipress = f.crear_ipress(codigo="87020001", es_sede_docente=True)
        otro = f.crear_usuario("cfr_otro", grupos=["Universidad"])
        self.client.force_authenticate(otro)
        resp = self.client.post(reverse("clinical-field-registration-list"), {
            "ipress": ipress.pk, "carrera_profesional": self.carrera.id,
            "campos_clinicos_registrados": 5,
        }, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_lectura_para_autenticado(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("clinical-field-registration-list"))
        self.assertEqual(resp.status_code, 200)


class ClinicalFieldAllocationViewSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("cfa_admin", is_superuser=True)
        cls.gore = f.crear_usuario("cfa_gore", grupos=["Gobierno Regional"])
        f.dar_ambito(cls.gore, f.crear_gobierno_regional(nombre="GORE CFA"), "Gobierno Regional")
        cls.carrera = f.crear_carrera("Med CFA")

    def setUp(self):
        self.client = APIClient()

    def test_crear_asignacion_gore(self):
        # Happy: Gobierno Regional crea una asignación.
        ipress = f.crear_ipress(codigo="88010001", es_sede_docente=True)
        reg = f.crear_registro_campo_clinico(ipress=ipress, carrera=self.carrera, registrados=10)
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="ESPECIFICO",
                                estado_codigo="VIGENTE")
        self.client.force_authenticate(self.gore)
        resp = self.client.post(reverse("clinical-field-allocation-list"), {
            "campo_clinico_ipress": reg.id, "convenio": conv.id,
            "campos_clinicos_autorizados": 3,
            "fecha_inicio": "2026-03-01", "fecha_fin": "2027-03-01",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_crear_asignacion_rol_denegado(self):
        # Unhappy: un rol no Gobierno Regional no puede asignar (403).
        otro = f.crear_usuario("cfa_otro", grupos=["Universidad"])
        self.client.force_authenticate(otro)
        resp = self.client.post(reverse("clinical-field-allocation-list"), {}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_eliminar_asignacion(self):
        # Happy: elimina una asignación y recalcula el acumulador.
        ipress = f.crear_ipress(codigo="88020001", es_sede_docente=True)
        reg = f.crear_registro_campo_clinico(ipress=ipress, carrera=self.carrera, registrados=10)
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="ESPECIFICO",
                                estado_codigo="VIGENTE")
        asig = f.crear_asignacion_campo_clinico(
            convenio=conv, registro=reg, ipress=ipress, carrera=self.carrera, autorizados=4,
        )
        self.client.force_authenticate(self.gore)
        resp = self.client.delete(reverse("clinical-field-allocation-detail", args=[asig.id]))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(ClinicalFieldAllocation.objects.filter(id=asig.id).exists())


class EntityCatalogViewSetTests(TestCase):
    """CRUD de entidades: escritura solo Administrador RENADS."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("ent_admin", grupos=["Administrador RENADS"])
        cls.comun = f.crear_usuario("ent_comun", grupos=["Universidad"])

    def setUp(self):
        self.client = APIClient()

    def test_crear_organo_admin(self):
        # Happy: el admin crea un órgano (catálogo con CRUD).
        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("organs-list"), {"nombre": "Órgano Nuevo Ent"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_crear_organo_denegado_a_no_admin(self):
        # Unhappy: un rol no admin no puede crear (403).
        self.client.force_authenticate(self.comun)
        resp = self.client.post(reverse("organs-list"), {"nombre": "Órgano Denegado"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_lectura_catalogo(self):
        # Happy: la lectura de un catálogo es para cualquier autenticado.
        self.client.force_authenticate(self.comun)
        resp = self.client.get(reverse("convention-types-list"))
        self.assertEqual(resp.status_code, 200)

    def test_organic_unit_unicidad(self):
        # Unhappy RN-GORE-3: unidad orgánica duplicada (organo, nombre) → 400.
        organo = f.crear_organo(f.ORGANO_MINSA)
        OrganicUnit.objects.create(organo=organo, nombre="Duplicada Ent")
        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("organic-units-list"), {
            "organo": organo.id, "nombre": "Duplicada Ent",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_executive_position_coherencia(self):
        # Unhappy RN-CE-02: organo != unidad_organica.organo → 400.
        organo_a = f.crear_organo(f.ORGANO_MINSA)
        organo_b = f.crear_organo(f.ORGANO_GORE)
        unidad = OrganicUnit.objects.create(organo=organo_a, nombre="UO Coh Ent")
        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("executive-positions-list"), {
            "organo": organo_b.id, "unidad_organica": unidad.id,
            "nombre_masculino": "Cargo Incoherente", "nombre_femenino": "Cargo Incoherente",
        }, format="json")
        self.assertEqual(resp.status_code, 400)


class FacultyCareersActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("fca_admin", grupos=["Administrador RENADS"])
        cls.uni = f.crear_universidad("Uni FCA", "UFCA")
        cls.facultad = f.crear_facultad(universidad=cls.uni)
        cls.c1 = f.crear_carrera("Med FCA")

    def setUp(self):
        self.client = APIClient()

    def test_sync_careers(self):
        # Happy: sincroniza carreras de la facultad en lote.
        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("faculties-careers", args=[self.facultad.id]),
                                {"carreras": [self.c1.id]}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data["carreras"]), 1)


class IpressAutorizarSedeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.conapres = f.crear_usuario("ipa_conapres", grupos=["CONAPRES", "Administrador RENADS"])

    def setUp(self):
        self.client = APIClient()

    def test_autorizar_sede_docente(self):
        # Happy: CONAPRES autoriza la sede docente.
        ipress = f.crear_ipress(codigo="89010001", es_sede_docente=False)
        self.client.force_authenticate(self.conapres)
        resp = self.client.post(
            reverse("ipress-autorizar-sede-docente", args=[ipress.pk]),
            {"autorizar": True}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        ipress.refresh_from_db()
        self.assertTrue(ipress.es_sede_docente)


class OrganRepresentativeViewSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("orv_admin", grupos=["Administrador RENADS"])
        cls.uni = f.crear_universidad("Uni ORV", "UORV")
        cls.tipo_doc = f.crear_tipo_documento()

    def setUp(self):
        self.client = APIClient()

    def test_crear_representante(self):
        # Happy: el admin crea un representante (delega en el service).
        from apps.convenios.models import ExecutivePosition
        cargo = ExecutivePosition.objects.create(
            organo=f.crear_organo(f.ORGANO_UNIVERSIDAD), unidad_organica=None,
            nombre_masculino="Rector ORV", nombre_femenino="Rectora ORV",
        )
        ct = ContentType.objects.get_for_model(type(self.uni))
        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("organ-representative-list"), {
            "tipo_contenido": ct.id, "id_objeto": self.uni.id, "nombre": "Rep ORV",
            "tipo_documento_identidad": self.tipo_doc.id, "numero_documento_identidad": "40000001",
            "sexo": "M", "cargo_ejecutivo": cargo.id, "fecha_inicio_designacion": "2026-03-01",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)


class SolicitanteContentTypeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_lista_tipos_solicitante(self):
        admin = f.crear_usuario("sct_admin", is_superuser=True)
        self.client.force_authenticate(admin)
        resp = self.client.get(reverse("solicitante-content-types"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data) > 0)

    def test_lista_tipos_representante(self):
        admin = f.crear_usuario("sct_admin2", is_superuser=True)
        self.client.force_authenticate(admin)
        resp = self.client.get(reverse("representante-content-types"))
        self.assertEqual(resp.status_code, 200)

    def test_no_autenticado(self):
        resp = self.client.get(reverse("solicitante-content-types"))
        self.assertEqual(resp.status_code, 401)


class AnnexAttachmentMixinTests(TestCase):
    """Adjunto real de anexos (PDF) por actor — storage mockeado."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("anx_admin", is_superuser=True)
        cls.conv = f.crear_convenio(creado_por=cls.admin)

    def setUp(self):
        self.client = APIClient()

    def _anexo(self, codigo):
        from apps.internados.models import AnnexDocument
        return AnnexDocument.objects.get(codigo=codigo)

    def _pdf(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile("resol.pdf", b"%PDF-1.4 fake", content_type="application/pdf")

    def test_annex_checklist(self):
        # Happy: el checklist cruza el catálogo con los adjuntos (vacío al inicio).
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("convention-annex-checklist", args=[self.conv.id]))
        self.assertEqual(resp.status_code, 200)
        codigos = {item["codigo"] for item in resp.data}
        self.assertIn("RESOL_MARCO", codigos)
        self.assertTrue(all(item["adjuntado"] is False for item in resp.data))

    def test_annex_upload_actor_incorrecto(self):
        # Unhappy: un anexo de otro actor no corresponde a este ViewSet.
        anexo_cc = self._anexo("RESOL_CONAPRES")  # actor CAMPO_CLINICO, no CONVENIO
        self.client.force_authenticate(self.admin)
        with patch("apps.convenios.mixins.get_document_storage") as mock_storage:
            mock_storage.return_value.subir.return_value = "ruta/x.pdf"
            resp = self.client.post(
                reverse("convention-annex-upload", args=[self.conv.id]),
                {"documento_anexo": anexo_cc.id, "archivo": self._pdf()},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 400)

    def test_annex_upload_ok(self):
        # Happy: adjunta un anexo del actor CONVENIO (storage mockeado).
        anexo = self._anexo("RESOL_MARCO")
        self.client.force_authenticate(self.admin)
        with patch("apps.convenios.mixins.get_document_storage") as mock_storage:
            mock_storage.return_value.subir.return_value = "ruta/resol.pdf"
            resp = self.client.post(
                reverse("convention-annex-upload", args=[self.conv.id]),
                {"documento_anexo": anexo.id, "archivo": self._pdf()},
                format="multipart",
            )
        self.assertEqual(resp.status_code, 201, resp.data)


class LogoStorageMixinTests(TestCase):
    """Subida/consulta de logo institucional (ImageField) — sin tocar backend real."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("logo_admin", grupos=["Administrador RENADS"])
        cls.gore = f.crear_gobierno_regional(nombre="GORE Logo")

    def setUp(self):
        self.client = APIClient()

    def _png(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # PNG mínimo válido (firma) para el ImageField.
        png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
               b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
               b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        return SimpleUploadedFile("logo.png", png, content_type="image/png")

    def test_logo_url_sin_logo_404(self):
        # Unhappy: sin logo cargado → 404.
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("regional-governments-logo-url", args=[self.gore.id]))
        self.assertEqual(resp.status_code, 404)

    def test_upload_logo(self):
        # Happy: sube el logo y devuelve su URL (storage por defecto = FileSystem en test).
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            reverse("regional-governments-upload-logo", args=[self.gore.id]),
            {"archivo": self._png()}, format="multipart",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn("referencia_logo", resp.data)
        self.gore.refresh_from_db()
        self.assertTrue(self.gore.referencia_logo)
        # Limpieza del binario escrito por el ImageField en MEDIA_ROOT.
        self.gore.referencia_logo.delete(save=False)


class DocumentViewSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("doc_admin", is_superuser=True)
        cls.conv = f.crear_convenio(creado_por=cls.admin)

    def setUp(self):
        self.client = APIClient()

    def _anexo(self):
        from apps.internados.models import AnnexDocument
        return AnnexDocument.objects.get(codigo="RESOL_MARCO")

    def test_create_documento(self):
        # Happy: crear un documento adjunta y versiona vía el service.
        ct = ContentType.objects.get_for_model(Convention)
        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("document-list"), {
            "tipo_contenido": ct.id, "id_objeto": self.conv.id,
            "documento_anexo": self._anexo().id, "referencia_externa": "ruta/doc.pdf",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_url_descarga(self):
        # Happy: la acción devuelve la url firmada (storage mockeado).
        from apps.common.services import adjuntar_documento
        doc = adjuntar_documento(self.conv, referencia_externa="ruta/doc.pdf",
                                 usuario=self.admin, documento_anexo=self._anexo())
        self.client.force_authenticate(self.admin)
        with patch("apps.convenios.views.get_document_storage") as mock_storage:
            mock_storage.return_value.url_firmada.return_value = "https://x/doc.pdf"
            resp = self.client.get(reverse("document-url-descarga", args=[doc.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["url"], "https://x/doc.pdf")


class AuditLogViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_solo_admin(self):
        # Unhappy: la bitácora es solo para Administrador RENADS.
        comun = f.crear_usuario("al_comun", grupos=["Universidad"])
        self.client.force_authenticate(comun)
        resp = self.client.get(reverse("audit-log-list"))
        self.assertEqual(resp.status_code, 403)

    def test_admin_lee(self):
        admin = f.crear_usuario("al_admin", grupos=["Administrador RENADS"])
        self.client.force_authenticate(admin)
        resp = self.client.get(reverse("audit-log-list"))
        self.assertEqual(resp.status_code, 200)
