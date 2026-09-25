"""Helpers de construcción de datos mock vía ORM para las pruebas de ``apps.internados``.

No se usan ``factory-boy`` ni ``faker``: todo se arma con el ORM. Estas funciones
crean el grafo mínimo de entidades del módulo 1 (convenios) de las que dependen los
modelos del módulo 2 (internados): universidad, unidad ejecutora, IPRESS, convenio
específico vigente, registro y asignación de campos clínicos, tutor, estudiante, etc.
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
    ConventionParticipant,
    ConventionStatus,
    ConventionType,
    ExecutingUnit,
    HealthGeographicScope,
    Ipress,
    ProfessionalCareer,
    Specialty,
    Ubigeo,
    University,
    UniversityEntityType,
    UniversityManagementType,
    UserEntityProfile,
)
from apps.internados.models import (
    IdentityDocumentType,
    Internship,
    InternshipPeriod,
    InternshipStatus,
    RelationshipType,
    RotationStatus,
    ServiceArea,
    Student,
    Tutor,
)

HOY = datetime.date(2026, 3, 1)


# ---------------------------------------------------------------------------
# Usuarios y grupos
# ---------------------------------------------------------------------------
def crear_usuario(username="u_intern", *, grupos=None, is_superuser=False,
                  email=None, first_name="Ana", last_name="Lopez Diaz"):
    """Crea un ``User`` con contraseña hasheada y grupos opcionales.

    El correo se deriva del username por defecto para evitar colisiones en la
    columna única ``auth_user.email`` cuando se crean varios usuarios.
    """
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
# Catálogos base
# ---------------------------------------------------------------------------
def crear_nivel(codigo="PREGRADO", nombre="Pregrado"):
    nivel, _ = AcademicLevel.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return nivel


def crear_carrera(nombre="Medicina", nivel=None):
    nivel = nivel or crear_nivel()
    return ProfessionalCareer.objects.create(nombre=nombre, nivel_academico=nivel)


def crear_especialidad(codigo="ESP-CIR", nombre="Cirugía"):
    esp, _ = Specialty.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return esp


def crear_tipo_documento(codigo="DNI", nombre="DNI"):
    t, _ = IdentityDocumentType.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return t


def crear_parentesco(codigo="PADRE", nombre="Padre"):
    p, _ = RelationshipType.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return p


def crear_periodo(codigo="2026-I", nombre="2026-I"):
    p, _ = InternshipPeriod.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return p


def crear_estado_internado(codigo="REGISTRADO", nombre=None, orden=0):
    e, _ = InternshipStatus.objects.get_or_create(
        codigo=codigo, defaults={"nombre": nombre or codigo.title(), "orden": orden}
    )
    return e


def crear_estado_rotacion(codigo="SOLICITADA", nombre=None, orden=0):
    e, _ = RotationStatus.objects.get_or_create(
        codigo=codigo, defaults={"nombre": nombre or codigo.title(), "orden": orden}
    )
    return e


def crear_servicio_area(codigo="SRV-1", nombre="Emergencia"):
    s, _ = ServiceArea.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return s


def crear_ambito(codigo="AMB-1", nombre="Lima"):
    a, _ = HealthGeographicScope.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
    return a


def crear_ubigeo(codigo="150101", departamento="LIMA", provincia="LIMA", distrito="LIMA"):
    u, _ = Ubigeo.objects.get_or_create(
        codigo=codigo,
        defaults=dict(departamento=departamento, provincia=provincia, distrito=distrito),
    )
    return u


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


def crear_unidad_ejecutora(codigo="0001", nombre="UE Salud", ambito=None):
    ambito = ambito or crear_ambito()
    return ExecutingUnit.objects.create(
        codigo=codigo, nombre=nombre, ambito_geografico_sanitario=ambito
    )


def crear_ipress(codigo="12345678", nombre="Hospital Central", ambito=None,
                 unidad_ejecutora=None, es_sede_docente=True):
    ambito = ambito or crear_ambito()
    if unidad_ejecutora is None:
        # UE única por IPRESS (código de 4 chars derivado del RENIPRESS) para no
        # colisionar en la PK de unidad_ejecutora al crear varias sedes.
        ue_codigo = codigo[-4:]
        unidad_ejecutora, _ = ExecutingUnit.objects.get_or_create(
            codigo=ue_codigo,
            defaults={"nombre": f"UE {ue_codigo}", "ambito_geografico_sanitario": ambito},
        )
    return Ipress.objects.create(
        codigo_renipress=codigo, nombre=nombre, unidad_ejecutora=unidad_ejecutora,
        ambito_geografico_sanitario=ambito, es_sede_docente=es_sede_docente,
    )


def crear_tipo_convenio(codigo="ESPECIFICO", nombre="Específico", anios=3):
    t, _ = ConventionType.objects.get_or_create(
        codigo=codigo, defaults={"nombre": nombre, "anios_vigencia": anios}
    )
    return t


def crear_estado_convenio(codigo="VIGENTE", nombre="Vigente", orden=20):
    e, _ = ConventionStatus.objects.get_or_create(
        codigo=codigo, defaults={"nombre": nombre, "orden": orden}
    )
    return e


def crear_convenio(*, creado_por, universidad=None, tipo_codigo="ESPECIFICO",
                   estado_codigo="VIGENTE", titulo="Convenio Específico X"):
    """Crea un Convenio (por defecto Específico vigente) con el grafo mínimo."""
    from apps.convenios.models import Organ, OrganicUnit

    universidad = universidad or crear_universidad()
    tipo = crear_tipo_convenio(codigo=tipo_codigo, nombre=tipo_codigo.title())
    estado = crear_estado_convenio(codigo=estado_codigo, nombre=estado_codigo.title())
    organo, _ = Organ.objects.get_or_create(nombre="GERESA")
    unidad, _ = OrganicUnit.objects.get_or_create(organo=organo, nombre="GERESA Lima")
    ct_uni = ContentType.objects.get_for_model(University)
    return Convention.objects.create(
        tipo_convenio=tipo, titulo=titulo,
        solicitante_tipo_contenido=ct_uni, solicitante_id_objeto=universidad.id,
        unidad_organica=unidad, universidad=universidad, estado_actual=estado,
        fecha_solicitud=HOY, fecha_inicio=HOY, fecha_fin=datetime.date(2028, 3, 1),
        creado_por=creado_por,
    )


def crear_registro_campo_clinico(*, ipress=None, carrera=None, registrados=5):
    ipress = ipress or crear_ipress()
    carrera = carrera or crear_carrera()
    return ClinicalFieldRegistration.objects.create(
        ipress=ipress, carrera_profesional=carrera,
        campos_clinicos_registrados=registrados,
    )


def crear_asignacion_campo_clinico(*, convenio, universidad=None, ipress=None,
                                   carrera=None, autorizados=3, registro=None):
    universidad = universidad or convenio.universidad
    ipress = ipress or crear_ipress()
    carrera = carrera or crear_carrera()
    registro = registro or crear_registro_campo_clinico(ipress=ipress, carrera=carrera)
    return ClinicalFieldAllocation.objects.create(
        campo_clinico_ipress=registro, convenio=convenio, ipress=ipress,
        carrera_profesional=carrera, universidad=universidad,
        fecha_inicio=HOY, fecha_fin=datetime.date(2027, 3, 1),
        campos_clinicos_autorizados=autorizados,
    )


# ---------------------------------------------------------------------------
# Personas del módulo
# ---------------------------------------------------------------------------
def crear_estudiante(*, creado_por, universidad=None, carrera=None, tipo_documento=None,
                     numero_documento="87654321", nombres="JUAN", apellido_paterno="PEREZ",
                     correo=None, telefono="999111222", periodo=None,
                     especialidad=None):
    # Correo derivado del documento para no colisionar en auth_user.email al
    # aprovisionar varios internos (RN-22 usa el correo del estudiante).
    if correo is None:
        correo = f"est{numero_documento}@mail.com"
    universidad = universidad or crear_universidad()
    carrera = carrera or crear_carrera()
    tipo_documento = tipo_documento or crear_tipo_documento()
    return Student.objects.create(
        tipo_documento_identidad=tipo_documento, numero_documento=numero_documento,
        nombres=nombres, apellido_paterno=apellido_paterno, apellido_materno="GOMEZ",
        correo=correo, telefono=telefono, universidad=universidad,
        carrera_profesional=carrera, periodo_internado=periodo, especialidad=especialidad,
        creado_por=creado_por,
    )


def crear_tutor(*, universidades=None, tipo_documento=None, numero_documento="45678912",
                nombres="LUIS", apellido_paterno="RAMOS"):
    tipo_documento = tipo_documento or crear_tipo_documento()
    tutor = Tutor.objects.create(
        tipo_documento_identidad=tipo_documento, numero_documento=numero_documento,
        nombres=nombres, apellido_paterno=apellido_paterno,
    )
    if universidades:
        tutor.universidades.set(universidades)
    return tutor


def crear_internado(*, creado_por, estudiante=None, convenio=None, campo_clinico=None,
                    ipress=None, tutor=None, ambito=None, estado=None,
                    fecha_inicio=None, fecha_fin=None):
    """Crea un ``Internship`` completo directamente por ORM (sin pasar por el service)."""
    ambito = ambito or crear_ambito()
    if ipress is None:
        # IPRESS por defecto idempotente por ámbito (reutiliza si ya existe) para
        # permitir crear varios internados en la misma sede sin colisionar la PK.
        ipress = Ipress.objects.filter(ambito_geografico_sanitario=ambito).first()
        if ipress is None:
            ipress = crear_ipress(ambito=ambito)
    universidad = crear_universidad() if estudiante is None else estudiante.universidad
    estudiante = estudiante or crear_estudiante(creado_por=creado_por, universidad=universidad)
    convenio = convenio or crear_convenio(creado_por=creado_por, universidad=estudiante.universidad)
    campo_clinico = campo_clinico or crear_asignacion_campo_clinico(
        convenio=convenio, universidad=estudiante.universidad, ipress=ipress,
    )
    tutor = tutor or crear_tutor(universidades=[estudiante.universidad])
    estado = estado or crear_estado_internado("REGISTRADO")
    return Internship.objects.create(
        estudiante=estudiante, convenio=convenio, campo_clinico=campo_clinico,
        ipress=ipress, tutor=tutor, ambito_geografico_sanitario=ambito,
        estado_actual=estado,
        fecha_inicio=fecha_inicio or HOY, fecha_fin=fecha_fin or datetime.date(2026, 9, 1),
        creado_por=creado_por,
    )


def crear_participante(*, convenio, universidad=None, es_firmante=True):
    universidad = universidad or convenio.universidad
    ct_uni = ContentType.objects.get_for_model(University)
    return ConventionParticipant.objects.create(
        convenio=convenio, tipo_contenido=ct_uni, id_objeto=universidad.id,
        es_firmante=es_firmante,
    )
