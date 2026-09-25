# Reapunta la FK `UserProfile.unidad_organica` al modelo renombrado
# `convenios.OrganicUnit` (antes `convenios.OrganDirectory`).
#
# NO renombra la columna: `unidad_organica_id` ya existía (introducida en la
# migración `common 0006`). Es un `AlterField` menor del `to=` que solo actualiza
# el estado del modelo; depende de la 0054 de convenios (donde el modelo cambia de
# nombre) para que `convenios.organicunit` exista.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0007_unaccent_extension"),
        ("convenios", "0054_rename_organic_unit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="unidad_organica",
            field=models.ForeignKey(
                blank=True,
                db_column="unidad_organica_id",
                help_text="Unidad orgánica a la que pertenece el usuario",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="perfiles_usuarios",
                to="convenios.organicunit",
                verbose_name="unidad orgánica",
            ),
        ),
    ]
