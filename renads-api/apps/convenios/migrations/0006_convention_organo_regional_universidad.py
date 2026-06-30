"""Agrega las FK obligatorias `organo_regional` y `universidad` a `convenio`.

Estrategia para no romper filas existentes: se agregan como nullable, se rellenan
con la primera entidad disponible (backfill) y luego se vuelven NOT NULL. En una base
sin convenios previos (despliegue nuevo) el backfill no aplica.
"""

from django.db import migrations, models
import django.db.models.deletion


def backfill(apps, schema_editor):
    Convention = apps.get_model("convenios", "Convention")
    RegionalOrgan = apps.get_model("convenios", "RegionalOrgan")
    University = apps.get_model("convenios", "University")

    organo = RegionalOrgan.objects.order_by("id").first()
    universidad = University.objects.order_by("id").first()

    pendientes = Convention.objects.filter(
        models.Q(organo_regional__isnull=True) | models.Q(universidad__isnull=True)
    )
    if not pendientes.exists():
        return
    if organo is None or universidad is None:
        raise RuntimeError(
            "No se puede rellenar convenio.organo_regional/universidad: "
            "se requiere al menos un órgano regional y una universidad."
        )
    pendientes.update(organo_regional=organo, universidad=universidad)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0005_ubigeo_executingunit_direccion_ipress_direccion_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="convention",
            name="organo_regional",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="convenios",
                db_column="organo_regional_id",
                to="convenios.regionalorgan",
                help_text=(
                    "Órgano regional (GERESA/DIRESA/DIRIS) parte del convenio. "
                    "Su tipo se deriva de esta relación."
                ),
            ),
        ),
        migrations.AddField(
            model_name="convention",
            name="universidad",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="convenios",
                db_column="universidad_id",
                to="convenios.university",
                help_text=(
                    "Universidad parte del convenio. "
                    "Su tipo de entidad se deriva de esta relación."
                ),
            ),
        ),
        migrations.RunPython(backfill, noop),
        migrations.AlterField(
            model_name="convention",
            name="organo_regional",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="convenios",
                db_column="organo_regional_id",
                to="convenios.regionalorgan",
                help_text=(
                    "Órgano regional (GERESA/DIRESA/DIRIS) parte del convenio. "
                    "Su tipo se deriva de esta relación."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="convention",
            name="universidad",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="convenios",
                db_column="universidad_id",
                to="convenios.university",
                help_text=(
                    "Universidad parte del convenio. "
                    "Su tipo de entidad se deriva de esta relación."
                ),
            ),
        ),
    ]
