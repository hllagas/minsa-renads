"""Pruebas de services del módulo Internados: reglas de negocio (RN) de escritura.

Cubre crear_internado (RN-2/3/4/6/13/21), aprovisionamiento del interno (RN-22),
declaraciones juradas (RN-23), tutor (RN-24, cambio), rotaciones (RN-8/9/11/12),
autorización (RN-10), prelación (RN-18), RN-19 y helpers de resolución de la trama.
"""

import datetime
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.common.models import UserProfile, UserSecurity
from apps.convenios.models import Document, UserEntityProfile
from apps.internados import services
from apps.internados.models import (
    Internship,
    InternshipStatusHistory,
    Rotation,
    RotationStatusHistory,
    TutorConvenio,
    TutorHistory,
)
from apps.internados.tests import factories as f


# ---------------------------------------------------------------------------
# RN-24 — validar_universidades_tutor
# ---------------------------------------------------------------------------
class ValidarUniversidadesTutorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u1 = f.crear_universidad("U1", "INEI1")
        cls.u2 = f.crear_universidad("U2", "INEI2")

    def test_happy_una_universidad(self):
        # No lanza con una universidad.
        services.validar_universidades_tutor([self.u1])

    def test_unhappy_vacia(self):
        with self.assertRaises(ValidationError):
            services.validar_universidades_tutor([])

    def test_unhappy_excede_tope(self):
        # Edge: más de MAX_UNIVERSIDADES_TUTOR (5) universidades.
        unis = [f.crear_universidad(f"U{i}", f"INEI{i}") for i in range(6)]
        with self.assertRaises(ValidationError):
            services.validar_universidades_tutor(unis)

    def test_unhappy_repetidas(self):
        with self.assertRaises(ValidationError):
            services.validar_universidades_tutor([self.u1, self.u1])


# ---------------------------------------------------------------------------
# TutorConvenio (RN-TC-01/02)
# ---------------------------------------------------------------------------
class CrearTutorConvenioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("tc_svc")
        cls.especifico = f.crear_convenio(creado_por=cls.user, tipo_codigo="ESPECIFICO")
        cls.marco = f.crear_convenio(creado_por=cls.user, tipo_codigo="MARCO", titulo="Marco X")
        cls.ipress = f.crear_ipress()
        cls.tutor = f.crear_tutor(universidades=[cls.especifico.universidad])

    def test_happy_crea_vinculo(self):
        tc = services.crear_tutor_convenio(
            tutor=self.tutor, convenio=self.especifico, ipress=self.ipress, usuario=self.user
        )
        self.assertIsInstance(tc, TutorConvenio)

    def test_unhappy_convenio_no_especifico(self):
        # RN-TC-01: solo Convenios Específicos.
        with self.assertRaises(ValidationError):
            services.crear_tutor_convenio(
                tutor=self.tutor, convenio=self.marco, ipress=self.ipress, usuario=self.user
            )

    def test_unhappy_duplicado(self):
        # RN-TC-02: (tutor, convenio) único.
        services.crear_tutor_convenio(
            tutor=self.tutor, convenio=self.especifico, ipress=self.ipress, usuario=self.user
        )
        with self.assertRaises(ValidationError):
            services.crear_tutor_convenio(
                tutor=self.tutor, convenio=self.especifico, ipress=self.ipress, usuario=self.user
            )

    def test_eliminar_vinculo(self):
        tc = services.crear_tutor_convenio(
            tutor=self.tutor, convenio=self.especifico, ipress=self.ipress, usuario=self.user
        )
        services.eliminar_tutor_convenio(tutor_convenio=tc, usuario=self.user)
        self.assertFalse(TutorConvenio.objects.filter(pk=tc.pk).exists())


