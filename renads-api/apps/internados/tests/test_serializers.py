"""Pruebas de serializers del módulo Internados (RN-19, RN-24, RN-TUT-MAX, detalles)."""

from types import SimpleNamespace

from django.test import TestCase

from apps.internados.serializers import (
    InternshipWriteSerializer,
    StudentSerializer,
    TutorSerializer,
)
from apps.internados.tests import factories as f


class StudentSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("ser_stu")
        cls.uni = f.crear_universidad()
        cls.dni = f.crear_tipo_documento()
        cls.nivel_pre = f.crear_nivel("PREGRADO", "Pregrado")
        cls.nivel_esp = f.crear_nivel("MAESTRIA", "Maestría")
        cls.carrera_pre = f.crear_carrera("Medicina", cls.nivel_pre)
        cls.carrera_esp = f.crear_carrera("Cardio", cls.nivel_esp)
        cls.periodo = f.crear_periodo()
        cls.especialidad = f.crear_especialidad()

    def _payload(self, **over):
        data = {
            "tipo_documento_identidad": self.dni.id,
            "numero_documento": "70000001",
            "nombres": "JUAN", "apellido_paterno": "PEREZ",
            "universidad": self.uni.id,
            "carrera_profesional": self.carrera_pre.id,
            "periodo_internado": self.periodo.id,
        }
        data.update(over)
        return data

    def test_pregrado_valido(self):
        ser = StudentSerializer(data=self._payload())
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_pregrado_sin_periodo_invalido(self):
        # RN-19: PREGRADO exige periodo.
        ser = StudentSerializer(data=self._payload(periodo_internado=None))
        self.assertFalse(ser.is_valid())
        self.assertIn("periodo_internado", ser.errors)

    def test_no_pregrado_exige_especialidad(self):
        ser = StudentSerializer(data=self._payload(
            carrera_profesional=self.carrera_esp.id, periodo_internado=None, especialidad=None
        ))
        self.assertFalse(ser.is_valid())
        self.assertIn("especialidad", ser.errors)

    def test_nota_fuera_de_rango(self):
        ser = StudentSerializer(data=self._payload(nota_promedio_ponderado="25"))
        self.assertFalse(ser.is_valid())
        self.assertIn("nota_promedio_ponderado", ser.errors)

    def test_detalles_lectura(self):
        est = f.crear_estudiante(creado_por=self.user, universidad=self.uni,
                                 carrera=self.carrera_pre, especialidad=self.especialidad)
        data = StudentSerializer(est).data
        self.assertEqual(data["carrera_profesional_detalle"]["nombre"], "Medicina")
        self.assertEqual(data["especialidad_detalle"]["nombre"], "Cirugía")


class TutorSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dni = f.crear_tipo_documento()
        cls.uni1 = f.crear_universidad("UT1", "T1")
        cls.uni2 = f.crear_universidad("UT2", "T2")

    def _payload(self, universidades):
        return {
            "tipo_documento_identidad": self.dni.id,
            "numero_documento": "45678912", "nombres": "LUIS", "apellido_paterno": "RAMOS",
            "universidades": universidades,
        }

    def _ctx_admin(self):
        admin = f.crear_usuario("ser_tut_admin", is_superuser=True)
        return {"request": SimpleNamespace(user=admin)}

    def test_una_universidad_valida(self):
        ser = TutorSerializer(data=self._payload([self.uni1.id]), context=self._ctx_admin())
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_sin_universidad_invalido(self):
        # RN-24: al menos una universidad.
        ser = TutorSerializer(data=self._payload([]), context=self._ctx_admin())
        self.assertFalse(ser.is_valid())
        self.assertIn("universidades", ser.errors)

    def test_crea_y_asigna_universidades(self):
        ser = TutorSerializer(data=self._payload([self.uni1.id, self.uni2.id]),
                              context=self._ctx_admin())
        self.assertTrue(ser.is_valid(), ser.errors)
        tutor = ser.save()
        self.assertEqual(tutor.universidades.count(), 2)

    def test_usuario_universidad_solo_su_ambito(self):
        # B5/RN-20: usuario Universidad no puede asignar una universidad ajena a su ámbito.
        user = f.crear_usuario("ser_tut_uni", grupos=["Universidad"])
        f.dar_ambito(user, self.uni1, "Universidad")
        ser = TutorSerializer(
            data=self._payload([self.uni2.id]),
            context={"request": SimpleNamespace(user=user)},
        )
        self.assertFalse(ser.is_valid())
        self.assertIn("universidades", ser.errors)

    def test_usuario_universidad_su_propia_ok(self):
        user = f.crear_usuario("ser_tut_uni2", grupos=["Universidad"])
        f.dar_ambito(user, self.uni1, "Universidad")
        ser = TutorSerializer(
            data=self._payload([self.uni1.id]),
            context={"request": SimpleNamespace(user=user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_update_reasigna_universidades(self):
        tutor = f.crear_tutor(numero_documento="45999999", universidades=[self.uni1])
        ser = TutorSerializer(
            tutor, data=self._payload([self.uni1.id, self.uni2.id]),
            context=self._ctx_admin(), partial=True,
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        actualizado = ser.save()
        self.assertEqual(actualizado.universidades.count(), 2)


class InternshipWriteSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("ser_int")
        f.crear_estado_internado("REGISTRADO")

    def test_tutor_max_internos(self):
        # RN-TUT-MAX: un tutor con 5 internos activos rechaza el 6to.
        uni = f.crear_universidad("UMax", "MX")
        ambito = f.crear_ambito("AMB-MX", "Max")
        ipress = f.crear_ipress(codigo="91000099", ambito=ambito)
        convenio = f.crear_convenio(creado_por=self.user, universidad=uni)
        campo = f.crear_asignacion_campo_clinico(
            convenio=convenio, universidad=uni, ipress=ipress, autorizados=10,
        )
        tutor = f.crear_tutor(numero_documento="99000001", universidades=[uni])
        estado = f.crear_estado_internado("ACTIVO")
        for i in range(5):
            f.crear_internado(
                creado_por=self.user, tutor=tutor, estado=estado, ambito=ambito,
                ipress=ipress, convenio=convenio, campo_clinico=campo,
                estudiante=f.crear_estudiante(creado_por=self.user, universidad=uni,
                                              numero_documento=f"9100000{i}"),
            )
        ser = InternshipWriteSerializer()
        with self.assertRaises(Exception):
            ser.validate_tutor(tutor)

    def test_tutor_bajo_tope_ok(self):
        tutor = f.crear_tutor(numero_documento="99000002")
        ser = InternshipWriteSerializer()
        self.assertEqual(ser.validate_tutor(tutor), tutor)
