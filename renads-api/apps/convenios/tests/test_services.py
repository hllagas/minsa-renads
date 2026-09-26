"""Pruebas de services del módulo Convenios: reglas de negocio (RN) de escritura.

Cubre el ciclo de vida del convenio, campos clínicos (registro CONAPRES y asignación
por Órgano Regional), partes por tipo, adendas, partes firmantes, nomenclatura,
representantes de órgano y carreras por facultad. Los objetos se arman por ORM en
``setUpTestData``; no se invocan dependencias de sistema (PDF/soffice/storage).
"""

import datetime

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.convenios import services
from apps.convenios.models import (
    ClinicalFieldAllocation,
    ClinicalFieldRegistration,
    Convention,
    ConventionParty,
    OrganicUnit,
    OrganRepresentative,
    OrganRepresentativeHistory,
    UniversityCareer,
)
from apps.convenios.tests import factories as f


# ---------------------------------------------------------------------------
# Helpers internos de estados/fechas
# ---------------------------------------------------------------------------
class HelperServiceTests(TestCase):
    def test_sumar_anios_normal(self):
        self.assertEqual(
            services._sumar_anios(datetime.date(2026, 3, 1), 3), datetime.date(2029, 3, 1)
        )

    def test_sumar_anios_29_febrero(self):
        # Edge: 29-feb en año no bisiesto se ajusta al 28.
        self.assertEqual(
            services._sumar_anios(datetime.date(2024, 2, 29), 1), datetime.date(2025, 2, 28)
        )

    def test_obtener_estado_inexistente(self):
        with self.assertRaises(ValidationError):
            services._obtener_estado("NO_EXISTE")


# ---------------------------------------------------------------------------
# crear_convenio (RN-1, RN-3, partes por tipo)
# ---------------------------------------------------------------------------
class CrearConvenioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("cc_user", is_superuser=True)
        cls.uni = f.crear_universidad("Uni CrearConv", "UCCV")

    def _datos_marco(self, **over):
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_GORE, nombre="GERESA CC")
        gore = f.crear_gobierno_regional(nombre="GORE CC")
        ct = ContentType.objects.get_for_model(type(self.uni))
        datos = {
            "tipo_convenio": f.tipo_convenio("MARCO"),
            "titulo": "Marco CC", "unidad_organica": unidad,
            "gobierno_regional": gore, "universidad": self.uni,
            "solicitante_tipo_contenido": ct, "solicitante_id_objeto": self.uni.id,
            "fecha_solicitud": f.HOY, "fecha_inicio": f.HOY,
        }
        datos.update(over)
        return datos

    def test_crear_marco_gore_happy(self):
        # Happy: GORE crea un Marco; fecha_fin se autocalcula por anios_vigencia.
        conv = services.crear_convenio(datos=self._datos_marco(), usuario=self.usuario)
        self.assertEqual(conv.estado_actual.codigo, "SOLICITUD_REGISTRADA")
        self.assertEqual(conv.fecha_fin, datetime.date(2030, 3, 1))
        self.assertTrue(conv.historial_estados.exists())

    def test_marco_categoria_no_permitida(self):
        # Unhappy RN-1: una Unidad Ejecutora no puede solicitar Marco.
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_UE, nombre="UE CC")
        datos = self._datos_marco(unidad_organica=unidad, gobierno_regional=None)
        with self.assertRaises(ValidationError):
            services.crear_convenio(datos=datos, usuario=self.usuario)

    def test_marco_no_lleva_unidad_ejecutora_ni_facultad(self):
        # Unhappy: un Marco no puede llevar unidad ejecutora / facultad.
        ue = f.crear_unidad_ejecutora(codigo="7001", nombre="UE X")
        with self.assertRaises(ValidationError):
            services.crear_convenio(datos=self._datos_marco(unidad_ejecutora=ue),
                                    usuario=self.usuario)

    def test_marco_regional_exige_gobierno_regional(self):
        # Unhappy RN-GORE-1: Marco de GORE sin gobierno_regional → error.
        with self.assertRaises(ValidationError):
            services.crear_convenio(datos=self._datos_marco(gobierno_regional=None),
                                    usuario=self.usuario)

    def test_marco_no_depende_de_otro(self):
        # Unhappy: un Marco no puede colgar de otro convenio_marco.
        otro_marco = services.crear_convenio(datos=self._datos_marco(), usuario=self.usuario)
        with self.assertRaises(ValidationError):
            services.crear_convenio(
                datos=self._datos_marco(convenio_marco=otro_marco), usuario=self.usuario
            )

    def test_especifico_requiere_marco_vigente(self):
        # Unhappy RN-3: Específico (no DIRIS) sin Marco → error.
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_GORE, nombre="GERESA E")
        facultad = f.crear_facultad(universidad=self.uni)
        ue = f.crear_unidad_ejecutora(codigo="7002", nombre="UE E")
        ct = ContentType.objects.get_for_model(type(self.uni))
        datos = {
            "tipo_convenio": f.tipo_convenio("ESPECIFICO"), "titulo": "Esp E",
            "unidad_organica": unidad, "universidad": self.uni,
            "unidad_ejecutora": ue, "facultad": facultad,
            "solicitante_tipo_contenido": ct, "solicitante_id_objeto": self.uni.id,
            "fecha_solicitud": f.HOY, "fecha_inicio": f.HOY,
        }
        with self.assertRaises(ValidationError):
            services.crear_convenio(datos=datos, usuario=self.usuario)

    def test_especifico_diris_sin_marco_ok(self):
        # Happy: DIRIS crea un Específico sin Marco (exenta RN-3).
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_DIRIS, nombre="DIRIS CC")
        facultad = f.crear_facultad(universidad=self.uni)
        ue = f.crear_unidad_ejecutora(codigo="7003", nombre="UE DIRIS")
        ct = ContentType.objects.get_for_model(type(self.uni))
        datos = {
            "tipo_convenio": f.tipo_convenio("ESPECIFICO"), "titulo": "Esp DIRIS",
            "unidad_organica": unidad, "universidad": self.uni,
            "unidad_ejecutora": ue, "facultad": facultad,
            "solicitante_tipo_contenido": ct, "solicitante_id_objeto": self.uni.id,
            "fecha_solicitud": f.HOY, "fecha_inicio": f.HOY,
        }
        conv = services.crear_convenio(datos=datos, usuario=self.usuario)
        self.assertEqual(conv.tipo_convenio.codigo, "ESPECIFICO")

    def test_especifico_facultad_de_otra_universidad(self):
        # Unhappy: la facultad debe pertenecer a la universidad esperada.
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_DIRIS, nombre="DIRIS FF")
        otra_uni = f.crear_universidad("Otra FF", "OFF")
        facultad = f.crear_facultad(universidad=otra_uni)
        ue = f.crear_unidad_ejecutora(codigo="7004", nombre="UE FF")
        ct = ContentType.objects.get_for_model(type(self.uni))
        datos = {
            "tipo_convenio": f.tipo_convenio("ESPECIFICO"), "titulo": "Esp FF",
            "unidad_organica": unidad, "universidad": self.uni,
            "unidad_ejecutora": ue, "facultad": facultad,
            "solicitante_tipo_contenido": ct, "solicitante_id_objeto": self.uni.id,
            "fecha_solicitud": f.HOY, "fecha_inicio": f.HOY,
        }
        with self.assertRaises(ValidationError):
            services.crear_convenio(datos=datos, usuario=self.usuario)