# ---------------------------------------------------------------------------
# RN-19 — validar_regla_periodo_especialidad
# ---------------------------------------------------------------------------
class ReglaPeriodoEspecialidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nivel_pre = f.crear_nivel("PREGRADO", "Pregrado")
        cls.nivel_esp = f.crear_nivel("SEGUNDA_ESPECIALIDAD", "Segunda especialidad")
        cls.carrera_pre = f.crear_carrera("Medicina", cls.nivel_pre)
        cls.carrera_esp = f.crear_carrera("Cardiología", cls.nivel_esp)
        cls.periodo = f.crear_periodo()
        cls.especialidad = f.crear_especialidad()

    def test_pregrado_happy(self):
        services.validar_regla_periodo_especialidad(
            carrera=self.carrera_pre, periodo_internado=self.periodo, especialidad=None
        )

    def test_pregrado_sin_periodo(self):
        with self.assertRaises(ValidationError):
            services.validar_regla_periodo_especialidad(
                carrera=self.carrera_pre, periodo_internado=None, especialidad=None
            )

    def test_pregrado_con_especialidad_sobrante(self):
        with self.assertRaises(ValidationError):
            services.validar_regla_periodo_especialidad(
                carrera=self.carrera_pre, periodo_internado=self.periodo, especialidad=self.especialidad
            )

    def test_no_pregrado_happy(self):
        services.validar_regla_periodo_especialidad(
            carrera=self.carrera_esp, periodo_internado=None, especialidad=self.especialidad
        )

    def test_no_pregrado_sin_especialidad(self):
        with self.assertRaises(ValidationError):
            services.validar_regla_periodo_especialidad(
                carrera=self.carrera_esp, periodo_internado=None, especialidad=None
            )

    def test_no_pregrado_con_periodo_sobrante(self):
        with self.assertRaises(ValidationError):
            services.validar_regla_periodo_especialidad(
                carrera=self.carrera_esp, periodo_internado=self.periodo, especialidad=self.especialidad
            )


