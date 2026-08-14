"""Refactor de campos clínicos.

Separa la antigua tabla `campo_clinico` (`ClinicalField`) en:
- `campo_clinico_ipress` (`ClinicalFieldRegistration`) — registro CONAPRES del total
  de campos clínicos por sede docente + carrera.
- `campo_clinico_ipress_universidad` (`ClinicalFieldAllocation`) — asignación por
  universidad (Órgano Regional).

La data migration crea, por cada registro existente, una asignación con la
universidad del convenio, `campos_clinicos_autorizados = campos_clinicos_registrados`
y las fechas de vigencia del registro (o del convenio como respaldo); luego recalcula
`campos_clinicos_asignados`. Se leen `vigencia_inicio`/`vigencia_fin` ANTES de
eliminarlos.

**Migración irreversible en sentido inverso:** al revertir, el re-alta de los campos
legado eliminados (`ambito_geografico_sanitario_id` FK NOT NULL, sin default) provoca
`IntegrityError` si existen filas, y los datos de vigencia/ámbito ya no son
recuperables. La ruta forward (producción) es la soportada; no se contempla revertir.
"""

from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


def crear_asignaciones_iniciales(apps, schema_editor):
    """Crea 1 asignación por registro existente y actualiza el acumulador."""
    ClinicalFieldRegistration = apps.get_model("convenios", "ClinicalFieldRegistration")
    ClinicalFieldAllocation = apps.get_model("convenios", "ClinicalFieldAllocation")

    for registro in ClinicalFieldRegistration.objects.all():
        convenio = registro.convenio
        # Fechas: preferir las de vigencia del registro (aún presentes en este punto),
        # con respaldo en las del convenio.
        fecha_inicio = registro.vigencia_inicio or convenio.fecha_inicio
        fecha_fin = registro.vigencia_fin or convenio.fecha_fin

        ClinicalFieldAllocation.objects.create(
            campo_clinico_ipress=registro,
            convenio=convenio,
            ipress=registro.ipress,
            carrera_profesional=registro.carrera_profesional,
            especialidad=registro.especialidad,
            universidad=convenio.universidad,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            campos_clinicos_autorizados=registro.campos_clinicos_registrados,
        )
        registro.campos_clinicos_asignados = registro.campos_clinicos_registrados
        registro.save(update_fields=["campos_clinicos_asignados", "actualizado_en"])


