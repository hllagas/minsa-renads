"""Helpers de construcción de datos mock vía ORM para las pruebas de ``apps.convenios``.

No se usan ``factory-boy`` ni ``faker``: todo se arma con el ORM. El test runner de
Django crea la BD de test desde las migraciones, que **siembran** los catálogos
canónicos (``ConventionStatus``, ``ConventionType``, los 5 ``Organ`` canónicos y los
``AnnexDocument``). Por eso estas fábricas usan ``get_or_create`` / consultas sobre las
filas sembradas en lugar de crear duplicados que violen ``unique``.

La categoría de una ``OrganicUnit`` se **deriva** del nombre de su ``Organ`` (propiedad
``OrganicUnit.categoria``), por lo que los ``Organ`` se crean con los nombres canónicos
exactos: ``"MINSA Administrativo"`` (ORGANO_MINSA), ``"Universidad"``,
``"Gobierno Regional"``, ``"MINSA DIRIS"`` y ``"Unidad Ejecutora"``.
"""

import datetime

from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType

from apps.convenios.models import (
    AcademicLevel,
    AuthorizationType,
    ClinicalFieldAllocation,
    ClinicalFieldRegistration,
    Convention,
    ConventionParty,
    ConventionStatus,
    ConventionType,
    ExecutingUnit,
    ExecutivePosition,
    Faculty,
    HealthGeographicScope,
    Ipress,
    Organ,
    OrganicUnit,
    OrganRepresentative,
    ProfessionalCareer,
    ProfessionalCareer as Career,
    RegionalGovernment,
    Region,
    Specialty,
    Ubigeo,
    University,
    UniversityCareer,
    UniversityEntityType,
    UniversityManagementType,
    UserEntityProfile,
)

HOY = datetime.date(2026, 3, 1)

# Nombres canónicos de Organ → categoría (mirror de OrganicUnit._NOMBRE_A_CATEGORIA).
ORGANO_MINSA = "MINSA Administrativo"
ORGANO_UNIVERSIDAD = "Universidad"
ORGANO_GORE = "Gobierno Regional"
ORGANO_DIRIS = "MINSA DIRIS"
ORGANO_UE = "Unidad Ejecutora"


# ---------------------------------------------------------------------------
# Usuarios y grupos
# ---------------------------------------------------------------------------
def crear_usuario(username="u_conv", *, grupos=None, is_superuser=False, email=None,
                  first_name="Ana", last_name="Lopez Diaz"):
    """Crea un ``User`` con contraseña hasheada y grupos opcionales."""
    if email is None:
        email = f"{username}@renads.test"
    user = User.objects.create_user(
        username=username, password="Passw0rd!seg9", email=email,
        first_name=first_name, last_name=last_name,
    )
    if is_superuser:
        user.is_superuser = True
        user.is_staff = True
        user.save(update_fields=["is_superuser", "is_staff"])
    for nombre in grupos or []:
        grupo, _ = Group.objects.get_or_create(name=nombre)
        user.groups.add(grupo)
    return user


def crear_grupo(nombre):
    grupo, _ = Group.objects.get_or_create(name=nombre)
    return grupo


def dar_ambito(usuario, entidad, grupo_nombre="Universidad"):
    """Otorga al usuario un perfil institucional activo sobre ``entidad``."""
    grupo, _ = Group.objects.get_or_create(name=grupo_nombre)
    ct = ContentType.objects.get_for_model(type(entidad))
    return UserEntityProfile.objects.create(
        usuario=usuario, tipo_contenido=ct, id_objeto=str(entidad.pk),
        grupo=grupo, activo=True,
    )


# ---------------------------------------------------------------------------
# Órganos / unidades orgánicas / cargos
# ---------------------------------------------------------------------------
def crear_organo(nombre=ORGANO_GORE):
    """Crea (o reutiliza) un ``Organ`` por nombre canónico."""
    organo, _ = Organ.objects.get_or_create(nombre=nombre)
    return organo


def crear_unidad_organica(*, organo_nombre=ORGANO_GORE, nombre="GERESA Lima", organo=None):
    """Crea una ``OrganicUnit`` cuya categoría deriva del nombre del ``Organ``."""
    organo = organo or crear_organo(organo_nombre)
    unidad, _ = OrganicUnit.objects.get_or_create(
        organo=organo, nombre=nombre, defaults={"siglas": "UO"}
    )
    return unidad