# ---------------------------------------------------------------------------
# crear_internado (RN-2/3/4/6/13/21) + aprovisionamiento (RN-22)
# ---------------------------------------------------------------------------
class CrearInternadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("crea_int")
        Group.objects.get_or_create(name="Interno")
        # Estados necesarios en el flujo.
        f.crear_estado_internado("REGISTRADO")
        cls.ambito = f.crear_ambito()
        cls.ue = f.crear_unidad_ejecutora(ambito=cls.ambito)
        cls.ipress = f.crear_ipress(ambito=cls.ambito, unidad_ejecutora=cls.ue)
        cls.universidad = f.crear_universidad()
        cls.convenio = f.crear_convenio(creado_por=cls.user, universidad=cls.universidad)
        cls.carrera = f.crear_carrera()
        cls.campo = f.crear_asignacion_campo_clinico(
            convenio=cls.convenio, universidad=cls.universidad, ipress=cls.ipress,
            carrera=cls.carrera, autorizados=2,
        )
        cls.tutor = f.crear_tutor(universidades=[cls.universidad])

    def _datos(self, **overrides):
        estudiante = overrides.pop("estudiante", None) or f.crear_estudiante(
            creado_por=self.user, universidad=self.universidad, carrera=self.carrera,
            numero_documento=overrides.pop("dni", "20304050"),
        )
        datos = {
            "estudiante": estudiante,
            "convenio": self.convenio,
            "campo_clinico": self.campo,
            "ipress": self.ipress,
            "tutor": self.tutor,
            "fecha_inicio": datetime.date(2026, 3, 1),
            "fecha_fin": datetime.date(2026, 9, 1),
        }
        datos.update(overrides)
        return datos

    def test_happy_crea_internado_y_aprovisiona(self):
        # Happy: crea internado REGISTRADO, historial, usuario Interno y perfil.
        datos = self._datos(dni="20304051")
        internado = services.crear_internado(datos=datos, usuario=self.user)
        self.assertEqual(internado.estado_actual.codigo, "REGISTRADO")
        self.assertEqual(internado.estado_declaraciones, "PENDIENTE")
        self.assertTrue(InternshipStatusHistory.objects.filter(interno=internado).exists())
        # RN-22: usuario Interno creado con debe_cambiar_password.
        interno_user = User.objects.get(username="20304051")
        self.assertTrue(interno_user.groups.filter(name="Interno").exists())
        self.assertTrue(UserSecurity.objects.get(usuario=interno_user).debe_cambiar_password)
        self.assertTrue(UserProfile.objects.filter(usuario=interno_user).exists())

    def test_happy_deriva_ambito_de_la_sede(self):
        internado = services.crear_internado(datos=self._datos(dni="20304052"), usuario=self.user)
        self.assertEqual(internado.ambito_geografico_sanitario_id, self.ambito.id)

    def test_unhappy_convenio_no_especifico(self):
        marco = f.crear_convenio(creado_por=self.user, tipo_codigo="MARCO", titulo="Marco Y",
                                 universidad=self.universidad)
        datos = self._datos(dni="20304053", convenio=marco)
        with self.assertRaises(ValidationError):
            services.crear_internado(datos=datos, usuario=self.user)

    def test_unhappy_convenio_no_vigente(self):
        no_vig = f.crear_convenio(creado_por=self.user, estado_codigo="SOLICITUD_REGISTRADA",
                                  universidad=self.universidad, titulo="No vigente")
        campo = f.crear_asignacion_campo_clinico(
            convenio=no_vig, universidad=self.universidad, ipress=self.ipress, carrera=self.carrera,
        )
        datos = self._datos(dni="20304054", convenio=no_vig, campo_clinico=campo)
        with self.assertRaises(ValidationError):
            services.crear_internado(datos=datos, usuario=self.user)

    def test_unhappy_campo_de_otro_convenio(self):
        otro = f.crear_convenio(creado_por=self.user, universidad=self.universidad, titulo="Otro")
        campo_otro = f.crear_asignacion_campo_clinico(
            convenio=otro, universidad=self.universidad, ipress=self.ipress, carrera=self.carrera,
        )
        datos = self._datos(dni="20304055", campo_clinico=campo_otro)
        with self.assertRaises(ValidationError):
            services.crear_internado(datos=datos, usuario=self.user)

    def test_unhappy_duracion_mayor_a_un_anio(self):
        datos = self._datos(dni="20304056", fecha_fin=datetime.date(2027, 4, 1))
        with self.assertRaises(ValidationError):
            services.crear_internado(datos=datos, usuario=self.user)

    def test_unhappy_fecha_fin_anterior(self):
        datos = self._datos(dni="20304057", fecha_inicio=datetime.date(2026, 9, 1),
                            fecha_fin=datetime.date(2026, 3, 1))
        with self.assertRaises(ValidationError):
            services.crear_internado(datos=datos, usuario=self.user)

    def test_unhappy_ambito_enviado_no_coincide(self):
        otro_ambito = f.crear_ambito("AMB-2", "Cusco")
        datos = self._datos(dni="20304058", ambito_geografico_sanitario=otro_ambito)
        with self.assertRaises(ValidationError):
            services.crear_internado(datos=datos, usuario=self.user)

    def test_unhappy_max_campos_autorizados(self):
        # RN-13: campo con 2 autorizados; el 3er internado debe rechazarse.
        services.crear_internado(datos=self._datos(dni="30001"), usuario=self.user)
        services.crear_internado(datos=self._datos(dni="30002"), usuario=self.user)
        with self.assertRaises(ValidationError):
            services.crear_internado(datos=self._datos(dni="30003"), usuario=self.user)

    def test_unhappy_internado_vigente_duplicado(self):
        # RN-21: un estudiante con internado vigente no puede tener otro.
        estudiante = f.crear_estudiante(creado_por=self.user, universidad=self.universidad,
                                        carrera=self.carrera, numero_documento="40001")
        services.crear_internado(datos=self._datos(estudiante=estudiante), usuario=self.user)
        with self.assertRaises(ValidationError):
            services.crear_internado(datos=self._datos(estudiante=estudiante), usuario=self.user)

    def test_email_best_effort_se_envia_on_commit(self):
        # RN-22: correo best-effort tras commit (captura vía locmem).
        with self.captureOnCommitCallbacks(execute=True):
            services.crear_internado(datos=self._datos(dni="50001", ), usuario=self.user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Registro como interno", mail.outbox[0].subject)


# ---------------------------------------------------------------------------
# RN-21 — tiene_internado_vigente
# ---------------------------------------------------------------------------
class TieneInternadoVigenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("vig")

    def test_bloqueante(self):
        f.crear_estado_internado("ACTIVO")
        internado = f.crear_internado(creado_por=self.user,
                                      estado=f.crear_estado_internado("ACTIVO"))
        self.assertTrue(services.tiene_internado_vigente(internado.estudiante))

    def test_liberador_no_bloquea(self):
        estado = f.crear_estado_internado("CULMINADO")
        internado = f.crear_internado(creado_por=self.user, estado=estado)
        self.assertFalse(services.tiene_internado_vigente(internado.estudiante))


# ---------------------------------------------------------------------------
# RN-22 — aprovisionar_interno (reingreso idempotente) y perfil
# ---------------------------------------------------------------------------
class AprovisionarInternoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("aprov")
        Group.objects.get_or_create(name="Interno")

    def test_reingreso_reutiliza_usuario(self):
        # Edge: aprovisionar dos veces reutiliza el mismo User (idempotente).
        internado = f.crear_internado(creado_por=self.user)
        u1 = services.aprovisionar_interno(internado, self.user)
        u2 = services.aprovisionar_interno(internado, self.user)
        self.assertEqual(u1.pk, u2.pk)
        self.assertEqual(UserProfile.objects.filter(usuario=u1).count(), 1)

    def test_mapear_tipo_documento_dni(self):
        internado = f.crear_internado(creado_por=self.user)
        codigo = services._mapear_tipo_documento_interno(internado.estudiante)
        self.assertEqual(codigo, "DNI")

    def test_mapear_tipo_documento_fallback_ce(self):
        # Documento de 9 dígitos con tipo no mapeable → CE.
        tipo = f.crear_tipo_documento("XX", "Desconocido")
        est = f.crear_estudiante(creado_por=self.user, tipo_documento=tipo,
                                 numero_documento="123456789")
        self.assertEqual(services._mapear_tipo_documento_interno(est), "CE")

    def test_telefono_unico_sintetico_si_colisiona(self):
        # Edge: si el teléfono ya está tomado, se genera uno sintético.
        unidad, cargo = services._obtener_placeholders_no_aplica()
        otro_user = f.crear_usuario("otro_tel")
        UserProfile.objects.create(
            usuario=otro_user, tipo_documento="DNI", numero_documento="99999999",
            telefono="999111222", unidad_organica=unidad, cargo=cargo,
        )
        generado = services._generar_telefono_perfil_unico("999111222")
        self.assertNotEqual(generado, "999111222")
        self.assertTrue(generado.startswith("9"))
        self.assertEqual(len(generado), 9)

    def test_telefono_usa_el_real_si_libre(self):
        generado = services._generar_telefono_perfil_unico("987654321")
        self.assertEqual(generado, "987654321")


# ---------------------------------------------------------------------------
# RN-22 — notificar_registro_interno
# ---------------------------------------------------------------------------
class NotificarRegistroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("notif")

    def test_sin_correo_no_envia(self):
        internado = f.crear_internado(
            creado_por=self.user,
            estudiante=f.crear_estudiante(creado_por=self.user, correo=""),
        )
        self.assertFalse(services.notificar_registro_interno(internado))
        self.assertEqual(len(mail.outbox), 0)

    def test_con_correo_envia(self):
        internado = f.crear_internado(creado_por=self.user)
        self.assertTrue(services.notificar_registro_interno(internado))
        self.assertEqual(len(mail.outbox), 1)

    def test_fallo_envio_no_propaga(self):
        internado = f.crear_internado(creado_por=self.user)
        with mock.patch("apps.internados.services.send_mail", side_effect=RuntimeError("smtp")):
            self.assertFalse(services.notificar_registro_interno(internado))


# ---------------------------------------------------------------------------
# RN-23 — Declaraciones juradas
# ---------------------------------------------------------------------------
class DeclaracionesJuradasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("dj")
        cls.internado = f.crear_internado(creado_por=cls.user)

    def test_sin_obligatorios_completas(self):
        # Edge: sin DJ obligatorias en el catálogo → recálculo marca COMPLETAS.
        from apps.internados.models import AnnexDocument
        AnnexDocument.objects.filter(tipo_actor="INTERNO", obligatorio=True).update(obligatorio=False)
        services.recalcular_estado_declaraciones(self.internado, usuario=self.user)
        self.internado.refresh_from_db()
        self.assertEqual(self.internado.estado_declaraciones, "COMPLETAS")

    def test_con_obligatorio_pendiente_hasta_adjuntar(self):
        from apps.internados.models import AnnexDocument
        # Deja un único obligatorio activo del actor INTERNO para un flujo controlado.
        AnnexDocument.objects.filter(tipo_actor="INTERNO").update(obligatorio=False, activo=False)
        anexo = AnnexDocument.objects.create(
            codigo="DJ-1", nombre="DJ veracidad", tipo_actor="INTERNO",
            obligatorio=True, activo=True,
        )
        services.recalcular_estado_declaraciones(self.internado, usuario=self.user)
        self.internado.refresh_from_db()
        self.assertEqual(self.internado.estado_declaraciones, "PENDIENTE")
        # Adjuntar el Document ACTIVO del anexo → COMPLETAS.
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Internship)
        Document.objects.create(
            tipo_contenido=ct, id_objeto=self.internado.pk, referencia_externa="k",
            estado="ACTIVO", documento_anexo=anexo, cargado_por=self.user,
        )
        services.recalcular_estado_declaraciones(self.internado, usuario=self.user)
        self.internado.refresh_from_db()
        self.assertEqual(self.internado.estado_declaraciones, "COMPLETAS")

    def test_no_degrada_validadas(self):
        self.internado.estado_declaraciones = "VALIDADAS"
        self.internado.save(update_fields=["estado_declaraciones"])
        services.recalcular_estado_declaraciones(self.internado, usuario=self.user)
        self.internado.refresh_from_db()
        self.assertEqual(self.internado.estado_declaraciones, "VALIDADAS")

    def test_revisar_validadas_happy(self):
        self.internado.estado_declaraciones = "COMPLETAS"
        self.internado.save(update_fields=["estado_declaraciones"])
        services.revisar_declaraciones(
            internado=self.internado, resultado="VALIDADAS", usuario=self.user
        )
        self.internado.refresh_from_db()
        self.assertEqual(self.internado.estado_declaraciones, "VALIDADAS")

    def test_revisar_resultado_invalido(self):
        self.internado.estado_declaraciones = "COMPLETAS"
        self.internado.save(update_fields=["estado_declaraciones"])
        with self.assertRaises(ValidationError):
            services.revisar_declaraciones(
                internado=self.internado, resultado="XXX", usuario=self.user
            )

    def test_revisar_estado_no_completas(self):
        # Unhappy: en PENDIENTE no se puede revisar.
        with self.assertRaises(ValidationError):
            services.revisar_declaraciones(
                internado=self.internado, resultado="VALIDADAS", usuario=self.user
            )


