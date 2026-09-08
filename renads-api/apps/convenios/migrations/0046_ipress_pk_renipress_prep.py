"""Refactor de la PK de ``Ipress`` — parte A: verificación + columnas transitorias + swap de GFK.

VERIFICACIÓN DE DATOS PREVIA A LA MIGRACIÓN (T-01, Fase 0):
==========================================================
Consultas ejecutadas en ``python manage.py shell`` sobre la BD de desarrollo:

- ``Ipress.objects.exclude(codigo_renipress__regex=r'^.{1,8}$').values_list('pk','codigo_renipress')``
  → ``[]`` (ninguna fila con codigo_renipress > 8 chars, vacío o nulo).
- ``Ipress.objects.count()`` → 0 filas.
- ``Ipress.objects.values('codigo_renipress').distinct().count()`` → 0 (unicidad OK).
- ``ct_ipress = ContentType.objects.get_for_model(Ipress).id`` → 29.
- ``UserEntityProfile.objects.filter(tipo_contenido_id=ct_ipress).count()`` → 0 filas.
- ``AuditLog.objects.filter(tipo_contenido_id=ct_ipress).count()`` → 0 filas.

Conclusión: la tabla ``ipress`` y las filas GFK a remapear están vacías en dev; los
``RunPython`` son noop efectivos pero quedan correctos para producción (backfill real +
``RuntimeError`` ante integridad rota).

CONFIRMACIÓN DE GFK QUE APUNTAN A ``Ipress`` (análisis del spec):
================================================================
Solo ``UserEntityProfile.id_objeto`` y ``AuditLog.id_objeto`` referencian ``Ipress`` en
algún flujo (alcance institucional + auditoría de sede docente) → ambos cambian a
``CharField(64)``. Los otros 4 GFK (``Document``, ``ConventionParticipant``, ``Firma``,
``Convention.solicitante``) NO apuntan a ``Ipress`` y conservan ``PositiveBigIntegerField``.

Operaciones de esta migración:
1. AlterField ``Ipress.codigo_renipress`` → max_length=8 (aún no PK, sigue unique=True).
2. AddField columnas transitorias ``ipress_codigo`` en ClinicalFieldRegistration/Allocation.
3. RunPython backfill de ``ipress_codigo`` en ambos modelos de convenios.
4. AlterField ``UserEntityProfile.id_objeto`` y ``AuditLog.id_objeto`` → CharField(64).
5. RunPython remapeo de las filas GFK Ipress (id entero → codigo_renipress) tras el
   AlterField (evita coerción SQLite; las filas no-Ipress las castea el AlterField).
"""

from django.db import migrations, models


def backfill_ipress_codigo_convenios(apps, schema_editor):
    """Copia ``Ipress.codigo_renipress`` en la columna transitoria de las 2 FK de convenios."""
    ClinicalFieldRegistration = apps.get_model("convenios", "ClinicalFieldRegistration")
    ClinicalFieldAllocation = apps.get_model("convenios", "ClinicalFieldAllocation")
    Ipress = apps.get_model("convenios", "Ipress")

    codigo_por_id = {ip.id: ip.codigo_renipress for ip in Ipress.objects.all()}

    for modelo, etiqueta in ((ClinicalFieldRegistration, "campo_clinico_ipress"),
                             (ClinicalFieldAllocation, "campo_clinico_ipress_universidad")):
        for fila in modelo.objects.filter(ipress_id__isnull=False):
            codigo = codigo_por_id.get(fila.ipress_id)
            if codigo is None:
                raise RuntimeError(
                    f"Integridad referencial rota: la fila id={fila.id} de "
                    f"`{etiqueta}` referencia ipress_id={fila.ipress_id} que no existe "
                    "en la tabla `ipress`. Corrija los datos antes de aplicar la migración."
                )
            fila.ipress_codigo = codigo
            fila.save(update_fields=["ipress_codigo"])


def remapear_gfk_ipress(apps, schema_editor):
    """Sobre-escribe ``id_objeto`` de las filas GFK Ipress con el ``codigo_renipress``.

    Se ejecuta tras el ``AlterField`` de ``id_objeto`` a ``CharField(64)``: las filas
    no-Ipress ya quedaron con su id entero casteado a str automáticamente por SQLite;
    aquí solo se corrigen las filas cuyo ``tipo_contenido`` es ``Ipress``, cuyo valor
    debe ser el código RENIPRESS y no el antiguo id entero.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    Ipress = apps.get_model("convenios", "Ipress")
    UserEntityProfile = apps.get_model("convenios", "UserEntityProfile")
    AuditLog = apps.get_model("convenios", "AuditLog")

    try:
        ct_ipress = ContentType.objects.get(app_label="convenios", model="ipress").id
    except ContentType.DoesNotExist:
        return

    codigo_por_id = {str(ip.id): ip.codigo_renipress for ip in Ipress.objects.all()}

    for modelo, etiqueta in ((UserEntityProfile, "perfil_usuario_entidad"),
                             (AuditLog, "bitacora_auditoria")):
        for fila in modelo.objects.filter(tipo_contenido_id=ct_ipress):
            id_actual = str(fila.id_objeto)
            codigo = codigo_por_id.get(id_actual)
            if codigo is None:
                raise RuntimeError(
                    f"Integridad referencial rota: la fila id={fila.id} de "
                    f"`{etiqueta}` referencia una Ipress id_objeto={id_actual} que no "
                    "existe en la tabla `ipress`. Corrija los datos antes de migrar."
                )
            fila.id_objeto = codigo
            fila.save(update_fields=["id_objeto"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0045_executingunit_nueva_estructura"),
    ]

    operations = [
        # Paso 1: acortar codigo_renipress a 8 chars (aún no PK).
        migrations.AlterField(
            model_name="ipress",
            name="codigo_renipress",
            field=models.CharField(
                verbose_name="código RENIPRESS",
                max_length=8,
                unique=True,
                help_text="Código único RENIPRESS del establecimiento",
            ),
        ),

        # Paso 2: columnas transitorias en las 2 FK de convenios (db_column distinto).
        migrations.AddField(
            model_name="clinicalfieldregistration",
            name="ipress_codigo",
            field=models.CharField(
                max_length=8,
                null=True,
                blank=True,
                db_column="ipress_codigo",
                help_text="Campo transitorio: código RENIPRESS de la sede (futura FK textual)",
            ),
        ),
        migrations.AddField(
            model_name="clinicalfieldallocation",
            name="ipress_codigo",
            field=models.CharField(
                max_length=8,
                null=True,
                blank=True,
                db_column="ipress_codigo_asig",
                help_text="Campo transitorio: código RENIPRESS de la sede (futura FK textual)",
            ),
        ),

        # Paso 3: backfill de las columnas transitorias de convenios.
        migrations.RunPython(
            backfill_ipress_codigo_convenios, reverse_code=migrations.RunPython.noop
        ),

        # Paso 4: id_objeto genérico → CharField(64) (castea filas no-Ipress a str).
        migrations.AlterField(
            model_name="userentityprofile",
            name="id_objeto",
            field=models.CharField(
                verbose_name="id objeto",
                max_length=64,
                help_text="Identificador de la entidad asociada",
            ),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="id_objeto",
            field=models.CharField(
                verbose_name="id objeto",
                max_length=64,
                help_text="Registro afectado",
            ),
        ),

        # Paso 5: remapeo de las filas GFK Ipress (id entero → codigo_renipress).
        migrations.RunPython(
            remapear_gfk_ipress, reverse_code=migrations.RunPython.noop
        ),
    ]