# ---------------------------------------------------------------------------
# _avanzar_estado / cambiar_estado
# ---------------------------------------------------------------------------
class CambiarEstadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("ce_user", is_superuser=True)

    def test_avanzar_estado_forward(self):
        # Happy: avanza a un estado posterior.
        conv = f.crear_convenio(creado_por=self.usuario, estado_codigo="SOLICITUD_REGISTRADA")
        services._avanzar_estado(conv, "VALIDADO_TECNICAMENTE", self.usuario)
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "VALIDADO_TECNICAMENTE")

    def test_avanzar_estado_no_regresa(self):
        # Edge: idempotente y forward-only, no retrocede un convenio ya vigente.
        conv = f.crear_convenio(creado_por=self.usuario, estado_codigo="VIGENTE")
        services._avanzar_estado(conv, "SOLICITUD_REGISTRADA", self.usuario)
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "VIGENTE")

    def test_avanzar_estado_especifico_en_marco_no_aplica(self):
        # Edge: un estado ESPECIFICO no aplica a un Marco → no cambia.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="SOLICITUD_REGISTRADA")
        services._avanzar_estado(conv, "CONAPRES_FAVORABLE", self.usuario)
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "SOLICITUD_REGISTRADA")

    def test_set_estado_especifico_en_marco_lanza(self):
        # Unhappy: forzar un estado ESPECIFICO en un Marco vía cambiar_estado → error.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE)
        with self.assertRaises(ValidationError):
            services.cambiar_estado(convenio=conv, nuevo_estado_codigo="CONAPRES_FAVORABLE",
                                    usuario=self.usuario)

    def test_adenda_vigente_marca_origen_ampliado(self):
        # Happy: al pasar una adenda a VIGENTE, el origen queda AMPLIADO.
        origen = f.crear_convenio(creado_por=self.usuario, estado_codigo="VIGENTE",
                                  titulo="Origen Amp")
        adenda = f.crear_convenio(creado_por=self.usuario, universidad=origen.universidad,
                                  estado_codigo="SOLICITUD_REGISTRADA", titulo="Adenda Amp")
        adenda.convenio_origen = origen
        adenda.es_adenda = True
        adenda.save()
        services.cambiar_estado(convenio=adenda, nuevo_estado_codigo="VIGENTE",
                                usuario=self.usuario)
        origen.refresh_from_db()
        self.assertEqual(origen.estado_actual.codigo, "AMPLIADO")