# ---------------------------------------------------------------------------
# cambiar_estado_internado (RN-23 gate ACTIVO) y actualizar_internado
# ---------------------------------------------------------------------------
class CambiarEstadoInternadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("cei")
        f.crear_estado_internado("REGISTRADO")
        f.crear_estado_internado("ACTIVO")
        f.crear_estado_internado("VALIDADO")
        cls.internado = f.crear_internado(creado_por=cls.user)

    def test_activo_sin_validadas_falla(self):
        with self.assertRaises(ValidationError):
            services.cambiar_estado_internado(
                internado=self.internado, nuevo_estado_codigo="ACTIVO", usuario=self.user
            )

    def test_activo_con_validadas_ok(self):
        self.internado.estado_declaraciones = "VALIDADAS"
        self.internado.save(update_fields=["estado_declaraciones"])
        internado = services.cambiar_estado_internado(
            internado=self.internado, nuevo_estado_codigo="ACTIVO", usuario=self.user
        )
        self.assertEqual(internado.estado_actual.codigo, "ACTIVO")

    def test_estado_inexistente(self):
        with self.assertRaises(ValidationError):
            services.cambiar_estado_internado(
                internado=self.internado, nuevo_estado_codigo="NO_EXISTE", usuario=self.user
            )


class ActualizarInternadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("act_int")
        cls.internado = f.crear_internado(creado_por=cls.user)

    def test_actualiza_observaciones(self):
        services.actualizar_internado(
            internado=self.internado, datos={"observaciones": "nota"}, usuario=self.user
        )
        self.internado.refresh_from_db()
        self.assertEqual(self.internado.observaciones, "nota")

    def test_periodo_invalido(self):
        with self.assertRaises(ValidationError):
            services.actualizar_internado(
                internado=self.internado,
                datos={"fecha_inicio": datetime.date(2026, 9, 1),
                       "fecha_fin": datetime.date(2026, 3, 1)},
                usuario=self.user,
            )

    def test_ipress_fuera_de_ambito(self):
        otro_ambito = f.crear_ambito("AMB-9", "Otro")
        otra_ipress = f.crear_ipress(codigo="99999999", ambito=otro_ambito)
        with self.assertRaises(ValidationError):
            services.actualizar_internado(
                internado=self.internado, datos={"ipress": otra_ipress}, usuario=self.user
            )