def crear_cargo(*, unidad=None, organo=None, nombre="Director General"):
    """Crea un ``ExecutivePosition`` coherente (organo == unidad.organo)."""
    if unidad is None:
        unidad = crear_unidad_organica()
    organo = organo or unidad.organo
    cargo, _ = ExecutivePosition.objects.get_or_create(
        unidad_organica=unidad, nombre_masculino=nombre,
        defaults={"organo": organo, "nombre_femenino": nombre},
    )
    return cargo


# ---------------------------------------------------------------------------
# Catálogos base
# ---------------------------------------------------------------------------
def crear_nivel(codigo="PREGRADO", nombre="Pregrado"):
    n, _ = AcademicLevel.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return n


def crear_carrera(nombre="Medicina", nivel=None):
    nivel = nivel or crear_nivel()
    return ProfessionalCareer.objects.create(nombre=nombre, nivel_academico=nivel)


def crear_especialidad(codigo="ESP-CIR", nombre="Cirugía"):
    e, _ = Specialty.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return e


def crear_ambito(codigo="AMB-1", nombre="Lima"):
    a, _ = HealthGeographicScope.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return a


def crear_region(nombre="Lima", codigo="LIM"):
    r, _ = Region.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return r


def crear_ubigeo(codigo="150101", departamento="LIMA", provincia="LIMA", distrito="LIMA"):
    u, _ = Ubigeo.objects.get_or_create(
        codigo=codigo,
        defaults=dict(departamento=departamento, provincia=provincia, distrito=distrito),
    )
    return u


def crear_tipo_documento(codigo="DNI", nombre="DNI"):
    from apps.internados.models import IdentityDocumentType
    t, _ = IdentityDocumentType.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return t


# ---------------------------------------------------------------------------
# Entidades institucionales
# ---------------------------------------------------------------------------
def crear_universidad(nombre="Universidad Nacional", codigo_inei="UNI1"):
    gestion, _ = UniversityManagementType.objects.get_or_create(
        codigo="PUB", defaults={"nombre": "Pública"}
    )
    tipo_entidad, _ = UniversityEntityType.objects.get_or_create(nombre="Universidad")
    autorizacion, _ = AuthorizationType.objects.get_or_create(
        codigo="LIC", defaults={"nombre": "Licenciada"}
    )
    return University.objects.create(
        nombre=nombre, siglas="UN", tipo_gestion=gestion,
        tipo_entidad=tipo_entidad, tipo_autorizacion=autorizacion, codigo_inei=codigo_inei,
    )


def crear_facultad(*, universidad=None, nombre="Facultad de Medicina"):
    universidad = universidad or crear_universidad()
    return Faculty.objects.create(universidad=universidad, nombre=nombre)


def crear_gobierno_regional(*, nombre="GORE Lima", region=None, sigla="GRL"):
    region = region or crear_region()
    return RegionalGovernment.objects.create(nombre=nombre, region=region, sigla=sigla)


def crear_unidad_ejecutora(codigo="0001", nombre="UE Salud", ambito=None):
    ambito = ambito or crear_ambito()
    ue, _ = ExecutingUnit.objects.get_or_create(
        codigo=codigo, defaults={"nombre": nombre, "ambito_geografico_sanitario": ambito}
    )
    return ue


def crear_ipress(codigo="12345678", nombre="Hospital Central", ambito=None,
                 unidad_ejecutora=None, es_sede_docente=True):
    ambito = ambito or crear_ambito()
    if unidad_ejecutora is None:
        ue_codigo = codigo[-4:]
        unidad_ejecutora, _ = ExecutingUnit.objects.get_or_create(
            codigo=ue_codigo,
            defaults={"nombre": f"UE {ue_codigo}", "ambito_geografico_sanitario": ambito},
        )
    return Ipress.objects.create(
        codigo_renipress=codigo, nombre=nombre, unidad_ejecutora=unidad_ejecutora,
        ambito_geografico_sanitario=ambito, es_sede_docente=es_sede_docente,
    )


def crear_conapres(nombre="CONAPRES"):
    from apps.convenios.models import Conapres
    return Conapres.objects.create(nombre=nombre)


