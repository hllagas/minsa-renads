# Generated manually — rename in-place OrganDirectory → OrganicUnit
#
# Rename completo de la entidad `OrganDirectory` (tabla `organo_directorio`) a
# `OrganicUnit` (tabla `unidad_organica`), preservando datos. Se usan únicamente
# operaciones de rename/alter (RenameModel/AlterModelTable/RenameField/AlterField/
# RemoveConstraint/AddConstraint/AlterUniqueTogether/AlterModelOptions), que se traducen
# a `ALTER TABLE ... RENAME` — NO se recrean tablas (nada de CreateModel/DeleteModel).
#
# Columnas FK entrantes renombradas a `unidad_organica_id`:
#   - cargo_ejecutivo.organo_directivo_id
#   - convenio.organo_directorio_id
#   - parte_convenio.organo_directorio_id
#   - evaluacion_tecnica.organo_directorio_id
# (UserProfile.unidad_organica ya usa la columna `unidad_organica_id`: su AlterField
#  vive en la migración dependiente de `apps.common`.)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0053_professionalcareer_orden"),
    ]

    operations = [
        # 1. Renombrar el modelo y fijar la tabla física (organo_directorio → unidad_organica).
        migrations.RenameModel(
            old_name="OrganDirectory",
            new_name="OrganicUnit",
        ),
        migrations.AlterModelTable(
            name="organicunit",
            table="unidad_organica",
        ),
        # 2. Opciones del modelo (verbose_name / verbose_name_plural).
        migrations.AlterModelOptions(
            name="organicunit",
            options={
                "verbose_name": "unidad orgánica",
                "verbose_name_plural": "unidades orgánicas",
            },
        ),
        # 3. Renombrar el constraint de unicidad (organo, nombre).
        migrations.RemoveConstraint(
            model_name="organicunit",
            name="uniq_organo_dir_organo_nombre",
        ),
        migrations.AddConstraint(
            model_name="organicunit",
            constraint=models.UniqueConstraint(
                fields=["organo", "nombre"],
                name="uniq_unidad_organica_organo_nombre",
            ),
        ),
        # 4. FK entrantes: rename de atributo + AlterField de db_column/to.
        # F1 — ExecutivePosition.organo_directivo → unidad_organica.
        # (El help_text de la FK `organo` cita ahora `unidad_organica.organo`.)
        migrations.AlterField(
            model_name="executiveposition",
            name="organo",
            field=models.ForeignKey(
                db_column="organo_id",
                help_text=(
                    "Categoría de órgano (FK a la tabla canónica `organo`) a la que "
                    "pertenece el cargo; debe coincidir con unidad_organica.organo "
                    "cuando este está seteado"
                ),
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cargos_ejecutivos",
                to="convenios.organ",
                verbose_name="órgano",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="executiveposition",
            unique_together=set(),
        ),
        migrations.RenameField(
            model_name="executiveposition",
            old_name="organo_directivo",
            new_name="unidad_organica",
        ),
        migrations.AlterField(
            model_name="executiveposition",
            name="unidad_organica",
            field=models.ForeignKey(
                blank=True,
                db_column="unidad_organica_id",
                help_text="Unidad orgánica a la que pertenece el cargo",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cargos",
                to="convenios.organicunit",
                verbose_name="unidad orgánica",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="executiveposition",
            unique_together={("unidad_organica", "nombre_masculino")},
        ),
        migrations.AlterModelOptions(
            name="executiveposition",
            options={
                "ordering": ["unidad_organica", "nombre_masculino"],
                "verbose_name": "cargo ejecutivo",
            },
        ),
        # F2 — Convention.organo_directorio → unidad_organica.
        migrations.RenameField(
            model_name="convention",
            old_name="organo_directorio",
            new_name="unidad_organica",
        ),
        migrations.AlterField(
            model_name="convention",
            name="unidad_organica",
            field=models.ForeignKey(
                db_column="unidad_organica_id",
                help_text="Unidad orgánica (GERESA/DIRESA/DIRIS) parte del convenio.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="convenios",
                to="convenios.organicunit",
            ),
        ),
        # F3 — ConventionParty.organo_directorio → unidad_organica.
        migrations.RenameField(
            model_name="conventionparty",
            old_name="organo_directorio",
            new_name="unidad_organica",
        ),
        migrations.AlterField(
            model_name="conventionparty",
            name="unidad_organica",
            field=models.ForeignKey(
                db_column="unidad_organica_id",
                help_text="Unidad orgánica que representa la parte",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="convenios.organicunit",
            ),
        ),
        # F4 — TechnicalEvaluation.organo_directorio → unidad_organica.
        migrations.RenameField(
            model_name="technicalevaluation",
            old_name="organo_directorio",
            new_name="unidad_organica",
        ),
        migrations.AlterField(
            model_name="technicalevaluation",
            name="unidad_organica",
            field=models.ForeignKey(
                blank=True,
                db_column="unidad_organica_id",
                help_text="Unidad evaluadora (DIGEP) — unidad orgánica",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="convenios.organicunit",
            ),
        ),
    ]