# ---------------------------------------------------------------------------
# cambiar_tutor (RN-14)
# ---------------------------------------------------------------------------
class CambiarTutorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("ct")
        cls.internado = f.crear_internado(creado_por=cls.user)

    def test_registra_historial_y_cambia(self):
        nuevo = f.crear_tutor(numero_documento="55667788",
                              universidades=[self.internado.estudiante.universidad])
        services.cambiar_tutor(
            internado=self.internado,
            datos={"tutor": nuevo, "fecha_cambio": datetime.date(2026, 4, 1), "motivo": "cambio"},
            usuario=self.user,
        )
        self.internado.refresh_from_db()
        self.assertEqual(self.internado.tutor_id, nuevo.id)
        self.assertTrue(TutorHistory.objects.filter(interno=self.internado, tutor=nuevo).exists())


# ---------------------------------------------------------------------------
# Rotaciones (RN-8/9/10/11/12)
# ---------------------------------------------------------------------------
class RotacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("rot")
        f.crear_estado_rotacion("SOLICITADA")
        f.crear_estado_rotacion("AUTORIZADA")
        f.crear_estado_rotacion("OBSERVADA")
        f.crear_estado_rotacion("RECHAZADA")
        f.crear_estado_rotacion("EN_CURSO")
        cls.ambito = f.crear_ambito()
        cls.internado = f.crear_internado(
            creado_por=cls.user, ambito=cls.ambito,
            fecha_inicio=datetime.date(2026, 3, 1), fecha_fin=datetime.date(2026, 9, 1),
        )
        cls.origen = f.crear_ipress(codigo="10000001", ambito=cls.ambito)
        cls.destino = f.crear_ipress(codigo="10000002", ambito=cls.ambito)
        cls.servicio = f.crear_servicio_area()

    def _datos(self, **over):
        datos = {
            "ipress_origen": self.origen, "ipress_destino": self.destino,
            "servicio_area": self.servicio,
            "fecha_inicio": datetime.date(2026, 4, 1), "fecha_fin": datetime.date(2026, 5, 1),
        }
        datos.update(over)
        return datos

    def test_crear_rotacion_happy(self):
        rot = services.crear_rotacion(internado=self.internado, datos=self._datos(), usuario=self.user)
        self.assertEqual(rot.numero_rotacion, 1)
        self.assertEqual(rot.estado_actual.codigo, "SOLICITADA")

    def test_rotacion_ambito_distinto(self):
        otro = f.crear_ipress(codigo="20000001", ambito=f.crear_ambito("AMB-X", "X"))
        with self.assertRaises(ValidationError):
            services.crear_rotacion(
                internado=self.internado, datos=self._datos(ipress_destino=otro), usuario=self.user
            )

    def test_rotacion_fechas_fuera_de_periodo(self):
        with self.assertRaises(ValidationError):
            services.crear_rotacion(
                internado=self.internado,
                datos=self._datos(fecha_inicio=datetime.date(2026, 1, 1)),
                usuario=self.user,
            )

    def test_max_rotaciones(self):
        # RN-9: máximo 4 rotaciones.
        for _ in range(4):
            services.crear_rotacion(internado=self.internado, datos=self._datos(), usuario=self.user)
        with self.assertRaises(ValidationError):
            services.crear_rotacion(internado=self.internado, datos=self._datos(), usuario=self.user)

    def test_autorizar_rotacion_happy(self):
        rot = services.crear_rotacion(internado=self.internado, datos=self._datos(), usuario=self.user)
        participante = f.crear_participante(convenio=self.internado.convenio, es_firmante=True)
        services.autorizar_rotacion(
            rotacion=rot,
            datos={"participante_convenio": participante, "resultado": "APROBADO",
                   "fecha_autorizacion": datetime.date(2026, 4, 2)},
            usuario=self.user,
        )
        rot.refresh_from_db()
        self.assertEqual(rot.estado_actual.codigo, "AUTORIZADA")

    def test_autorizar_participante_no_firmante(self):
        rot = services.crear_rotacion(internado=self.internado, datos=self._datos(), usuario=self.user)
        participante = f.crear_participante(convenio=self.internado.convenio, es_firmante=False)
        with self.assertRaises(ValidationError):
            services.autorizar_rotacion(
                rotacion=rot,
                datos={"participante_convenio": participante, "resultado": "APROBADO",
                       "fecha_autorizacion": datetime.date(2026, 4, 2)},
                usuario=self.user,
            )

    def test_iniciar_sin_autorizacion_aprobada(self):
        # RN-11: no inicia sin autorización APROBADO.
        rot = services.crear_rotacion(internado=self.internado, datos=self._datos(), usuario=self.user)
        with self.assertRaises(ValidationError):
            services.iniciar_rotacion(rotacion=rot, usuario=self.user)

    def test_iniciar_con_autorizacion(self):
        rot = services.crear_rotacion(internado=self.internado, datos=self._datos(), usuario=self.user)
        participante = f.crear_participante(convenio=self.internado.convenio, es_firmante=True)
        services.autorizar_rotacion(
            rotacion=rot,
            datos={"participante_convenio": participante, "resultado": "APROBADO",
                   "fecha_autorizacion": datetime.date(2026, 4, 2)},
            usuario=self.user,
        )
        rot = services.iniciar_rotacion(rotacion=rot, usuario=self.user)
        self.assertEqual(rot.estado_actual.codigo, "EN_CURSO")

    def test_cambiar_estado_rotacion(self):
        rot = services.crear_rotacion(internado=self.internado, datos=self._datos(), usuario=self.user)
        services.cambiar_estado_rotacion(
            rotacion=rot, nuevo_estado_codigo="OBSERVADA", usuario=self.user
        )
        rot.refresh_from_db()
        self.assertEqual(rot.estado_actual.codigo, "OBSERVADA")
        self.assertTrue(RotationStatusHistory.objects.filter(rotacion=rot).exists())