# ---------------------------------------------------------------------------
# Convenios
# ---------------------------------------------------------------------------
def tipo_convenio(codigo="ESPECIFICO"):
    """Devuelve el ``ConventionType`` sembrado (MARCO/ESPECIFICO)."""
    return ConventionType.objects.get(codigo=codigo)


def estado_convenio(codigo="VIGENTE"):
    """Devuelve un ``ConventionStatus`` sembrado por código."""
    return ConventionStatus.objects.get(codigo=codigo)


def crear_convenio(*, creado_por, universidad=None, tipo_codigo="ESPECIFICO",
                   estado_codigo="VIGENTE", titulo="Convenio X",
                   unidad_organica=None, organo_nombre=ORGANO_GORE,
                   unidad_ejecutora=None, facultad=None, convenio_marco=None,
                   gobierno_regional=None, solicitante=None,
                   fecha_fin=datetime.date(2028, 3, 1)):
    """Crea un ``Convention`` por ORM (sin pasar por el service)."""
    universidad = universidad or crear_universidad()
    tipo = tipo_convenio(tipo_codigo)
    estado = estado_convenio(estado_codigo)
    unidad_organica = unidad_organica or crear_unidad_organica(organo_nombre=organo_nombre)
    if solicitante is None:
        solicitante = universidad
    ct_sol = ContentType.objects.get_for_model(type(solicitante))
    return Convention.objects.create(
        tipo_convenio=tipo, titulo=titulo,
        convenio_marco=convenio_marco,
        solicitante_tipo_contenido=ct_sol, solicitante_id_objeto=solicitante.pk,
        unidad_organica=unidad_organica, universidad=universidad, estado_actual=estado,
        gobierno_regional=gobierno_regional,
        unidad_ejecutora=unidad_ejecutora, facultad=facultad,
        fecha_solicitud=HOY, fecha_inicio=HOY, fecha_fin=fecha_fin,
        creado_por=creado_por,
    )


def crear_registro_campo_clinico(*, ipress=None, carrera=None, especialidad=None,
                                 registrados=5, asignados=0, creado_por=None,
                                 numero_resolucion_conapres=""):
    ipress = ipress or crear_ipress()
    carrera = carrera or crear_carrera()
    return ClinicalFieldRegistration.objects.create(
        ipress=ipress, carrera_profesional=carrera, especialidad=especialidad,
        campos_clinicos_registrados=registrados, campos_clinicos_asignados=asignados,
        numero_resolucion_conapres=numero_resolucion_conapres, creado_por=creado_por,
    )


def crear_asignacion_campo_clinico(*, convenio, universidad=None, ipress=None,
                                   carrera=None, autorizados=3, registro=None,
                                   creado_por=None):
    universidad = universidad or convenio.universidad
    ipress = ipress or crear_ipress()
    carrera = carrera or crear_carrera()
    registro = registro or crear_registro_campo_clinico(ipress=ipress, carrera=carrera)
    return ClinicalFieldAllocation.objects.create(
        campo_clinico_ipress=registro, convenio=convenio, ipress=ipress,
        carrera_profesional=carrera, universidad=universidad,
        fecha_inicio=HOY, fecha_fin=datetime.date(2027, 3, 1),
        campos_clinicos_autorizados=autorizados, creado_por=creado_por,
    )


def crear_representante(*, entidad, cargo=None, nombre="Juan Perez",
                        numero="10000001", sexo="M", tipo_documento=None, activo=True):
    tipo_documento = tipo_documento or crear_tipo_documento()
    ct = ContentType.objects.get_for_model(type(entidad))
    cargo = cargo or crear_cargo()
    return OrganRepresentative.objects.create(
        tipo_contenido=ct, id_objeto=entidad.pk, nombre=nombre,
        tipo_documento_identidad=tipo_documento, numero_documento_identidad=numero,
        sexo=sexo, cargo_ejecutivo=cargo, fecha_inicio_designacion=HOY, activo=activo,
    )


def crear_universidad_carrera(*, universidad, carrera, facultad, activo=True):
    return UniversityCareer.objects.create(
        universidad=universidad, carrera_profesional=carrera,
        facultad=facultad, activo=activo,
    )