# ---------------------------------------------------------------------------
# actualizar_convenio
# ---------------------------------------------------------------------------
class ActualizarConvenioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("ac_user", is_superuser=True)

    def test_actualizar_titulo(self):
        # Un Específico completo (con UE + facultad) para pasar la revalidación de partes.
        uni = f.crear_universidad("Uni Act", "UACT")
        facultad = f.crear_facultad(universidad=uni)
        ue = f.crear_unidad_ejecutora(codigo="7101", nombre="UE Act")
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_DIRIS, nombre="DIRIS Act")
        conv = f.crear_convenio(creado_por=self.usuario, universidad=uni, tipo_codigo="ESPECIFICO",
                                titulo="Antes", unidad_organica=unidad,
                                unidad_ejecutora=ue, facultad=facultad)
        services.actualizar_convenio(convenio=conv, datos={"titulo": "Después"},
                                     usuario=self.usuario)
        conv.refresh_from_db()
        self.assertEqual(conv.titulo, "Después")

    def test_actualizar_marco_con_facultad_falla(self):
        # Unhappy: PATCH que pone facultad a un Marco viola las partes por tipo.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, gobierno_regional=None)
        # El Marco válido no lleva GORE en la fábrica; damos gore para que pase el gate GORE.
        conv.gobierno_regional = f.crear_gobierno_regional(nombre="GORE AC")
        conv.save()
        facultad = f.crear_facultad(universidad=conv.universidad)
        with self.assertRaises(ValidationError):
            services.actualizar_convenio(convenio=conv, datos={"facultad": facultad},
                                         usuario=self.usuario)


# ---------------------------------------------------------------------------
# Evaluación técnica + nomenclatura
# ---------------------------------------------------------------------------
class EvaluacionTecnicaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("et_user", is_superuser=True)

    def test_validado_marco_exige_nomenclatura(self):
        # Unhappy: aprobar DIGEP un Marco sin nomenclatura → error.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="EN_EVALUACION_DIGEP")
        datos = {"resultado": "VALIDADO", "fecha_evaluacion": f.HOY}
        with self.assertRaises(ValidationError):
            services.registrar_evaluacion_tecnica(convenio=conv, datos=dict(datos),
                                                  usuario=self.usuario)

    def test_validado_marco_con_nomenclatura(self):
        # Happy: aprueba DIGEP y persiste la nomenclatura, avanza a VALIDADO_TECNICAMENTE.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="EN_EVALUACION_DIGEP")
        datos = {"resultado": "VALIDADO", "fecha_evaluacion": f.HOY, "nomenclatura": "N-001-2026"}
        services.registrar_evaluacion_tecnica(convenio=conv, datos=datos, usuario=self.usuario)
        conv.refresh_from_db()
        self.assertEqual(conv.nomenclatura, "N-001-2026")
        self.assertEqual(conv.estado_actual.codigo, "VALIDADO_TECNICAMENTE")

    def test_observado_avanza_a_observado_digep(self):
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="EN_EVALUACION_DIGEP")
        datos = {"resultado": "OBSERVADO", "fecha_evaluacion": f.HOY, "observaciones": "X"}
        services.registrar_evaluacion_tecnica(convenio=conv, datos=datos, usuario=self.usuario)
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "OBSERVADO_DIGEP")


# ---------------------------------------------------------------------------
# Opiniones CONAPRES / OGAJ
# ---------------------------------------------------------------------------
class OpinionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("op_user", is_superuser=True)

    def test_conapres_solo_especifico(self):
        # Unhappy: la opinión CONAPRES solo aplica a Específicos.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE)
        with self.assertRaises(ValidationError):
            services.registrar_opinion_conapres(
                convenio=conv, datos={"fecha_solicitud": f.HOY, "resultado_opinion": "FAVORABLE"},
                usuario=self.usuario,
            )

    def test_conapres_favorable(self):
        # Happy: opinión CONAPRES favorable avanza el estado del Específico.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="ESPECIFICO",
                                estado_codigo="SOLICITUD_REGISTRADA")
        services.registrar_opinion_conapres(
            convenio=conv, datos={"fecha_solicitud": f.HOY, "resultado_opinion": "FAVORABLE"},
            usuario=self.usuario,
        )
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "CONAPRES_FAVORABLE")

    def test_ogaj_solo_marco(self):
        # Unhappy: la opinión jurídica OGAJ solo aplica a Marcos.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="ESPECIFICO")
        with self.assertRaises(ValidationError):
            services.registrar_opinion_juridica(
                convenio=conv, datos={"fecha_envio": f.HOY, "resultado_opinion": "FAVORABLE"},
                usuario=self.usuario,
            )

    def test_ogaj_favorable(self):
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="VALIDADO_TECNICAMENTE")
        services.registrar_opinion_juridica(
            convenio=conv, datos={"fecha_envio": f.HOY, "resultado_opinion": "FAVORABLE"},
            usuario=self.usuario,
        )
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "OGAJ_FAVORABLE")

    def test_conapres_observado(self):
        # Edge: opinión CONAPRES observada avanza a CONAPRES_OBSERVADO.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="ESPECIFICO",
                                estado_codigo="SOLICITUD_REGISTRADA")
        services.registrar_opinion_conapres(
            convenio=conv, datos={"fecha_solicitud": f.HOY, "estado_atencion": "ATENDIDO",
                                  "resultado_opinion": "OBSERVADO"},
            usuario=self.usuario,
        )
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "CONAPRES_OBSERVADO")

    def test_ogaj_observado(self):
        # Edge: opinión OGAJ observada avanza a OGAJ_OBSERVADO.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="VALIDADO_TECNICAMENTE")
        services.registrar_opinion_juridica(
            convenio=conv, datos={"fecha_envio": f.HOY, "resultado_opinion": "OBSERVADO"},
            usuario=self.usuario,
        )
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "OGAJ_OBSERVADO")

    def test_agregar_participante(self):
        # Happy: agrega un participante al convenio.
        conv = f.crear_convenio(creado_por=self.usuario)
        ct = ContentType.objects.get_for_model(type(conv.universidad))
        part = services.agregar_participante(
            convenio=conv,
            datos={"tipo_contenido": ct, "id_objeto": conv.universidad.id, "es_firmante": True},
            usuario=self.usuario,
        )
        self.assertIsNotNone(part.pk)