# ---------------------------------------------------------------------------
# RN-18 — prelación
# ---------------------------------------------------------------------------
class PrelacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("prel")
        cls.uni = f.crear_universidad()

    def test_orden_por_nota_desc_nulos_al_final(self):
        from apps.internados.models import Student
        f.crear_estudiante(creado_por=self.user, universidad=self.uni, numero_documento="1",
                           nombres="A")
        alto = f.crear_estudiante(creado_por=self.user, universidad=self.uni, numero_documento="2",
                                  nombres="B")
        alto.nota_promedio_ponderado = 18
        alto.save()
        medio = f.crear_estudiante(creado_por=self.user, universidad=self.uni, numero_documento="3",
                                   nombres="C")
        medio.nota_promedio_ponderado = 15
        medio.save()
        qs = services.estudiantes_por_prelacion(Student.objects.all())
        notas = [e.nota_promedio_ponderado for e in qs]
        self.assertEqual(notas[0], 18)
        self.assertEqual(notas[1], 15)
        self.assertIsNone(notas[2])


# ---------------------------------------------------------------------------
# Helpers de resolución de la trama (RN-16)
# ---------------------------------------------------------------------------
class ResolversTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dni = f.crear_tipo_documento("DNI", "DNI")
        cls.padre = f.crear_parentesco("PADRE", "Padre")
        cls.uni = f.crear_universidad("UPrueba", "INEIR")
        cls.esp = f.crear_especialidad("ESP-1", "Cardiología")
        cls.periodo = f.crear_periodo("2026-I", "2026-I")

    def test_parse_fecha_formatos(self):
        self.assertEqual(services._parse_fecha("15/04/1998"), datetime.date(1998, 4, 15))
        self.assertEqual(services._parse_fecha("1998-04-15"), datetime.date(1998, 4, 15))
        self.assertIsNone(services._parse_fecha(None))

    def test_parse_fecha_invalida(self):
        with self.assertRaises(ValidationError):
            services._parse_fecha("no-fecha")

    def test_resolver_universidad_por_id_y_inei(self):
        self.assertEqual(services._resolver_universidad(str(self.uni.id)), self.uni)
        self.assertEqual(services._resolver_universidad("INEIR"), self.uni)

    def test_resolver_universidad_inexistente(self):
        with self.assertRaises(ValidationError):
            services._resolver_universidad("9999")

    def test_resolver_tipo_documento_por_codigo(self):
        self.assertEqual(services._resolver_tipo_documento("DNI"), self.dni)

    def test_resolver_tipo_documento_requerido(self):
        with self.assertRaises(ValidationError):
            services._resolver_tipo_documento(None)

    def test_resolver_periodo_normaliza_semestre(self):
        # `2026-01` → `2026-I`.
        self.assertEqual(services._resolver_periodo_internado("2026-01"), self.periodo)

    def test_resolver_periodo_none(self):
        self.assertIsNone(services._resolver_periodo_internado(None))

    def test_resolver_especialidad_por_codigo(self):
        self.assertEqual(services._resolver_especialidad("ESP-1"), self.esp)

    def test_resolver_parentesco_por_nombre(self):
        self.assertEqual(services._resolver_parentesco("Padre"), self.padre)

    def test_normalizar_codigo_periodo_sin_patron(self):
        self.assertEqual(services._normalizar_codigo_periodo("2026-I"), "2026-I")

    def test_resolver_carrera_no_pregrado(self):
        nivel = f.crear_nivel("MAESTRIA", "Maestría")
        carrera = f.crear_carrera("Cardiología", nivel)
        self.assertEqual(services._resolver_carrera_no_pregrado("Cardiología"), carrera)

    def test_resolver_carrera_no_pregrado_inexistente(self):
        with self.assertRaises(ValidationError):
            services._resolver_carrera_no_pregrado("Inexistente XYZ")


