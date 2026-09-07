# Hand-written: OrganRepresentative(+History) FK organo_directorio → entidad polimórfica.
#
# Pasos: 1) agregar tipo_contenido/id_objeto nullables; 2) data migration poblar desde
# organo_directorio (todas las filas actuales son OrganDirectory); 3) volverlos NOT NULL;
# 4) eliminar la FK organo_directorio (decisión D2 del spec); 5) índice de entidad.
#
# reverse_code repuebla organo_directorio desde id_objeto para las filas cuyo
# tipo_contenido es organdirectory (reversibilidad de los datos).

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F


def poblar_entidad(apps, schema_editor):
    OrganRepresentative = apps.get_model("convenios", "OrganRepresentative")
    OrganRepresentativeHistory = apps.get_model("convenios", "OrganRepresentativeHistory")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct, _ = ContentType.objects.get_or_create(
        app_label="convenios", model="organdirectory"
    )
    OrganRepresentative.objects.all().update(
        tipo_contenido=ct, id_objeto=F("organo_directorio_id")
    )
    OrganRepresentativeHistory.objects.all().update(
        tipo_contenido=ct, id_objeto=F("organo_directorio_id")
    )


def revertir_entidad(apps, schema_editor):
    OrganRepresentative = apps.get_model("convenios", "OrganRepresentative")
    OrganRepresentativeHistory = apps.get_model("convenios", "OrganRepresentativeHistory")
    ContentType = apps.get_model("contenttypes", "ContentType")
    try:
        ct = ContentType.objects.get(app_label="convenios", model="organdirectory")
    except ContentType.DoesNotExist:
        return
    OrganRepresentative.objects.filter(tipo_contenido=ct).update(
        organo_directorio_id=F("id_objeto")
    )
    OrganRepresentativeHistory.objects.filter(tipo_contenido=ct).update(
        organo_directorio_id=F("id_objeto")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("convenios", "0037_organdirectory_uniq_por_gore"),
    ]

    operations = [
        # 1) Campos genéricos nullables (temporal).
        migrations.AddField(
            model_name="organrepresentative",
            name="tipo_contenido",
            field=models.ForeignKey(
                null=True, db_column="tipo_contenido_id", related_name="+",
                on_delete=django.db.models.deletion.PROTECT, to="contenttypes.contenttype",
                help_text="Tipo de entidad representada (ContentType)",
            ),
        ),
        migrations.AddField(
            model_name="organrepresentative",
            name="id_objeto",
            field=models.PositiveIntegerField(
                null=True, db_column="id_objeto", verbose_name="id del objeto",
                help_text="Id de la entidad representada",
            ),
        ),
        migrations.AddField(
            model_name="organrepresentativehistory",
            name="tipo_contenido",
            field=models.ForeignKey(
                null=True, db_column="tipo_contenido_id", related_name="+",
                on_delete=django.db.models.deletion.PROTECT, to="contenttypes.contenttype",
                help_text="Tipo de entidad representada (ContentType)",
            ),
        ),
        migrations.AddField(
            model_name="organrepresentativehistory",
            name="id_objeto",
            field=models.PositiveIntegerField(
                null=True, db_column="id_objeto", verbose_name="id del objeto",
                help_text="Id de la entidad representada",
            ),
        ),
        # 2) Data migration: poblar desde organo_directorio.
        migrations.RunPython(poblar_entidad, revertir_entidad),
        # 3) Volver NOT NULL.
        migrations.AlterField(
            model_name="organrepresentative",
            name="tipo_contenido",
            field=models.ForeignKey(
                db_column="tipo_contenido_id", related_name="+",
                on_delete=django.db.models.deletion.PROTECT, to="contenttypes.contenttype",
                help_text="Tipo de entidad representada (ContentType)",
            ),
        ),
        migrations.AlterField(
            model_name="organrepresentative",
            name="id_objeto",
            field=models.PositiveIntegerField(
                db_column="id_objeto", verbose_name="id del objeto",
                help_text="Id de la entidad representada",
            ),
        ),
        migrations.AlterField(
            model_name="organrepresentativehistory",
            name="tipo_contenido",
            field=models.ForeignKey(
                db_column="tipo_contenido_id", related_name="+",
                on_delete=django.db.models.deletion.PROTECT, to="contenttypes.contenttype",
                help_text="Tipo de entidad representada (ContentType)",
            ),
        ),
        migrations.AlterField(
            model_name="organrepresentativehistory",
            name="id_objeto",
            field=models.PositiveIntegerField(
                db_column="id_objeto", verbose_name="id del objeto",
                help_text="Id de la entidad representada",
            ),
        ),
        # 4) Eliminar la FK organo_directorio (D2).
        migrations.RemoveField(model_name="organrepresentative", name="organo_directorio"),
        migrations.RemoveField(model_name="organrepresentativehistory", name="organo_directorio"),
        # 5) Índice de entidad + opciones de modelo.
        migrations.AddIndex(
            model_name="organrepresentative",
            index=models.Index(
                fields=["tipo_contenido", "id_objeto"], name="idx_org_repr_entidad"
            ),
        ),
        migrations.AlterModelOptions(
            name="organrepresentative",
            options={
                "ordering": ["id"],
                "verbose_name": "representante de entidad",
                "verbose_name_plural": "representantes de entidad",
            },
        ),
    ]
