"""Seed de catálogos `especialidad` y `ambito_geografico_sanitario` con valores oficiales.

Fuentes:
- Especialidades: Nomenclatura oficial CONAREME (Sistema Nacional de Residentado Médico).
  Nota: "Cirugía de Cabeza y Cuello" se registra con su denominación vigente
  "Cirugía de Cabeza, Cuello y Maxilofacial" (Acuerdo N° 037-CONAREME-2019).
- Ámbito geográfico sanitario: jurisdicciones de las autoridades sanitarias regionales del
  MINSA — una por región (DIRESA/GERESA) + DIRESA Callao + las 4 DIRIS de Lima Metropolitana.
"""

from django.db import migrations


# (código, nombre) — 46 especialidades médicas oficiales CONAREME
SPECIALTIES = [
    ("ADMINISTRACION_GESTION_SALUD", "Administración y Gestión en Salud"),
    ("ADOLESCENTOLOGIA", "Adolescentología"),
    ("ANATOMIA_PATOLOGICA", "Anatomía Patológica"),
    ("ANESTESIOLOGIA", "Anestesiología"),
    ("CARDIOLOGIA", "Cardiología"),
    ("CIRUGIA_CABEZA_CUELLO_MAXILOFACIAL", "Cirugía de Cabeza, Cuello y Maxilofacial"),
    ("CIRUGIA_TORAX_CARDIOVASCULAR", "Cirugía de Tórax y Cardiovascular"),
    ("CIRUGIA_GENERAL", "Cirugía General"),
    ("CIRUGIA_ONCOLOGICA", "Cirugía Oncológica"),
    ("CIRUGIA_PEDIATRICA", "Cirugía Pediátrica"),
    ("CIRUGIA_PLASTICA", "Cirugía Plástica"),
    ("DERMATOLOGIA", "Dermatología"),
    ("ENDOCRINOLOGIA", "Endocrinología"),
    ("GASTROENTEROLOGIA", "Gastroenterología"),
    ("GENETICA_MEDICA", "Genética Médica"),
    ("GERIATRIA", "Geriatría"),
    ("GINECOLOGIA_OBSTETRICIA", "Ginecología y Obstetricia"),
    ("HEMATOLOGIA", "Hematología"),
    ("INMUNOLOGIA_ALERGIA", "Inmunología y Alergia"),
    ("MEDICINA_EMERGENCIAS_DESASTRES", "Medicina de Emergencias y Desastres"),
    ("MEDICINA_ENF_INFECCIOSAS_TROPICALES", "Medicina de Enfermedades Infecciosas y Tropicales"),
    ("MEDICINA_DEPORTE", "Medicina del Deporte"),
    ("MEDICINA_FAMILIAR_COMUNITARIA", "Medicina Familiar y Comunitaria"),
    ("MEDICINA_FISICA_REHABILITACION", "Medicina Física y de Rehabilitación"),
    ("MEDICINA_HIPERBARICA_SUBACUATICA", "Medicina Hiperbárica y Sub Acuática"),
    ("MEDICINA_INTENSIVA", "Medicina Intensiva"),
    ("MEDICINA_INTERNA", "Medicina Interna"),
    ("MEDICINA_LEGAL", "Medicina Legal"),
    ("MEDICINA_NUCLEAR", "Medicina Nuclear"),
    ("MEDICINA_OCUPACIONAL_MEDIO_AMBIENTE", "Medicina Ocupacional y del Medio Ambiente"),
    ("MEDICINA_ONCOLOGICA", "Medicina Oncológica"),
    ("NEFROLOGIA", "Nefrología"),
    ("NEONATOLOGIA", "Neonatología"),
    ("NEUMOLOGIA", "Neumología"),
    ("NEUROCIRUGIA", "Neurocirugía"),
    ("NEUROLOGIA", "Neurología"),
    ("OFTALMOLOGIA", "Oftalmología"),
    ("ORTOPEDIA_TRAUMATOLOGIA", "Ortopedia y Traumatología"),
    ("OTORRINOLARINGOLOGIA", "Otorrinolaringología"),
    ("PATOLOGIA_CLINICA", "Patología Clínica"),
    ("PEDIATRIA", "Pediatría"),
    ("PSIQUIATRIA", "Psiquiatría"),
    ("RADIOLOGIA", "Radiología"),
    ("RADIOTERAPIA", "Radioterapia"),
    ("REUMATOLOGIA", "Reumatología"),
    ("UROLOGIA", "Urología"),
]


# (código, nombre) — ámbitos geográficos sanitarios (autoridades sanitarias regionales)
HEALTH_GEOGRAPHIC_SCOPES = [
    ("AMAZONAS", "Amazonas"),
    ("ANCASH", "Áncash"),
    ("APURIMAC", "Apurímac"),
    ("AREQUIPA", "Arequipa"),
    ("AYACUCHO", "Ayacucho"),
    ("CAJAMARCA", "Cajamarca"),
    ("CALLAO", "Callao"),
    ("CUSCO", "Cusco"),
    ("HUANCAVELICA", "Huancavelica"),
    ("HUANUCO", "Huánuco"),
    ("ICA", "Ica"),
    ("JUNIN", "Junín"),
    ("LA_LIBERTAD", "La Libertad"),
    ("LAMBAYEQUE", "Lambayeque"),
    ("LORETO", "Loreto"),
    ("MADRE_DE_DIOS", "Madre de Dios"),
    ("MOQUEGUA", "Moquegua"),
    ("PASCO", "Pasco"),
    ("PIURA", "Piura"),
    ("PUNO", "Puno"),
    ("SAN_MARTIN", "San Martín"),
    ("TACNA", "Tacna"),
    ("TUMBES", "Tumbes"),
    ("UCAYALI", "Ucayali"),
    ("LIMA_DIRESA", "Lima (Región)"),
    ("LIMA_DIRIS_NORTE", "Lima Metropolitana - DIRIS Lima Norte"),
    ("LIMA_DIRIS_CENTRO", "Lima Metropolitana - DIRIS Lima Centro"),
    ("LIMA_DIRIS_SUR", "Lima Metropolitana - DIRIS Lima Sur"),
    ("LIMA_DIRIS_ESTE", "Lima Metropolitana - DIRIS Lima Este"),
]


def seed(apps, schema_editor):
    Specialty = apps.get_model("convenios", "Specialty")
    for codigo, nombre in SPECIALTIES:
        Specialty.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})

    HealthGeographicScope = apps.get_model("convenios", "HealthGeographicScope")
    for codigo, nombre in HEALTH_GEOGRAPHIC_SCOPES:
        HealthGeographicScope.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})


def unseed(apps, schema_editor):
    Specialty = apps.get_model("convenios", "Specialty")
    Specialty.objects.filter(codigo__in=[c for c, _ in SPECIALTIES]).delete()

    HealthGeographicScope = apps.get_model("convenios", "HealthGeographicScope")
    HealthGeographicScope.objects.filter(codigo__in=[c for c, _ in HEALTH_GEOGRAPHIC_SCOPES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0002_seed_catalogos"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