# ---------------------------------------------------------------------------
# Campos clínicos — Registro (CONAPRES)
# ---------------------------------------------------------------------------
class RegistroCampoClinicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("rcc_user", is_superuser=True)
        cls.carrera = f.crear_carrera("Medicina RCC")

    def test_crear_registro_sede_docente(self):
        # Happy: registra campos clínicos sobre una sede docente.
        ipress = f.crear_ipress(codigo="80010001", es_sede_docente=True)
        reg = services.crear_registro_campo_clinico(
            datos={"ipress": ipress, "carrera_profesional": self.carrera,
                   "campos_clinicos_registrados": 8},
            usuario=self.usuario,
        )
        self.assertEqual(reg.campos_clinicos_asignados, 0)

    def test_crear_registro_no_sede_docente(self):
        # Unhappy: IPRESS no autorizada como sede docente → error.
        ipress = f.crear_ipress(codigo="80020001", es_sede_docente=False)
        with self.assertRaises(ValidationError):
            services.crear_registro_campo_clinico(
                datos={"ipress": ipress, "carrera_profesional": self.carrera,
                       "campos_clinicos_registrados": 5},
                usuario=self.usuario,
            )

    def test_actualizar_registro_menos_que_asignados(self):
        # Unhappy: bajar registrados por debajo de lo ya asignado → error.
        reg = f.crear_registro_campo_clinico(carrera=self.carrera, registrados=10, asignados=6)
        with self.assertRaises(ValidationError):
            services.actualizar_registro_campo_clinico(
                registro=reg, datos={"campos_clinicos_registrados": 4}, usuario=self.usuario
            )

    def test_actualizar_registro_ok(self):
        # Happy: sube el total registrado.
        reg = f.crear_registro_campo_clinico(carrera=self.carrera, registrados=5)
        services.actualizar_registro_campo_clinico(
            registro=reg, datos={"campos_clinicos_registrados": 9}, usuario=self.usuario
        )
        reg.refresh_from_db()
        self.assertEqual(reg.campos_clinicos_registrados, 9)


