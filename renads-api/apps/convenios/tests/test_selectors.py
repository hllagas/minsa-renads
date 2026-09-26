"""Pruebas de selectors del módulo Convenios (lectura, alcance institucional y vigencia)."""

import datetime

from django.test import TestCase

from apps.convenios import selectors
from apps.convenios.models import ConventionParticipant
from apps.convenios.tests import factories as f
from django.contrib.contenttypes.models import ContentType


class ConveniosVisiblesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("s_admin", is_superuser=True)
        cls.uni = f.crear_universidad("Uni Vis", "UVIS")
        cls.otra = f.crear_universidad("Otra Vis", "OVIS")
        cls.usuario = f.crear_usuario("s_uni", grupos=["Universidad"])
        f.dar_ambito(cls.usuario, cls.uni, "Universidad")
        cls.conv_propio = f.crear_convenio(creado_por=cls.admin, universidad=cls.uni,
                                           solicitante=cls.uni, titulo="Propio")
        cls.conv_ajeno = f.crear_convenio(creado_por=cls.admin, universidad=cls.otra,
                                          solicitante=cls.otra, titulo="Ajeno")

    def test_superusuario_ve_todo(self):
        # Happy: el superusuario ve todos los convenios.
        qs = selectors.convenios_visibles(self.admin)
        self.assertEqual(qs.count(), 2)

    def test_usuario_ve_solo_su_ambito_como_solicitante(self):
        # Happy: el usuario ve solo el convenio de su universidad (solicitante).
        qs = selectors.convenios_visibles(self.usuario)
        self.assertEqual(list(qs), [self.conv_propio])

    def test_usuario_sin_perfil_no_ve_nada(self):
        # Unhappy: sin perfiles institucionales no ve ninguno.
        anonimo = f.crear_usuario("s_sinperfil")
        self.assertEqual(selectors.convenios_visibles(anonimo).count(), 0)

    def test_usuario_ve_convenio_donde_participa(self):
        # Edge: aunque no sea solicitante, ve el convenio si su entidad participa.
        ct = ContentType.objects.get_for_model(type(self.uni))
        ConventionParticipant.objects.create(
            convenio=self.conv_ajeno, tipo_contenido=ct, id_objeto=self.uni.id,
            es_firmante=True,
        )
        qs = selectors.convenios_visibles(self.usuario)
        self.assertIn(self.conv_ajeno, qs)
        self.assertIn(self.conv_propio, qs)


class VigenciaEfectivaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("v_admin", is_superuser=True)

    def test_sin_adendas_devuelve_fecha_fin_propia(self):
        # Happy: sin adendas, la vigencia efectiva es la fecha_fin del convenio.
        conv = f.crear_convenio(creado_por=self.admin, fecha_fin=datetime.date(2028, 1, 1))
        self.assertEqual(selectors.vigencia_efectiva(conv), datetime.date(2028, 1, 1))

    def test_adenda_vigente_extiende_vigencia(self):
        # Happy: una adenda vigente con fecha_fin mayor extiende la vigencia efectiva.
        conv = f.crear_convenio(creado_por=self.admin, fecha_fin=datetime.date(2028, 1, 1))
        adenda = f.crear_convenio(
            creado_por=self.admin, universidad=conv.universidad,
            estado_codigo="VIGENTE", titulo="Adenda", fecha_fin=datetime.date(2030, 1, 1),
        )
        adenda.convenio_origen = conv
        adenda.es_adenda = True
        adenda.save()
        self.assertEqual(selectors.vigencia_efectiva(conv), datetime.date(2030, 1, 1))

    def test_adenda_no_vigente_no_extiende(self):
        # Unhappy: adenda en estado no vigente no cuenta para la vigencia efectiva.
        conv = f.crear_convenio(creado_por=self.admin, fecha_fin=datetime.date(2028, 1, 1))
        adenda = f.crear_convenio(
            creado_por=self.admin, universidad=conv.universidad,
            estado_codigo="SOLICITUD_REGISTRADA", titulo="Adenda2",
            fecha_fin=datetime.date(2031, 1, 1),
        )
        adenda.convenio_origen = conv
        adenda.es_adenda = True
        adenda.save()
        self.assertEqual(selectors.vigencia_efectiva(conv), datetime.date(2028, 1, 1))


class CamposClinicosSelectorsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("cc_admin", is_superuser=True)

    def test_registros_y_asignaciones_queryset(self):
        # Happy: los selectors devuelven querysets con las FKs precargadas.
        reg = f.crear_registro_campo_clinico()
        conv = f.crear_convenio(creado_por=self.admin)
        f.crear_asignacion_campo_clinico(convenio=conv, registro=reg,
                                         ipress=reg.ipress, carrera=reg.carrera_profesional)
        self.assertIn(reg, selectors.registros_campo_clinico())
        self.assertEqual(selectors.asignaciones_campo_clinico().count(), 1)

    def test_campos_clinicos_del_especifico(self):
        # Happy: filtra los registros de la UE del convenio por carreras de la facultad.
        uni = f.crear_universidad("Uni CC", "UCC")
        facultad = f.crear_facultad(universidad=uni)
        carrera = f.crear_carrera("Enfermería CC")
        f.crear_universidad_carrera(universidad=uni, carrera=carrera, facultad=facultad)
        ue = f.crear_unidad_ejecutora(codigo="9001", nombre="UE CC")
        ipress = f.crear_ipress(codigo="90010001", unidad_ejecutora=ue, es_sede_docente=True)
        reg = f.crear_registro_campo_clinico(ipress=ipress, carrera=carrera)
        conv = f.crear_convenio(
            creado_por=self.admin, universidad=uni, tipo_codigo="ESPECIFICO",
            unidad_ejecutora=ue, facultad=facultad,
        )
        resultado = list(selectors.campos_clinicos_del_especifico(conv))
        self.assertEqual(resultado, [reg])

    def test_campos_clinicos_excluye_carreras_de_otra_facultad(self):
        # Unhappy: un registro con carrera no ligada a la facultad no aparece.
        uni = f.crear_universidad("Uni CC2", "UCC2")
        facultad = f.crear_facultad(universidad=uni)
        ue = f.crear_unidad_ejecutora(codigo="9002", nombre="UE CC2")
        ipress = f.crear_ipress(codigo="90020001", unidad_ejecutora=ue)
        otra_carrera = f.crear_carrera("Odontología CC2")
        f.crear_registro_campo_clinico(ipress=ipress, carrera=otra_carrera)
        conv = f.crear_convenio(
            creado_por=self.admin, universidad=uni, tipo_codigo="ESPECIFICO",
            unidad_ejecutora=ue, facultad=facultad,
        )
        self.assertEqual(list(selectors.campos_clinicos_del_especifico(conv)), [])


class DocumentosYParticipantesSelectorsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("dp_admin", is_superuser=True)

    def test_participantes_de(self):
        conv = f.crear_convenio(creado_por=self.admin)
        ct = ContentType.objects.get_for_model(type(conv.universidad))
        ConventionParticipant.objects.create(
            convenio=conv, tipo_contenido=ct, id_objeto=conv.universidad.id,
        )
        self.assertEqual(selectors.participantes_de(conv).count(), 1)

    def test_historial_convenio_ordenado(self):
        conv = f.crear_convenio(creado_por=self.admin)
        from apps.convenios.models import ConventionStatusHistory
        ConventionStatusHistory.objects.create(
            convenio=conv, estado=f.estado_convenio("VIGENTE"), cambiado_por=self.admin,
        )
        self.assertGreaterEqual(selectors.historial_convenio(conv).count(), 1)

    def test_documentos_de_vacio(self):
        # Edge: un objeto sin documentos devuelve queryset vacío.
        conv = f.crear_convenio(creado_por=self.admin)
        self.assertEqual(selectors.documentos_de(conv).count(), 0)
