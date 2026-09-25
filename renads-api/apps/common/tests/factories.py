"""Helpers de construcción de datos mock vía ORM para las pruebas de ``apps.common``.

No se usan ``factory-boy`` ni ``faker``: todo se arma con el ORM. Estas funciones
crean las entidades institucionales mínimas (órgano, unidad orgánica, cargo) que el
perfil de usuario exige (todos los campos ``NOT NULL``), más usuarios y grupos.
"""

from django.contrib.auth.models import Group, User

from apps.convenios.models import ExecutivePosition, Organ, OrganicUnit


def crear_organo(nombre="MINSA Administrativo"):
    """Crea (o reutiliza) un ``Organ`` por nombre."""
    organo, _ = Organ.objects.get_or_create(nombre=nombre)
    return organo


def crear_unidad_organica(organo=None, nombre="Dirección General de Personal"):
    """Crea una ``OrganicUnit`` colgada de un ``Organ``."""
    organo = organo or crear_organo()
    unidad, _ = OrganicUnit.objects.get_or_create(organo=organo, nombre=nombre)
    return unidad


def crear_cargo(unidad=None, organo=None, nombre="Director General"):
    """Crea un ``ExecutivePosition`` coherente (organo == unidad.organo)."""
    if unidad is None:
        unidad = crear_unidad_organica(organo)
    organo = organo or unidad.organo
    cargo, _ = ExecutivePosition.objects.get_or_create(
        unidad_organica=unidad,
        nombre_masculino=nombre,
        defaults={"organo": organo, "nombre_femenino": nombre},
    )
    return cargo


def crear_usuario(
    username="user1",
    *,
    password="Passw0rd!segura9",
    email="user1@renads.test",
    first_name="Juan",
    last_name="Perez Lopez",
    is_superuser=False,
    is_staff=False,
    grupos=None,
):
    """Crea un ``User`` con contraseña hasheada y grupos opcionales."""
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    if is_superuser or is_staff:
        user.is_superuser = is_superuser
        user.is_staff = is_staff
        user.save(update_fields=["is_superuser", "is_staff"])
    if grupos:
        for nombre in grupos:
            grupo, _ = Group.objects.get_or_create(name=nombre)
            user.groups.add(grupo)
    return user


def crear_grupo(nombre):
    """Crea (o reutiliza) un ``Group`` por nombre."""
    grupo, _ = Group.objects.get_or_create(name=nombre)
    return grupo
