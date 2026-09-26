"""Pruebas de modelos del módulo Convenios: propiedades derivadas y validaciones de ``clean``."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase

from apps.convenios.models import Ipress, OrganicUnit
from apps.convenios.tests import factories as f


class OrganicUnitCategoriaTests(TestCase):
    """Propiedad derivada ``categoria`` a partir del nombre del ``Organ``."""

    def test_categoria_derivada_de_organo_canonico(self):
        # Happy: el nombre canónico del órgano mapea a la categoría.
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_GORE, nombre="GERESA X")
        self.assertEqual(unidad.categoria, "GOBIERNO_REGIONAL")
        self.assertEqual(unidad.get_categoria_display(), "Gobierno Regional")

    def test_categoria_diris_y_minsa_y_universidad(self):
        # Edge: cada nombre canónico mapea a su categoría.
        diris = f.crear_unidad_organica(organo_nombre=f.ORGANO_DIRIS, nombre="DIRIS LC")
        minsa = f.crear_unidad_organica(organo_nombre=f.ORGANO_MINSA, nombre="DIGEP")
        uni = f.crear_unidad_organica(organo_nombre=f.ORGANO_UNIVERSIDAD, nombre="UNMSM Org")
        ue = f.crear_unidad_organica(organo_nombre=f.ORGANO_UE, nombre="UE 001")
        self.assertEqual(diris.categoria, "MINSA_DIRIS")
        self.assertEqual(minsa.categoria, "ORGANO_MINSA")
        self.assertEqual(uni.categoria, "UNIVERSIDAD")
        self.assertEqual(ue.categoria, "UNIDAD_EJECUTORA")

    def test_categoria_none_para_organo_no_canonico(self):
        # Unhappy: un órgano con nombre no canónico devuelve None (shim histórico).
        organo = f.crear_organo("Órgano Raro No Canónico")
        unidad = OrganicUnit.objects.create(organo=organo, nombre="Rara")
        self.assertIsNone(unidad.categoria)
        self.assertIsNone(unidad.get_categoria_display())

    def test_str(self):
        unidad = f.crear_unidad_organica(nombre="GERESA Str")
        self.assertEqual(str(unidad), "GERESA Str")


class IpressCleanTests(TestCase):
    """Coherencia geográfica microred ↔ ámbito en ``Ipress.clean``."""

    def test_clean_sin_microred_no_valida(self):
        # Happy: sin microred no se valida coherencia.
        ipress = f.crear_ipress()
        ipress.full_clean(exclude=["longitud", "latitud"])

    def test_clean_microred_incoherente(self):
        # Unhappy: microred de otro ámbito → ValidationError.
        ambito_a = f.crear_ambito("A", "Ambito A")
        ambito_b = f.crear_ambito("B", "Ambito B")
        from apps.convenios.models import Microred, Red
        red_b = Red.objects.create(codigo="RED-B", nombre="Red B",
                                   ambito_geografico_sanitario=ambito_b)
        microred = Microred.objects.create(codigo="MR-B", nombre="Microred B", red=red_b)
        ipress = f.crear_ipress(ambito=ambito_a)
        ipress.microred = microred
        with self.assertRaises(DjangoValidationError):
            ipress.clean()

    def test_clean_microred_coherente(self):
        # Edge: microred del mismo ámbito → sin error.
        from apps.convenios.models import Microred, Red
        ambito = f.crear_ambito("C", "Ambito C")
        red = Red.objects.create(codigo="RED-C", nombre="Red C",
                                 ambito_geografico_sanitario=ambito)
        microred = Microred.objects.create(codigo="MR-C", nombre="Microred C", red=red)
        ipress = f.crear_ipress(ambito=ambito)
        ipress.microred = microred
        ipress.clean()  # no lanza


class ModelStrTests(TestCase):
    """`__str__` de modelos clave (cobertura de representación)."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("m_admin", is_superuser=True)

    def test_convention_str(self):
        conv = f.crear_convenio(creado_por=self.admin, titulo="Mi Convenio")
        self.assertEqual(str(conv), "Mi Convenio")

    def test_convention_party_str(self):
        conv = f.crear_convenio(creado_por=self.admin)
        unidad = f.crear_unidad_organica(nombre="Parte UO")
        from apps.convenios.models import ConventionParty
        parte = ConventionParty.objects.create(
            convenio=conv, rol="MINSA", unidad_organica=unidad, orden=1
        )
        self.assertIn("MINSA", str(parte))

    def test_organ_and_university_str(self):
        organo = f.crear_organo(f.ORGANO_MINSA)
        self.assertEqual(str(organo), f.ORGANO_MINSA)
        uni = f.crear_universidad("UNI Str", "UST")
        self.assertEqual(str(uni), "UNI Str")

    def test_representante_str(self):
        uni = f.crear_universidad("UNI Rep", "URP")
        rep = f.crear_representante(entidad=uni, nombre="Rep Nombre")
        self.assertEqual(str(rep), "Rep Nombre")