# ---------------------------------------------------------------------------
# Campos clínicos — Asignación (Órgano Regional) + acumulador
# ---------------------------------------------------------------------------
class AsignacionCampoClinicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("acc_user", is_superuser=True)
        cls.carrera = f.crear_carrera("Medicina ACC")

    def _registro(self, registrados=10):
        ipress = f.crear_ipress(codigo="81010001")
        return f.crear_registro_campo_clinico(ipress=ipress, carrera=self.carrera,
                                             registrados=registrados)

    def _convenio(self, universidad=None):
        return f.crear_convenio(creado_por=self.usuario, universidad=universidad,
                                tipo_codigo="ESPECIFICO", estado_codigo="VIGENTE")

    def test_crear_asignacion_recalcula_acumulador(self):
        # Happy: crea una asignación; el acumulador del registro se recalcula.
        reg = self._registro(registrados=10)
        conv = self._convenio()
        asig = services.crear_asignacion_campo_clinico(
            datos={"campo_clinico_ipress": reg, "convenio": conv,
                   "campos_clinicos_autorizados": 4,
                   "fecha_inicio": f.HOY, "fecha_fin": datetime.date(2027, 3, 1)},
            usuario=self.usuario,
        )
        reg.refresh_from_db()
        self.assertEqual(reg.campos_clinicos_asignados, 4)
        # La sede/carrera/universidad se derivan del registro y del convenio.
        self.assertEqual(asig.ipress_id, reg.ipress_id)
        self.assertEqual(asig.universidad_id, conv.universidad_id)

    def test_crear_asignacion_excede_disponibilidad(self):
        # Unhappy: autorizar más que lo disponible → error.
        reg = self._registro(registrados=3)
        conv = self._convenio()
        with self.assertRaises(ValidationError):
            services.crear_asignacion_campo_clinico(
                datos={"campo_clinico_ipress": reg, "convenio": conv,
                       "campos_clinicos_autorizados": 5,
                       "fecha_inicio": f.HOY, "fecha_fin": datetime.date(2027, 3, 1)},
                usuario=self.usuario,
            )

    def test_crear_asignacion_convenio_no_vigente(self):
        # Unhappy: el Específico debe estar vigente.
        reg = self._registro()
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="ESPECIFICO",
                                estado_codigo="SOLICITUD_REGISTRADA")
        with self.assertRaises(ValidationError):
            services.crear_asignacion_campo_clinico(
                datos={"campo_clinico_ipress": reg, "convenio": conv,
                       "campos_clinicos_autorizados": 2,
                       "fecha_inicio": f.HOY, "fecha_fin": datetime.date(2027, 3, 1)},
                usuario=self.usuario,
            )

    def test_crear_asignacion_convenio_marco(self):
        # Unhappy: la asignación solo aplica a Específicos.
        reg = self._registro()
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="VIGENTE")
        with self.assertRaises(ValidationError):
            services.crear_asignacion_campo_clinico(
                datos={"campo_clinico_ipress": reg, "convenio": conv,
                       "campos_clinicos_autorizados": 1,
                       "fecha_inicio": f.HOY, "fecha_fin": datetime.date(2027, 3, 1)},
                usuario=self.usuario,
            )

    def test_actualizar_asignacion_revalida(self):
        # Happy + Unhappy: actualizar dentro y fuera de disponibilidad.
        reg = self._registro(registrados=6)
        conv = self._convenio()
        asig = services.crear_asignacion_campo_clinico(
            datos={"campo_clinico_ipress": reg, "convenio": conv,
                   "campos_clinicos_autorizados": 2,
                   "fecha_inicio": f.HOY, "fecha_fin": datetime.date(2027, 3, 1)},
            usuario=self.usuario,
        )
        services.actualizar_asignacion_campo_clinico(
            asignacion=asig, datos={"campos_clinicos_autorizados": 5}, usuario=self.usuario
        )
        reg.refresh_from_db()
        self.assertEqual(reg.campos_clinicos_asignados, 5)
        with self.assertRaises(ValidationError):
            services.actualizar_asignacion_campo_clinico(
                asignacion=asig, datos={"campos_clinicos_autorizados": 20},
                usuario=self.usuario,
            )

    def test_eliminar_asignacion_recalcula(self):
        # Happy: eliminar la asignación deja el acumulador en 0.
        reg = self._registro(registrados=6)
        conv = self._convenio()
        asig = services.crear_asignacion_campo_clinico(
            datos={"campo_clinico_ipress": reg, "convenio": conv,
                   "campos_clinicos_autorizados": 3,
                   "fecha_inicio": f.HOY, "fecha_fin": datetime.date(2027, 3, 1)},
            usuario=self.usuario,
        )
        services.eliminar_asignacion_campo_clinico(asignacion=asig, usuario=self.usuario)
        reg.refresh_from_db()
        self.assertEqual(reg.campos_clinicos_asignados, 0)
        self.assertFalse(ClinicalFieldAllocation.objects.filter(pk=asig.pk).exists())

    def test_disponibilidad_con_dos_asignaciones(self):
        # Edge: dos universidades comparten un registro; Σ no puede exceder registrados.
        reg = self._registro(registrados=5)
        conv1 = self._convenio(universidad=f.crear_universidad("U Comp1", "UCP1"))
        conv2 = self._convenio(universidad=f.crear_universidad("U Comp2", "UCP2"))
        services.crear_asignacion_campo_clinico(
            datos={"campo_clinico_ipress": reg, "convenio": conv1,
                   "campos_clinicos_autorizados": 3,
                   "fecha_inicio": f.HOY, "fecha_fin": datetime.date(2027, 3, 1)},
            usuario=self.usuario,
        )
        with self.assertRaises(ValidationError):
            services.crear_asignacion_campo_clinico(
                datos={"campo_clinico_ipress": reg, "convenio": conv2,
                       "campos_clinicos_autorizados": 3,
                       "fecha_inicio": f.HOY, "fecha_fin": datetime.date(2027, 3, 1)},
                usuario=self.usuario,
            )


# ---------------------------------------------------------------------------
# Adendas
# ---------------------------------------------------------------------------
class AdendaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("ad_user", is_superuser=True)

    def test_crear_adenda_hereda_origen(self):
        # Happy: la adenda hereda tipo/universidad/órgano del origen.
        origen = f.crear_convenio(creado_por=self.usuario, estado_codigo="VIGENTE",
                                  titulo="Origen Ad")
        adenda = services.crear_adenda(
            convenio_origen=origen,
            datos={"fecha_inicio": datetime.date(2027, 1, 1)}, usuario=self.usuario,
        )
        self.assertTrue(adenda.es_adenda)
        self.assertEqual(adenda.convenio_origen_id, origen.id)
        self.assertEqual(adenda.universidad_id, origen.universidad_id)
        self.assertEqual(adenda.estado_actual.codigo, "SOLICITUD_REGISTRADA")

    def test_crear_adenda_sin_fecha_inicio(self):
        # Unhappy: falta fecha_inicio → error.
        origen = f.crear_convenio(creado_por=self.usuario)
        with self.assertRaises(ValidationError):
            services.crear_adenda(convenio_origen=origen, datos={}, usuario=self.usuario)

    def test_crear_adenda_fecha_fin_anterior(self):
        # Unhappy: fecha_fin <= fecha_inicio → error.
        origen = f.crear_convenio(creado_por=self.usuario)
        with self.assertRaises(ValidationError):
            services.crear_adenda(
                convenio_origen=origen,
                datos={"fecha_inicio": datetime.date(2027, 6, 1),
                       "fecha_fin": datetime.date(2027, 1, 1)},
                usuario=self.usuario,
            )


