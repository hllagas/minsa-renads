"""Pruebas de endpoints (DRF) del módulo Internados vía APIClient.

Autenticación con ``force_authenticate``. El gate temporal ``IsModuleEnabled`` es
pass-through en el DB de test (el ContentType de ``internship`` no está gobernado por
ninguna ventana de calendario), por lo que la escritura de universidad no se bloquea.
"""

import datetime
import io

import openpyxl
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.internados.models import Internship, Student, Tutor
from apps.internados.tests import factories as f


class StudentViewSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uni = f.crear_universidad()
        cls.carrera = f.crear_carrera()
        cls.periodo = f.crear_periodo()
        cls.dni = f.crear_tipo_documento()
        cls.admin = f.crear_usuario("v_admin", is_superuser=True)
        cls.uni_user = f.crear_usuario("v_uni", grupos=["Universidad"])
        f.dar_ambito(cls.uni_user, cls.uni, "Universidad")

    def setUp(self):
        self.client = APIClient()

    def _payload(self, **over):
        data = {
            "tipo_documento_identidad": self.dni.id, "numero_documento": "70000010",
            "nombres": "JUAN", "apellido_paterno": "PEREZ",
            "universidad": self.uni.id, "carrera_profesional": self.carrera.id,
            "periodo_internado": self.periodo.id,
        }
        data.update(over)
        return data

    def test_crear_estudiante_universidad(self):
        self.client.force_authenticate(self.uni_user)
        resp = self.client.post(reverse("student-list"), self._payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(Student.objects.filter(numero_documento="70000010").exists())

    def test_crear_estudiante_fuera_de_ambito(self):
        # Unhappy: universidad fuera del ámbito del usuario → 403.
        otra = f.crear_universidad("Otra", "OT")
        self.client.force_authenticate(self.uni_user)
        resp = self.client.post(reverse("student-list"),
                                self._payload(universidad=otra.id), format="json")
        self.assertEqual(resp.status_code, 403)

    def test_lectura_alcance_universidad(self):
        f.crear_estudiante(creado_por=self.admin, universidad=self.uni,
                           numero_documento="70000011")
        otra = f.crear_universidad("Otra2", "OT2")
        f.crear_estudiante(creado_por=self.admin, universidad=otra,
                           numero_documento="70000012")
        self.client.force_authenticate(self.uni_user)
        resp = self.client.get(reverse("student-list"))
        self.assertEqual(resp.status_code, 200)
        numeros = {r["numero_documento"] for r in resp.data["results"]}
        self.assertEqual(numeros, {"70000011"})

    def test_no_autenticado_401(self):
        resp = self.client.get(reverse("student-list"))
        self.assertEqual(resp.status_code, 401)

    def test_bulk_template_descarga(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("student-bulk-template"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("spreadsheetml", resp["Content-Type"])


class StudentBulkUploadViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uni = f.crear_universidad()
        cls.nivel = f.crear_nivel("PREGRADO", "Pregrado")
        cls.carrera = f.crear_carrera("Medicina", cls.nivel)
        cls.periodo = f.crear_periodo()
        f.crear_tipo_documento("DNI", "DNI")
        f.crear_ubigeo()
        cls.uni_user = f.crear_usuario("bulk_uni", grupos=["Universidad"])
        f.dar_ambito(cls.uni_user, cls.uni, "Universidad")

    def setUp(self):
        self.client = APIClient()

    def _trama(self, filas):
        headers = ["tipo_documento", "numero_documento", "apellido_paterno", "nombres",
                   "carrera_profesional"]
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for fila in filas:
            ws.append(fila)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = "trama.xlsx"
        return buf

    def test_bulk_validate_limpio(self):
        self.client.force_authenticate(self.uni_user)
        buf = self._trama([["DNI", "70000021", "PEREZ", "JUAN", "Medicina"]])
        resp = self.client.post(
            reverse("student-bulk-validate"),
            {"archivo": buf, "universidad_id": self.uni.id, "periodo_internado_id": self.periodo.id},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["valido"])

    def test_bulk_upload_con_errores_422_no_crea(self):
        self.client.force_authenticate(self.uni_user)
        buf = self._trama([["DNI", "123", "PEREZ", "JUAN", "Medicina"]])  # DNI corto
        resp = self.client.post(
            reverse("student-bulk-upload"),
            {"archivo": buf, "universidad_id": self.uni.id, "periodo_internado_id": self.periodo.id},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(Student.objects.count(), 0)

    def test_bulk_upload_limpio_crea(self):
        self.client.force_authenticate(self.uni_user)
        buf = self._trama([["DNI", "70000022", "PEREZ", "JUAN", "Medicina"]])
        resp = self.client.post(
            reverse("student-bulk-upload"),
            {"archivo": buf, "universidad_id": self.uni.id, "periodo_internado_id": self.periodo.id},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["creados"], 1)


class InternshipViewSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        f.crear_estado_internado("REGISTRADO")
        f.crear_estado_internado("ACTIVO")
        cls.ambito = f.crear_ambito()
        cls.ipress = f.crear_ipress(ambito=cls.ambito)
        cls.uni = f.crear_universidad()
        cls.convenio = f.crear_convenio(creado_por=f.crear_usuario("cnv_owner"),
                                        universidad=cls.uni)
        cls.carrera = f.crear_carrera()
        cls.campo = f.crear_asignacion_campo_clinico(
            convenio=cls.convenio, universidad=cls.uni, ipress=cls.ipress, carrera=cls.carrera,
        )
        cls.tutor = f.crear_tutor(universidades=[cls.uni])
        cls.uni_user = f.crear_usuario("int_uni", grupos=["Universidad"])
        f.dar_ambito(cls.uni_user, cls.uni, "Universidad")
        cls.estudiante = f.crear_estudiante(creado_por=cls.uni_user, universidad=cls.uni,
                                            carrera=cls.carrera, numero_documento="61000001")

    def setUp(self):
        self.client = APIClient()

    def _payload(self, **over):
        data = {
            "estudiante": self.estudiante.id, "convenio": self.convenio.id,
            "campo_clinico": self.campo.id, "ipress": self.ipress.codigo_renipress,
            "tutor": self.tutor.id,
            "fecha_inicio": "2026-03-01", "fecha_fin": "2026-09-01",
        }
        data.update(over)
        return data

    def test_crear_internado_universidad(self):
        self.client.force_authenticate(self.uni_user)
        resp = self.client.post(reverse("intern-list"), self._payload(), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(Internship.objects.filter(estudiante=self.estudiante).exists())

    def test_crear_internado_rol_ajeno_denegado(self):
        otro = f.crear_usuario("int_otro", grupos=["CONAPRES"])
        f.dar_ambito(otro, self.uni, "CONAPRES")
        self.client.force_authenticate(otro)
        resp = self.client.post(reverse("intern-list"), self._payload(), format="json")
        self.assertEqual(resp.status_code, 403)

    def test_revisar_declaraciones(self):
        internado = f.crear_internado(
            creado_por=self.uni_user, estudiante=self.estudiante, convenio=self.convenio,
            campo_clinico=self.campo, ipress=self.ipress, tutor=self.tutor, ambito=self.ambito,
        )
        internado.estado_declaraciones = "COMPLETAS"
        internado.save(update_fields=["estado_declaraciones"])
        self.client.force_authenticate(self.uni_user)
        resp = self.client.post(
            reverse("intern-revisar-declaraciones", args=[internado.id]),
            {"resultado": "VALIDADAS"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        internado.refresh_from_db()
        self.assertEqual(internado.estado_declaraciones, "VALIDADAS")

    def test_historial_action(self):
        internado = f.crear_internado(
            creado_por=self.uni_user, estudiante=self.estudiante, convenio=self.convenio,
            campo_clinico=self.campo, ipress=self.ipress, tutor=self.tutor, ambito=self.ambito,
        )
        self.client.force_authenticate(self.uni_user)
        resp = self.client.get(reverse("intern-historial", args=[internado.id]))
        self.assertEqual(resp.status_code, 200)

    def _internado(self):
        return f.crear_internado(
            creado_por=self.uni_user, estudiante=self.estudiante, convenio=self.convenio,
            campo_clinico=self.campo, ipress=self.ipress, tutor=self.tutor, ambito=self.ambito,
        )

    def test_update_internado(self):
        internado = self._internado()
        self.client.force_authenticate(self.uni_user)
        resp = self.client.patch(
            reverse("intern-detail", args=[internado.id]),
            {"observaciones": "nueva nota"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        internado.refresh_from_db()
        self.assertEqual(internado.observaciones, "nueva nota")

    def test_cambiar_estado_requiere_admin(self):
        internado = self._internado()
        self.client.force_authenticate(self.uni_user)  # rol Universidad, no Admin
        resp = self.client.post(
            reverse("intern-cambiar-estado", args=[internado.id]),
            {"estado_codigo": "ACTIVO"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_cambiar_tutor(self):
        internado = self._internado()
        nuevo = f.crear_tutor(numero_documento="61999999", universidades=[self.uni])
        self.client.force_authenticate(self.uni_user)
        resp = self.client.post(
            reverse("intern-cambiar-tutor", args=[internado.id]),
            {"tutor": nuevo.id, "fecha_cambio": "2026-04-01", "motivo": "cambio"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        internado.refresh_from_db()
        self.assertEqual(internado.tutor_id, nuevo.id)

    def test_rotaciones_get_y_post(self):
        f.crear_estado_rotacion("SOLICITADA")
        internado = self._internado()
        origen = f.crear_ipress(codigo="61000201", ambito=self.ambito)
        destino = f.crear_ipress(codigo="61000202", ambito=self.ambito)
        servicio = f.crear_servicio_area()
        self.client.force_authenticate(self.uni_user)
        resp = self.client.post(
            reverse("intern-rotaciones", args=[internado.id]),
            {"ipress_origen": origen.codigo_renipress, "ipress_destino": destino.codigo_renipress,
             "servicio_area": servicio.id, "fecha_inicio": "2026-04-01", "fecha_fin": "2026-05-01"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(len(resp.data), 1)


class TutorViewSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uni = f.crear_universidad()
        cls.dni = f.crear_tipo_documento()
        cls.admin = f.crear_usuario("tut_admin", is_superuser=True)

    def setUp(self):
        self.client = APIClient()

    def test_crear_tutor(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("tutor-list"), {
            "tipo_documento_identidad": self.dni.id, "numero_documento": "45000001",
            "nombres": "LUIS", "apellido_paterno": "RAMOS", "universidades": [self.uni.id],
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Tutor.objects.count(), 1)

    def test_buscar_faltan_parametros(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("tutor-buscar"))
        self.assertEqual(resp.status_code, 400)

    def test_buscar_no_encontrado(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("tutor-buscar"),
                               {"tipo_documento_identidad": self.dni.id, "numero_documento": "0"})
        self.assertEqual(resp.status_code, 404)

    def test_buscar_encontrado(self):
        tutor = f.crear_tutor(tipo_documento=self.dni, numero_documento="45000009",
                              universidades=[self.uni])
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("tutor-buscar"),
                               {"tipo_documento_identidad": self.dni.id,
                                "numero_documento": "45000009"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], tutor.id)

    def test_convenios_action_get(self):
        convenio = f.crear_convenio(creado_por=self.admin, universidad=self.uni)
        ipress = f.crear_ipress(codigo="45000100")
        tutor = f.crear_tutor(tipo_documento=self.dni, numero_documento="45000010",
                              universidades=[self.uni])
        from apps.internados.models import TutorConvenio
        TutorConvenio.objects.create(tutor=tutor, convenio=convenio, ipress=ipress)
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("tutor-convenios", args=[tutor.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_convenios_action_post_y_delete(self):
        convenio = f.crear_convenio(creado_por=self.admin, universidad=self.uni,
                                    tipo_codigo="ESPECIFICO")
        ipress = f.crear_ipress(codigo="45000200")
        tutor = f.crear_tutor(tipo_documento=self.dni, numero_documento="45000020",
                              universidades=[self.uni])
        self.client.force_authenticate(self.admin)
        # POST crea el vínculo.
        resp = self.client.post(
            reverse("tutor-convenios", args=[tutor.id]),
            {"convenio": convenio.id, "ipress": ipress.codigo_renipress}, format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        # DELETE lo elimina.
        resp = self.client.delete(
            reverse("tutor-convenio-detail", args=[tutor.id, convenio.id])
        )
        self.assertEqual(resp.status_code, 204)


class DerivarUniversidadTests(TestCase):
    """Cubre _derivar_universidad_del_usuario vía el endpoint bulk-validate."""

    @classmethod
    def setUpTestData(cls):
        f.crear_tipo_documento("DNI", "DNI")
        f.crear_nivel("PREGRADO", "Pregrado")
        cls.admin = f.crear_usuario("dv_admin", is_superuser=True)

    def setUp(self):
        self.client = APIClient()

    def _archivo(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["tipo_documento", "numero_documento", "apellido_paterno", "nombres",
                   "carrera_profesional"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = "t.xlsx"
        return buf

    def test_admin_sin_universidad_id_error(self):
        # Admin debe enviar universidad_id explícito.
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            reverse("student-bulk-validate"), {"archivo": self._archivo()}, format="multipart"
        )
        self.assertEqual(resp.status_code, 400)

    def test_una_universidad_derivada(self):
        uni = f.crear_universidad("UDeriv", "DV")
        f.crear_carrera("Medicina", f.crear_nivel("PREGRADO", "Pregrado"))
        user = f.crear_usuario("dv_uni", grupos=["Universidad"])
        f.dar_ambito(user, uni, "Universidad")
        self.client.force_authenticate(user)
        resp = self.client.post(
            reverse("student-bulk-validate"), {"archivo": self._archivo()}, format="multipart"
        )
        # Sin filas de datos → válido, deriva la única universidad del perfil.
        self.assertEqual(resp.status_code, 200, resp.data)


class RotationViewSetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        f.crear_estado_rotacion("SOLICITADA")
        f.crear_estado_rotacion("EN_CURSO")
        cls.admin = f.crear_usuario("rot_admin", is_superuser=True)
        cls.ambito = f.crear_ambito()
        cls.internado = f.crear_internado(
            creado_por=cls.admin, ambito=cls.ambito,
            fecha_inicio=datetime.date(2026, 3, 1), fecha_fin=datetime.date(2026, 9, 1),
        )
        cls.origen = f.crear_ipress(codigo="70000101", ambito=cls.ambito)
        cls.destino = f.crear_ipress(codigo="70000102", ambito=cls.ambito)
        cls.servicio = f.crear_servicio_area()

    def setUp(self):
        self.client = APIClient()

    def test_listar_rotaciones(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("rotation-list"))
        self.assertEqual(resp.status_code, 200)

    def _rotacion(self):
        from apps.internados import services
        return services.crear_rotacion(
            internado=self.internado,
            datos={"ipress_origen": self.origen, "ipress_destino": self.destino,
                   "servicio_area": self.servicio,
                   "fecha_inicio": datetime.date(2026, 4, 1),
                   "fecha_fin": datetime.date(2026, 5, 1)},
            usuario=self.admin,
        )

    def test_autorizar_e_iniciar(self):
        f.crear_estado_rotacion("AUTORIZADA")
        rot = self._rotacion()
        participante = f.crear_participante(convenio=self.internado.convenio, es_firmante=True)
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            reverse("rotation-autorizar", args=[rot.id]),
            {"participante_convenio": participante.id, "resultado": "APROBADO",
             "fecha_autorizacion": "2026-04-02"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        resp = self.client.post(reverse("rotation-iniciar", args=[rot.id]))
        self.assertEqual(resp.status_code, 200, resp.data)
        rot.refresh_from_db()
        self.assertEqual(rot.estado_actual.codigo, "EN_CURSO")

    def test_cambiar_estado_rotacion(self):
        f.crear_estado_rotacion("OBSERVADA")
        rot = self._rotacion()
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            reverse("rotation-cambiar-estado", args=[rot.id]),
            {"estado_codigo": "OBSERVADA"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_historial_rotacion(self):
        rot = self._rotacion()
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("rotation-historial", args=[rot.id]))
        self.assertEqual(resp.status_code, 200)
