# Endurece `perfil_usuario` — PASO 1 de 2 (datos):
#   1. AddField `tiene_ficha_usuario` (default False) — seguro directo.
#   2. RunPython `backfill_perfiles` — crea los perfiles faltantes y rellena los
#      campos vacíos/nulos con datos aleatorios deterministas (semilla), respetando
#      la unicidad de `numero_documento`/`telefono`. En este punto las columnas
#      todavía son nullable, por lo que el RunPython puede escribir sin violar NOT NULL.
#
# Los `AlterField` a NOT NULL van en la migración `0010` (PASO 2). Se separan en dos
# migraciones porque en PostgreSQL un `RunPython` que escribe datos seguido de un
# `ALTER TABLE` sobre la MISMA tabla, dentro de la misma transacción de migración,
# falla con «cannot ALTER TABLE ... because it has pending trigger events» (los
# triggers de validación de FK quedan pendientes hasta el fin de la transacción).
# Al separarlos, el backfill se confirma antes de que corra el ALTER.
#
# El RunPython usa modelos históricos (`apps.get_model`) y nunca borra usuarios.
# Reverse del RunPython = noop (no se revierten los datos aleatorios).

import random

from django.db import migrations, models


APELLIDOS = [
    "Quispe", "Mamani", "Flores", "Huaman", "Rojas",
    "Vargas", "Torres", "Ramos", "Castro", "Diaz",
]


def backfill_perfiles(apps, schema_editor):
    """Crea los perfiles faltantes y rellena los campos vacíos/nulos (determinista).

    - Rellena SOLO los campos vacíos/nulos → idempotente y preserva los datos reales
      del perfil existente.
    - `numero_documento` = 8 dígitos (DNI); `telefono` = 9 dígitos empezando en 9;
      ambos verificados contra los sets de valores ya usados para respetar UNIQUE.
    - `unidad_organica`/`cargo` = PK real elegido al azar de las filas existentes
      (nunca inventa FKs).
    """
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("common", "UserProfile")
    OrganicUnit = apps.get_model("convenios", "OrganicUnit")
    ExecutivePosition = apps.get_model("convenios", "ExecutivePosition")

    rng = random.Random(20260924)  # semilla determinista para reproducibilidad

    unidades = list(OrganicUnit.objects.values_list("pk", flat=True))
    cargos = list(ExecutivePosition.objects.values_list("pk", flat=True))
    if not unidades or not cargos:
        raise RuntimeError(
            "No hay OrganicUnit/ExecutivePosition para el backfill del perfil de usuario."
        )

    # Documentos/teléfonos ya usados para no violar UNIQUE.
    docs_usados = set(
        UserProfile.objects.exclude(numero_documento__isnull=True)
        .exclude(numero_documento="")
        .values_list("numero_documento", flat=True)
    )
    tels_usados = set(
        UserProfile.objects.exclude(telefono__isnull=True)
        .exclude(telefono="")
        .values_list("telefono", flat=True)
    )

    def nuevo_documento():
        while True:
            d = str(rng.randint(10_000_000, 99_999_999))  # 8 dígitos (DNI)
            if d not in docs_usados:
                docs_usados.add(d)
                return d

    def nuevo_telefono():
        while True:
            t = "9" + str(rng.randint(0, 99_999_999)).zfill(8)  # 9 dígitos, empieza en 9
            if t not in tels_usados:
                tels_usados.add(t)
                return t

    for user in User.objects.all().order_by("pk"):
        perfil = UserProfile.objects.filter(usuario=user).first()
        if perfil is None:
            # (a) crea el perfil faltante
            perfil = UserProfile(usuario=user)

        # (b) rellena SOLO los campos vacíos/nulos, preservando datos reales
        if not perfil.tipo_documento:
            perfil.tipo_documento = "DNI"
        if not perfil.numero_documento:
            perfil.numero_documento = nuevo_documento()
        if not perfil.apellido_paterno:
            partes = (user.last_name or "").split(" ")
            perfil.apellido_paterno = partes[0] or rng.choice(APELLIDOS)
        if not perfil.apellido_materno:
            perfil.apellido_materno = rng.choice(APELLIDOS)
        if not perfil.telefono:
            perfil.telefono = nuevo_telefono()
        if perfil.unidad_organica_id is None:
            perfil.unidad_organica_id = rng.choice(unidades)  # fila real existente
        if perfil.cargo_id is None:
            perfil.cargo_id = rng.choice(cargos)  # fila real existente
        # tiene_ficha_usuario queda en False (default) para el backfill.
        perfil.save()


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0008_userprofile_organic_unit"),
    ]

    operations = [
        # 1. AddField seguro (default cubre las filas existentes).
        migrations.AddField(
            model_name="userprofile",
            name="tiene_ficha_usuario",
            field=models.BooleanField(
                default=False,
                db_column="tiene_ficha_usuario",
                help_text="Indica si la ficha del usuario está completa/validada",
                verbose_name="tiene ficha de usuario",
            ),
        ),
        # 2. Backfill de datos. Los AlterField a NOT NULL viven en la 0010.
        migrations.RunPython(backfill_perfiles, migrations.RunPython.noop),
    ]