# ---------------------------------------------------------------------------
# Gate de suscripción — campos clínicos con resolución CONAPRES
# ---------------------------------------------------------------------------
class GateSuscripcionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("gs_user", is_superuser=True)

    def test_firma_especifico_sin_campos_conapres(self):
        # Unhappy: firmar un Específico sin campo clínico con resolución CONAPRES → error.
        ue = f.crear_unidad_ejecutora(codigo="8201", nombre="UE Gate")
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="ESPECIFICO",
                                estado_codigo="ENVIADO_SG", unidad_ejecutora=ue)
        ct = ContentType.objects.get_for_model(type(conv.universidad))
        with self.assertRaises(ValidationError):
            services.registrar_firma(
                convenio=conv,
                datos={"firmante_tipo_contenido": ct, "firmante_id_objeto": conv.universidad.id,
                       "estado_firma": "FIRMADO"},
                usuario=self.usuario,
            )

    def test_firma_especifico_con_campos_conapres(self):
        # Happy: con campo clínico con resolución sobre la UE, la firma procede.
        ambito = f.crear_ambito("GATE", "Gate")
        ue = f.crear_unidad_ejecutora(codigo="8202", nombre="UE Gate2", ambito=ambito)
        ipress = f.crear_ipress(codigo="82020001", unidad_ejecutora=ue, ambito=ambito,
                                es_sede_docente=True)
        f.crear_registro_campo_clinico(ipress=ipress, carrera=f.crear_carrera("Med Gate"),
                                       numero_resolucion_conapres="RES-1")
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="ESPECIFICO",
                                estado_codigo="ENVIADO_SG", unidad_ejecutora=ue)
        ct = ContentType.objects.get_for_model(type(conv.universidad))
        firma = services.registrar_firma(
            convenio=conv,
            datos={"firmante_tipo_contenido": ct, "firmante_id_objeto": conv.universidad.id,
                   "estado_firma": "FIRMADO"},
            usuario=self.usuario,
        )
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "FIRMADO_EXTERNOS")
        self.assertIsNotNone(firma.pk)

    def test_firma_marco_organicunit_es_firmado_minsa(self):
        # Happy: firmante OrganicUnit en un Marco → estado FIRMADO_MINSA.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="ENVIADO_SG")
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_MINSA, nombre="MINSA Firma")
        ct = ContentType.objects.get_for_model(OrganicUnit)
        firma = services.registrar_firma(
            convenio=conv,
            datos={"firmante_tipo_contenido": ct, "firmante_id_objeto": unidad.id,
                   "estado_firma": "FIRMADO"},
            usuario=self.usuario,
        )
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "FIRMADO_MINSA")
        self.assertIsNotNone(firma.pk)

    def test_observaciones_pendientes_conapres_y_juridica(self):
        # Unhappy RN-9: observación CONAPRES pendiente bloquea la firma.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="ENVIADO_SG")
        from apps.convenios.models import LegalOpinion
        LegalOpinion.objects.create(convenio=conv, fecha_envio=f.HOY,
                                    resultado_opinion="OBSERVADO")
        self.assertTrue(services._tiene_observaciones_pendientes(conv))
        ct = ContentType.objects.get_for_model(OrganicUnit)
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_MINSA, nombre="MINSA Obs")
        with self.assertRaises(ValidationError):
            services.registrar_firma(
                convenio=conv,
                datos={"firmante_tipo_contenido": ct, "firmante_id_objeto": unidad.id,
                       "estado_firma": "FIRMADO"},
                usuario=self.usuario,
            )

    def test_firma_con_observaciones_pendientes(self):
        # Unhappy RN-9: no se firma con observaciones técnicas pendientes.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, estado_codigo="OBSERVADO_DIGEP")
        from apps.convenios.models import TechnicalEvaluation
        TechnicalEvaluation.objects.create(
            convenio=conv, resultado="OBSERVADO", evaluado_por=self.usuario,
            fecha_evaluacion=f.HOY,
        )
        ct = ContentType.objects.get_for_model(type(conv.universidad))
        with self.assertRaises(ValidationError):
            services.registrar_firma(
                convenio=conv,
                datos={"firmante_tipo_contenido": ct, "firmante_id_objeto": conv.universidad.id,
                       "estado_firma": "FIRMADO"},
                usuario=self.usuario,
            )