def borrar_asignaciones_iniciales(apps, schema_editor):
    """Reverso: elimina todas las asignaciones (se recrean al reaplicar)."""
    ClinicalFieldAllocation = apps.get_model("convenios", "ClinicalFieldAllocation")
    ClinicalFieldRegistration = apps.get_model("convenios", "ClinicalFieldRegistration")
    ClinicalFieldAllocation.objects.all().delete()
    ClinicalFieldRegistration.objects.all().update(campos_clinicos_asignados=0)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("convenios", "0014_category_classificationtype_microred_and_more"),
    ]

    operations = [
        # 1. Renombrar el modelo y la tabla.
        migrations.RenameModel(
            old_name="ClinicalField",
            new_name="ClinicalFieldRegistration",
        ),
        migrations.AlterModelTable(
            name="clinicalfieldregistration",
            table="campo_clinico_ipress",
        ),
        migrations.AlterModelOptions(
            name="clinicalfieldregistration",
            options={
                "verbose_name": "registro de campos clínicos por sede",
                "verbose_name_plural": "registros de campos clínicos por sede",
            },
        ),
        # 2. Renombrar el conteo y añadir el acumulador + auditoría.
        migrations.RenameField(
            model_name="clinicalfieldregistration",
            old_name="cantidad_maxima",
            new_name="campos_clinicos_registrados",
        ),
        migrations.AlterField(
            model_name="clinicalfieldregistration",
            name="campos_clinicos_registrados",
            field=models.PositiveIntegerField(
                help_text="Total de campos clínicos registrados por CONAPRES para la sede y carrera",
                verbose_name="campos clínicos registrados",
            ),
        ),
        migrations.AddField(
            model_name="clinicalfieldregistration",
            name="campos_clinicos_asignados",
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    "Acumulador Σ de los campos autorizados en las asignaciones por "
                    "universidad; recalculado por el service (solo lectura en la API)"
                ),
                verbose_name="campos clínicos asignados",
            ),
        ),
        migrations.AddField(
            model_name="clinicalfieldregistration",
            name="creado_por",
            field=models.ForeignKey(
                blank=True,
                db_column="creado_por",
                help_text="Usuario que creó el registro",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="clinicalfieldregistration",
            name="actualizado_en",
            field=models.DateTimeField(auto_now=True, verbose_name="actualizado en"),
        ),
        migrations.AddField(
            model_name="clinicalfieldregistration",
            name="actualizado_por",
            field=models.ForeignKey(
                blank=True,
                db_column="actualizado_por",
                help_text="Usuario que actualizó el registro",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="clinicalfieldregistration",
            unique_together={("convenio", "ipress", "carrera_profesional", "especialidad")},
        ),
        # 3. Crear el modelo de asignación por universidad.
        migrations.CreateModel(
            name="ClinicalFieldAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha_inicio", models.DateField(help_text="Inicio de vigencia de la asignación", verbose_name="fecha de inicio")),
                ("fecha_fin", models.DateField(help_text="Fin de vigencia de la asignación", verbose_name="fecha de fin")),
                ("campos_clinicos_autorizados", models.PositiveIntegerField(help_text="Cupos autorizados para la universidad", verbose_name="campos clínicos autorizados")),
                ("creado_en", models.DateTimeField(auto_now_add=True, verbose_name="creado en")),
                ("actualizado_en", models.DateTimeField(auto_now=True, verbose_name="actualizado en")),
                (
                    "campo_clinico_ipress",
                    models.ForeignKey(
                        db_column="campo_clinico_ipress_id",
                        help_text="Registro de campos clínicos (sede + carrera)",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="asignaciones",
                        to="convenios.clinicalfieldregistration",
                    ),
                ),
                (
                    "convenio",
                    models.ForeignKey(
                        db_column="convenio_id",
                        help_text="Convenio Específico vigente que respalda la asignación",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="convenios.convention",
                    ),
                ),
                (
                    "ipress",
                    models.ForeignKey(
                        db_column="ipress_id",
                        help_text="Sede docente (establecimiento)",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="convenios.ipress",
                    ),
                ),
                (
                    "carrera_profesional",
                    models.ForeignKey(
                        db_column="carrera_profesional_id",
                        help_text="Carrera / programa académico",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="convenios.professionalcareer",
                    ),
                ),
                (
                    "especialidad",
                    models.ForeignKey(
                        blank=True,
                        db_column="especialidad_id",
                        help_text="Especialidad",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="convenios.specialty",
                    ),
                ),
                (
                    "universidad",
                    models.ForeignKey(
                        db_column="universidad_id",
                        help_text="Universidad a la que se asignan los cupos",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="campos_clinicos_asignados",
                        to="convenios.university",
                    ),
                ),
                (
                    "creado_por",
                    models.ForeignKey(
                        blank=True,
                        db_column="creado_por",
                        help_text="Usuario que creó la asignación",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "actualizado_por",
                    models.ForeignKey(
                        blank=True,
                        db_column="actualizado_por",
                        help_text="Usuario que actualizó la asignación",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "asignación de campos clínicos por universidad",
                "verbose_name_plural": "asignaciones de campos clínicos por universidad",
                "db_table": "campo_clinico_ipress_universidad",
                "unique_together": {("campo_clinico_ipress", "universidad", "convenio")},
            },
        ),
        # 4. Data migration: crear 1 asignación por registro y recalcular el acumulador
        #    (lee vigencia_inicio/fin ANTES del RemoveField de abajo).
        migrations.RunPython(crear_asignaciones_iniciales, borrar_asignaciones_iniciales),
        # 5. Eliminar los campos legado del registro (tras mover los datos).
        migrations.RemoveField(model_name="clinicalfieldregistration", name="vigencia_inicio"),
        migrations.RemoveField(model_name="clinicalfieldregistration", name="vigencia_fin"),
        migrations.RemoveField(model_name="clinicalfieldregistration", name="ambito_geografico_sanitario"),
        migrations.RemoveField(model_name="clinicalfieldregistration", name="observaciones"),
    ]
