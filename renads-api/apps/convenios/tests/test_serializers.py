"""Pruebas de serializers del módulo Convenios (validaciones y campos derivados)."""

import datetime

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.convenios.serializers import (
    AdendaWriteSerializer,
    ClinicalFieldAllocationSerializer,
    ClinicalFieldRegistrationSerializer,
    ConventionReadSerializer,
    OrganRepresentativeSerializer,
    UniversityCareerSerializer,
)
from apps.convenios.tests import factories as f


class ConventionReadSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("srz_admin", is_superuser=True)

    def test_serializa_campos_derivados(self):
        # Happy: expone nombre del estado, tipo y vigencia efectiva.
        conv = f.crear_convenio(creado_por=self.admin, titulo="Serial X",
                                fecha_fin=datetime.date(2028, 1, 1))
        data = ConventionReadSerializer(conv).data
        self.assertEqual(data["titulo"], "Serial X")
        self.assertEqual(data["estado_codigo"], "VIGENTE")
        self.assertEqual(data["vigencia_efectiva"], datetime.date(2028, 1, 1))
        self.assertEqual(data["adendas"], [])
        self.assertEqual(data["partes_firmantes"], [])

    def test_detalle_facultad_y_gore(self):
        uni = f.crear_universidad("Uni Det", "UDET")
        facultad = f.crear_facultad(universidad=uni)
        ue = f.crear_unidad_ejecutora(codigo="7201", nombre="UE Det")
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_DIRIS, nombre="DIRIS Det")
        conv = f.crear_convenio(creado_por=self.admin, universidad=uni, tipo_codigo="ESPECIFICO",
                                unidad_organica=unidad, unidad_ejecutora=ue, facultad=facultad)
        data = ConventionReadSerializer(conv).data
        self.assertEqual(data["facultad_detalle"]["nombre"], facultad.nombre)
        self.assertIsNone(data["gobierno_regional_detalle"])


class AdendaWriteSerializerTests(TestCase):
    def test_fecha_inicio_requerida(self):
        # Unhappy: sin fecha_inicio → inválido.
        ser = AdendaWriteSerializer(data={})
        self.assertFalse(ser.is_valid())
        self.assertIn("fecha_inicio", ser.errors)

    def test_valido_con_fecha_inicio(self):
        ser = AdendaWriteSerializer(data={"fecha_inicio": "2027-01-01"})
        self.assertTrue(ser.is_valid(), ser.errors)


class ClinicalFieldRegistrationSerializerTests(TestCase):
    def test_disponibilidad_calculada(self):
        reg = f.crear_registro_campo_clinico(registrados=8, asignados=3)
        data = ClinicalFieldRegistrationSerializer(reg).data
        self.assertEqual(data["disponibilidad"], 5)
        self.assertIsNotNone(data["ipress_detalle"])

    def test_registrados_no_positivo(self):
        # Unhappy: campos_clinicos_registrados debe ser positivo.
        ipress = f.crear_ipress(codigo="86010001")
        carrera = f.crear_carrera("Med SerReg")
        ser = ClinicalFieldRegistrationSerializer(data={
            "ipress": ipress.pk, "carrera_profesional": carrera.id,
            "campos_clinicos_registrados": 0,
        })
        self.assertFalse(ser.is_valid())
        self.assertIn("campos_clinicos_registrados", ser.errors)


class ClinicalFieldAllocationSerializerTests(TestCase):
    def test_fecha_fin_anterior_a_inicio(self):
        # Unhappy: fecha_fin < fecha_inicio → inválido.
        reg = f.crear_registro_campo_clinico(registrados=5)
        admin = f.crear_usuario("cfa_admin", is_superuser=True)
        conv = f.crear_convenio(creado_por=admin)
        ser = ClinicalFieldAllocationSerializer(data={
            "campo_clinico_ipress": reg.id, "convenio": conv.id,
            "campos_clinicos_autorizados": 2,
            "fecha_inicio": "2027-06-01", "fecha_fin": "2027-01-01",
        })
        self.assertFalse(ser.is_valid())
        self.assertIn("fecha_fin", ser.errors)

    def test_autorizados_no_positivo(self):
        reg = f.crear_registro_campo_clinico(registrados=5)
        admin = f.crear_usuario("cfa_admin2", is_superuser=True)
        conv = f.crear_convenio(creado_por=admin)
        ser = ClinicalFieldAllocationSerializer(data={
            "campo_clinico_ipress": reg.id, "convenio": conv.id,
            "campos_clinicos_autorizados": 0,
            "fecha_inicio": "2027-01-01", "fecha_fin": "2027-06-01",
        })
        self.assertFalse(ser.is_valid())


class UniversityCareerSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uni = f.crear_universidad("Uni UC", "UUC")
        cls.facultad = f.crear_facultad(universidad=cls.uni)
        cls.carrera = f.crear_carrera("Med UC")

    def test_facultad_requerida(self):
        # Unhappy RN-FC-03: facultad requerida en la API.
        ser = UniversityCareerSerializer(data={
            "universidad": self.uni.id, "carrera_profesional": self.carrera.id,
        })
        self.assertFalse(ser.is_valid())
        self.assertIn("facultad", ser.errors)

    def test_facultad_de_otra_universidad(self):
        # Unhappy RN-FC-02: la facultad debe pertenecer a la universidad.
        otra_uni = f.crear_universidad("Otra UC", "OUC")
        otra_facultad = f.crear_facultad(universidad=otra_uni)
        ser = UniversityCareerSerializer(data={
            "universidad": self.uni.id, "carrera_profesional": self.carrera.id,
            "facultad": otra_facultad.id,
        })
        self.assertFalse(ser.is_valid())

    def test_valido(self):
        ser = UniversityCareerSerializer(data={
            "universidad": self.uni.id, "carrera_profesional": self.carrera.id,
            "facultad": self.facultad.id,
        })
        self.assertTrue(ser.is_valid(), ser.errors)


class OrganRepresentativeSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uni = f.crear_universidad("Uni Rep Srz", "URSZ")
        cls.tipo_doc = f.crear_tipo_documento()

    def _payload(self, **over):
        # Cargo global (sin unidad orgánica): aplica a cualquier entidad.
        from apps.convenios.models import ExecutivePosition
        cargo = ExecutivePosition.objects.create(
            organo=f.crear_organo(f.ORGANO_UNIVERSIDAD), unidad_organica=None,
            nombre_masculino="Rector Global Srz", nombre_femenino="Rectora Global Srz",
        )
        ct = ContentType.objects.get_for_model(type(self.uni))
        data = {
            "tipo_contenido": ct.id, "id_objeto": self.uni.id, "nombre": "Rep Srz",
            "tipo_documento_identidad": self.tipo_doc.id, "numero_documento_identidad": "30000001",
            "sexo": "M", "cargo_ejecutivo": cargo.id, "fecha_inicio_designacion": "2026-03-01",
        }
        data.update(over)
        return data

    def test_valido(self):
        ser = OrganRepresentativeSerializer(data=self._payload())
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_documento_duplicado_activo(self):
        # Unhappy: documento repetido entre representantes activos → inválido.
        f.crear_representante(entidad=self.uni, numero="30000002",
                              tipo_documento=self.tipo_doc)
        ser = OrganRepresentativeSerializer(data=self._payload(numero_documento_identidad="30000002"))
        self.assertFalse(ser.is_valid())
        self.assertIn("numero_documento_identidad", ser.errors)

    def test_entidad_inexistente(self):
        # Unhappy: id_objeto que no existe → inválido.
        ser = OrganRepresentativeSerializer(data=self._payload(id_objeto=999999))
        self.assertFalse(ser.is_valid())

    def test_tipo_no_permitido(self):
        # Unhappy: un ContentType fuera de la lista permitida → inválido.
        from apps.convenios.models import Region
        region = f.crear_region()
        ct = ContentType.objects.get_for_model(Region)
        ser = OrganRepresentativeSerializer(data=self._payload(
            tipo_contenido=ct.id, id_objeto=region.pk))
        self.assertFalse(ser.is_valid())
        self.assertIn("tipo_contenido", ser.errors)

    def test_cargo_no_corresponde_a_entidad(self):
        # Unhappy: cargo con unidad orgánica pero entidad no es esa OrganicUnit.
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_MINSA, nombre="UO Cargo Srz")
        cargo = f.crear_cargo(unidad=unidad, nombre="Cargo UO Srz")
        ser = OrganRepresentativeSerializer(data=self._payload(cargo_ejecutivo=cargo.id))
        self.assertFalse(ser.is_valid())
        self.assertIn("cargo_ejecutivo", ser.errors)