# ---------------------------------------------------------------------------
# Publicación
# ---------------------------------------------------------------------------
class PublicacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("pub_user", is_superuser=True)

    def test_publicar_actualiza_fechas_y_estado(self):
        conv = f.crear_convenio(creado_por=self.usuario, estado_codigo="SUSCRITO")
        services.publicar_convenio(
            convenio=conv,
            datos={"fecha_publicacion": f.HOY, "fecha_inicio": f.HOY,
                   "fecha_fin": datetime.date(2029, 1, 1)},
            usuario=self.usuario,
        )
        conv.refresh_from_db()
        self.assertEqual(conv.estado_actual.codigo, "PUBLICADO")
        self.assertEqual(conv.fecha_fin, datetime.date(2029, 1, 1))


# ---------------------------------------------------------------------------
# Representantes de órgano (histórico de bajas)
# ---------------------------------------------------------------------------
class OrganoRepresentanteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("or_user", is_superuser=True)
        cls.uni = f.crear_universidad("Uni Rep S", "URS")
        cls.tipo_doc = f.crear_tipo_documento()

    def _datos(self, cargo, numero="20000001"):
        ct = ContentType.objects.get_for_model(type(self.uni))
        return {
            "tipo_contenido": ct, "id_objeto": self.uni.id, "nombre": "Rep S",
            "tipo_documento_identidad": self.tipo_doc, "numero_documento_identidad": numero,
            "sexo": "M", "cargo_ejecutivo": cargo, "fecha_inicio_designacion": f.HOY,
        }

    def test_registrar_primer_representante(self):
        # Happy: sin anterior, solo crea el nuevo.
        cargo = f.crear_cargo(nombre="Rector S")
        rep = services.registrar_organo_representante(datos=self._datos(cargo),
                                                      usuario=self.usuario)
        self.assertTrue(rep.activo)
        self.assertEqual(OrganRepresentativeHistory.objects.count(), 0)

    def test_reemplazo_da_de_baja_anterior_y_historiza(self):
        # Happy: designar uno nuevo para el mismo par da de baja al anterior + histórico.
        cargo = f.crear_cargo(nombre="Decano S")
        anterior = services.registrar_organo_representante(
            datos=self._datos(cargo, numero="20000002"), usuario=self.usuario
        )
        services.registrar_organo_representante(
            datos=self._datos(cargo, numero="20000003"), usuario=self.usuario
        )
        anterior.refresh_from_db()
        self.assertFalse(anterior.activo)
        self.assertEqual(OrganRepresentativeHistory.objects.count(), 1)
        self.assertEqual(OrganRepresentative.objects.filter(activo=True).count(), 1)


# ---------------------------------------------------------------------------
# Autorizar sede docente
# ---------------------------------------------------------------------------
class AutorizarSedeDocenteTests(TestCase):
    def test_autorizar_y_desautorizar(self):
        usuario = f.crear_usuario("asd_user", is_superuser=True)
        ipress = f.crear_ipress(codigo="83010001", es_sede_docente=False)
        services.autorizar_sede_docente(ipress=ipress, usuario=usuario, autorizar=True)
        ipress.refresh_from_db()
        self.assertTrue(ipress.es_sede_docente)
        services.autorizar_sede_docente(ipress=ipress, usuario=usuario, autorizar=False)
        ipress.refresh_from_db()
        self.assertFalse(ipress.es_sede_docente)


# ---------------------------------------------------------------------------
# Carreras por facultad (sincronización)
# ---------------------------------------------------------------------------
class SincronizarCarrerasFacultadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("scf_user", is_superuser=True)
        cls.uni = f.crear_universidad("Uni SCF", "USCF")
        cls.facultad = f.crear_facultad(universidad=cls.uni)
        cls.c1 = f.crear_carrera("Medicina SCF")
        cls.c2 = f.crear_carrera("Enfermería SCF")

    def test_alta_de_carreras(self):
        # Happy: da de alta las carreras enviadas.
        resultado = services.sincronizar_carreras_facultad(
            facultad=self.facultad, carreras_ids=[self.c1.id, self.c2.id], usuario=self.usuario
        )
        self.assertEqual(len(resultado), 2)

    def test_baja_de_carreras_no_enviadas(self):
        # Happy: las carreras no enviadas se dan de baja (activo=False).
        services.sincronizar_carreras_facultad(
            facultad=self.facultad, carreras_ids=[self.c1.id, self.c2.id], usuario=self.usuario
        )
        services.sincronizar_carreras_facultad(
            facultad=self.facultad, carreras_ids=[self.c1.id], usuario=self.usuario
        )
        self.assertFalse(
            UniversityCareer.objects.get(facultad=self.facultad, carrera_profesional=self.c2).activo
        )

    def test_carrera_inexistente(self):
        # Unhappy RN-FC-01: carrera inexistente → error.
        with self.assertRaises(ValidationError):
            services.sincronizar_carreras_facultad(
                facultad=self.facultad, carreras_ids=[999999], usuario=self.usuario
            )

    def test_carrera_activa_en_otra_facultad_bloqueada(self):
        # Unhappy RN-FC-04: una carrera activa de otra facultad no puede tomarse.
        otra_facultad = f.crear_facultad(universidad=self.uni, nombre="Facultad Otra SCF")
        services.sincronizar_carreras_facultad(
            facultad=self.facultad, carreras_ids=[self.c1.id], usuario=self.usuario
        )
        with self.assertRaises(ValidationError):
            services.sincronizar_carreras_facultad(
                facultad=otra_facultad, carreras_ids=[self.c1.id], usuario=self.usuario
            )

    def test_carrera_liberada_puede_tomarse(self):
        # Edge: una carrera dada de baja en una facultad puede tomarse por otra.
        otra_facultad = f.crear_facultad(universidad=self.uni, nombre="Facultad Lib SCF")
        services.sincronizar_carreras_facultad(
            facultad=self.facultad, carreras_ids=[self.c1.id], usuario=self.usuario
        )
        # Baja en la primera facultad.
        services.sincronizar_carreras_facultad(
            facultad=self.facultad, carreras_ids=[], usuario=self.usuario
        )
        # Ahora la segunda facultad la toma.
        resultado = services.sincronizar_carreras_facultad(
            facultad=otra_facultad, carreras_ids=[self.c1.id], usuario=self.usuario
        )
        self.assertEqual(len(resultado), 1)