# ---------------------------------------------------------------------------
# crear_estudiantes_validados (all-or-nothing) — RN-16
# ---------------------------------------------------------------------------
class CrearEstudiantesValidadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("bulk")
        cls.uni = f.crear_universidad()
        cls.dni = f.crear_tipo_documento()
        cls.carrera = f.crear_carrera()

    def test_crea_todos(self):
        validos = [
            (2, {"tipo_documento_identidad": self.dni, "numero_documento": "70000001",
                 "nombres": "A", "apellido_paterno": "X", "carrera_profesional": self.carrera}),
            (3, {"tipo_documento_identidad": self.dni, "numero_documento": "70000002",
                 "nombres": "B", "apellido_paterno": "Y", "carrera_profesional": self.carrera}),
        ]
        creados = services.crear_estudiantes_validados(
            validos=validos, usuario=self.user, universidad=self.uni
        )
        self.assertEqual(creados, 2)


class MensajeErrorTests(TestCase):
    def test_dict(self):
        exc = ValidationError({"campo": ["mensaje"]})
        self.assertIn("campo", services._mensaje_error(exc))

    def test_lista(self):
        exc = ValidationError(["e1", "e2"])
        self.assertIn("e1", services._mensaje_error(exc))

    def test_string(self):
        exc = ValidationError("solo texto")
        self.assertIn("solo texto", services._mensaje_error(exc))


class ValidarTramaExcepcionTests(TestCase):
    def test_archivo_corrupto(self):
        import io as _io
        user = f.crear_usuario("trama_corr", is_superuser=True)
        uni = f.crear_universidad()
        with self.assertRaises(ValidationError):
            services.validar_trama_estudiantes(
                archivo=_io.BytesIO(b"no es xlsx"), usuario=user, universidad=uni
            )
