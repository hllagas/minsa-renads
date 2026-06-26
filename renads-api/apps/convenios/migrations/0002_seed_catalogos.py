"""Seed de catálogos cerrados del Módulo 1 (Gestionar Convenios)."""

from django.db import migrations


CONVENTION_TYPES = [
    ("MARCO", "Convenio Marco", 4),
    ("ESPECIFICO", "Convenio Específico", 3),
]

# (código, nombre, aplica_a, orden)
CONVENTION_STATUSES = [
    ("SOLICITUD_REGISTRADA", "Solicitud registrada", "TODOS", 1),
    ("PDF_PRELIMINAR_GENERADO", "PDF preliminar generado", "TODOS", 2),
    ("EN_EVALUACION_DIGEP", "En evaluación técnica DIGEP", "TODOS", 3),
    ("OBSERVADO_DIGEP", "Observado por DIGEP", "TODOS", 4),
    ("SUBSANADO", "Subsanado por entidad solicitante", "TODOS", 5),
    ("VALIDADO_TECNICAMENTE", "Validado técnicamente", "TODOS", 6),
    ("PENDIENTE_CONAPRES", "Pendiente de opinión CONAPRES", "ESPECIFICO", 7),
    ("CONAPRES_FAVORABLE", "Opinión CONAPRES favorable", "ESPECIFICO", 8),
    ("CONAPRES_OBSERVADO", "Opinión CONAPRES observada", "ESPECIFICO", 9),
    ("CAMPOS_CLINICOS_DEFINIDOS", "Campos clínicos definidos", "ESPECIFICO", 10),
    ("PENDIENTE_OGAJ", "Pendiente de opinión OGAJ", "TODOS", 11),
    ("OGAJ_FAVORABLE", "Opinión jurídica favorable", "TODOS", 12),
    ("OGAJ_OBSERVADO", "Opinión jurídica observada", "TODOS", 13),
    ("ENVIADO_SG", "Enviado a Secretaría General", "TODOS", 14),
    ("ENVIADO_VICEPAS", "Enviado a Despacho VICEPAS", "TODOS", 15),
    ("FIRMADO_MINSA", "Firmado por MINSA", "TODOS", 16),
    ("ENVIADO_EXTERNOS", "Enviado a entidades externas", "TODOS", 17),
    ("FIRMADO_EXTERNOS", "Firmado por entidades externas", "TODOS", 18),
    ("SUSCRITO", "Suscrito", "TODOS", 19),
    ("PUBLICADO", "Publicado", "TODOS", 20),
    ("VIGENTE", "Vigente", "TODOS", 21),
    ("PROXIMO_A_VENCER", "Próximo a vencer", "TODOS", 22),
    ("VENCIDO", "Vencido", "TODOS", 23),
    ("AMPLIADO", "Ampliado", "TODOS", 24),
    ("CERRADO", "Cerrado", "TODOS", 25),
    ("ANULADO", "Anulado", "TODOS", 26),
]

UNIVERSITY_MANAGEMENT_TYPES = [
    ("PUBLICA", "Pública"),
    ("PRIVADA", "Privada"),
]

UNIVERSITY_ENTITY_TYPES = [
    ("UNIVERSIDAD", "Universidad"),
    ("ESCUELA_POSGRADO", "Escuela de posgrado"),
    ("ESCUELA_SUPERIOR", "Escuela superior"),
    ("INSTITUTO", "Instituto"),
]

AUTHORIZATION_TYPES = [
    ("LICENCIADA", "Licenciada"),
    ("DENEGADA", "Denegada"),
    ("PENDIENTE", "Pendiente"),
]

ACADEMIC_LEVELS = [
    ("CARRERA_PROFESIONAL", "Carrera profesional"),
    ("SEGUNDA_ESPECIALIDAD", "Segunda especialidad"),
    ("MAESTRIA", "Maestría"),
    ("DOCTORADO", "Doctorado"),
]

REGIONAL_ORGAN_TYPES = [
    ("GERESA", "Gerencia Regional de Salud"),
    ("DIRESA", "Dirección Regional de Salud"),
    ("DIRIS", "Dirección de Redes Integradas de Salud"),
]

EXECUTING_UNIT_TYPES = [
    ("HOSPITAL", "Hospital"),
    ("INSTITUTO_ESPECIALIZADO", "Instituto especializado"),
    ("RED_SALUD", "Red de salud"),
]

MINSA_ORGAN_TYPES = [
    ("DIGEP", "Dirección General de Personal de la Salud"),
    ("OGAJ", "Oficina General de Asesoría Jurídica"),
    ("SG", "Secretaría General"),
    ("VICEPAS", "Despacho Viceministerial de Prestaciones y Aseguramiento en Salud"),
]

# Códigos INEI de departamentos del Perú (+ Callao)
REGIONS = [
    ("01", "Amazonas"), ("02", "Áncash"), ("03", "Apurímac"), ("04", "Arequipa"),
    ("05", "Ayacucho"), ("06", "Cajamarca"), ("07", "Callao"), ("08", "Cusco"),
    ("09", "Huancavelica"), ("10", "Huánuco"), ("11", "Ica"), ("12", "Junín"),
    ("13", "La Libertad"), ("14", "Lambayeque"), ("15", "Lima"), ("16", "Loreto"),
    ("17", "Madre de Dios"), ("18", "Moquegua"), ("19", "Pasco"), ("20", "Piura"),
    ("21", "Puno"), ("22", "San Martín"), ("23", "Tacna"), ("24", "Tumbes"),
    ("25", "Ucayali"),
]

SIMPLE_CATALOGS = {
    "UniversityManagementType": UNIVERSITY_MANAGEMENT_TYPES,
    "UniversityEntityType": UNIVERSITY_ENTITY_TYPES,
    "AuthorizationType": AUTHORIZATION_TYPES,
    "AcademicLevel": ACADEMIC_LEVELS,
    "RegionalOrganType": REGIONAL_ORGAN_TYPES,
    "ExecutingUnitType": EXECUTING_UNIT_TYPES,
    "MinsaOrganType": MINSA_ORGAN_TYPES,
    "Region": REGIONS,
}


def seed(apps, schema_editor):
    ConventionType = apps.get_model("convenios", "ConventionType")
    for codigo, nombre, anios in CONVENTION_TYPES:
        ConventionType.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre, "anios_vigencia": anios}
        )

    ConventionStatus = apps.get_model("convenios", "ConventionStatus")
    for codigo, nombre, aplica_a, orden in CONVENTION_STATUSES:
        ConventionStatus.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre, "aplica_a": aplica_a, "orden": orden}
        )

    for model_name, rows in SIMPLE_CATALOGS.items():
        Model = apps.get_model("convenios", model_name)
        for codigo, nombre in rows:
            Model.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})


def unseed(apps, schema_editor):
    codes = {
        "ConventionType": [r[0] for r in CONVENTION_TYPES],
        "ConventionStatus": [r[0] for r in CONVENTION_STATUSES],
        **{name: [r[0] for r in rows] for name, rows in SIMPLE_CATALOGS.items()},
    }
    for model_name, codigos in codes.items():
        Model = apps.get_model("convenios", model_name)
        Model.objects.filter(codigo__in=codigos).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
