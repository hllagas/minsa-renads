"""Refactor de entidades (1/3): schema aditivo, sin destruir datos.

Añade la columna `organo_directorio.categoria` (temporalmente nullable para el
backfill), los nuevos campos de `gobierno_regional` (`ubigeo`, `sigla`) y de
`facultad` (`referencia_logo`, `ubigeo`), y refactoriza `cargo_ejecutivo`
(rename `nombre`→`nombre_masculino`, add `nombre_femenino`). NO borra nada ni
cambia constraints de FK: eso ocurre en 0029 (datos) y 0030 (destructivo final).
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0027_move_contact_fields_to_regional_government"),
    ]

    operations = [
        # 1. organo_directorio.categoria (nullable temporal para permitir backfill en 0029).
        migrations.AddField(
            model_name="organdirectory",
            name="categoria",
            field=models.CharField(
                verbose_name="categoría",
                max_length=20,
                null=True,
                db_column="categoria",
                choices=[
                    ("ORGANO_MINSA", "Órgano del MINSA"),
                    ("UNIVERSIDAD", "Universidad"),
                    ("GOBIERNO_REGIONAL", "Gobierno Regional"),
                    ("MINSA_DIRIS", "MINSA DIRIS"),
                    ("UNIDAD_EJECUTORA", "Unidad Ejecutora"),
                ],
                help_text="Categoría del órgano (discriminador)",
            ),
        ),
        # 2. gobierno_regional: ubigeo + sigla.
        migrations.AddField(
            model_name="regionalgovernment",
            name="sigla",
            field=models.CharField(
                verbose_name="sigla",
                max_length=50,
                blank=True,
                default="",
                help_text="Sigla del gobierno regional",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="regionalgovernment",
            name="ubigeo",
            field=models.ForeignKey(
                to="convenios.ubigeo",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ubigeo_id",
                null=True,
                blank=True,
                related_name="+",
                help_text="Ubicación geográfica (UBIGEO)",
            ),
        ),
        # 3. facultad: referencia_logo + ubigeo.
        migrations.AddField(
            model_name="faculty",
            name="ubigeo",
            field=models.ForeignKey(
                to="convenios.ubigeo",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ubigeo_id",
                null=True,
                blank=True,
                related_name="+",
                help_text="Ubicación geográfica (UBIGEO)",
            ),
        ),
        migrations.AddField(
            model_name="faculty",
            name="referencia_logo",
            field=models.ImageField(
                verbose_name="logo",
                upload_to="facultad/",
                max_length=500,
                null=True,
                blank=True,
                help_text="Logo institucional (imagen almacenada en el repositorio de medios)",
            ),
        ),
        # 4. cargo_ejecutivo: rename nombre→nombre_masculino, add nombre_femenino.
        #    NO se toca `codigo`, `unique_together` ni `ordering` aquí (van en 0030).
        migrations.RenameField(
            model_name="executiveposition",
            old_name="nombre",
            new_name="nombre_masculino",
        ),
        migrations.AlterField(
            model_name="executiveposition",
            name="nombre_masculino",
            field=models.CharField(
                verbose_name="nombre (masculino)",
                max_length=255,
                help_text="Nombre del cargo en masculino",
            ),
        ),
        migrations.AddField(
            model_name="executiveposition",
            name="nombre_femenino",
            field=models.CharField(
                verbose_name="nombre (femenino)",
                max_length=255,
                blank=True,
                default="",
                help_text="Nombre del cargo en femenino",
            ),
            preserve_default=False,
        ),
    ]