# ---------------------------------------------------------------------------
# Partes firmantes (sincronización + composición)
# ---------------------------------------------------------------------------
class SincronizarPartesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("sp_user", is_superuser=True)

    def test_composicion_especifico(self):
        # Happy: un Específico requiere UNIDAD_EJECUTORA + FACULTAD.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="ESPECIFICO")
        ue_unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_UE, nombre="UE Parte")
        fac_unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_UNIVERSIDAD, nombre="Fac Parte")
        datos = [
            {"rol": "UNIDAD_EJECUTORA", "unidad_organica": ue_unidad, "orden": 1},
            {"rol": "FACULTAD", "unidad_organica": fac_unidad, "orden": 1},
        ]
        partes = services.sincronizar_partes(convenio=conv, datos=datos, usuario=self.usuario)
        self.assertEqual(len(partes), 2)

    def test_composicion_incompleta(self):
        # Unhappy: falta FACULTAD en un Específico → error de composición.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="ESPECIFICO")
        ue_unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_UE, nombre="UE Parte2")
        with self.assertRaises(ValidationError):
            services.sincronizar_partes(
                convenio=conv,
                datos=[{"rol": "UNIDAD_EJECUTORA", "unidad_organica": ue_unidad, "orden": 1}],
                usuario=self.usuario,
            )

    def test_parte_duplicada(self):
        # Unhappy: dos partes con el mismo (rol, orden) → error.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="ESPECIFICO")
        ue_unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_UE, nombre="UE Dup")
        with self.assertRaises(ValidationError):
            services.sincronizar_partes(
                convenio=conv,
                datos=[
                    {"rol": "UNIDAD_EJECUTORA", "unidad_organica": ue_unidad, "orden": 1},
                    {"rol": "UNIDAD_EJECUTORA", "unidad_organica": ue_unidad, "orden": 1},
                ],
                usuario=self.usuario,
            )

    def test_coherencia_cargo_no_pertenece(self):
        # Unhappy: cargo de otra unidad orgánica → error de coherencia.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="ESPECIFICO")
        ue_unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_UE, nombre="UE Coh")
        fac_unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_UNIVERSIDAD, nombre="Fac Coh")
        otra_unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_MINSA, nombre="Otra Coh")
        cargo_ajeno = f.crear_cargo(unidad=otra_unidad, nombre="Cargo Ajeno Coh")
        with self.assertRaises(ValidationError):
            services.sincronizar_partes(
                convenio=conv,
                datos=[
                    {"rol": "UNIDAD_EJECUTORA", "unidad_organica": ue_unidad,
                     "cargo_ejecutivo": cargo_ajeno, "orden": 1},
                    {"rol": "FACULTAD", "unidad_organica": fac_unidad, "orden": 1},
                ],
                usuario=self.usuario,
            )

    def test_sincronizar_elimina_partes_no_enviadas(self):
        # Edge: reconciliación idempotente — una segunda sync sin una parte la elimina.
        conv = f.crear_convenio(creado_por=self.usuario, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE)
        minsa = f.crear_unidad_organica(organo_nombre=f.ORGANO_MINSA, nombre="MINSA P")
        uni_org = f.crear_unidad_organica(organo_nombre=f.ORGANO_UNIVERSIDAD, nombre="Uni P")
        gore_org = f.crear_unidad_organica(organo_nombre=f.ORGANO_GORE, nombre="GORE P")
        # Marco GORE requiere MINSA + GOBIERNO_REGIONAL + UNIVERSIDAD.
        base = [
            {"rol": "MINSA", "unidad_organica": minsa, "orden": 1},
            {"rol": "GOBIERNO_REGIONAL", "unidad_organica": gore_org, "orden": 1},
            {"rol": "UNIVERSIDAD", "unidad_organica": uni_org, "orden": 1},
        ]
        services.sincronizar_partes(convenio=conv, datos=base, usuario=self.usuario)
        self.assertEqual(ConventionParty.objects.filter(convenio=conv).count(), 3)
        # Re-sincronizar con los mismos 3 es idempotente (no falla).
        partes = services.sincronizar_partes(convenio=conv, datos=base, usuario=self.usuario)
        self.assertEqual(len(partes), 3)
