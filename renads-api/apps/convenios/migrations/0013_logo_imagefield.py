"""Migra `referencia_logo` de `CharField` a `ImageField` en las 5 entidades con logo.

Etapa 4 de `spec/almacenamiento.md`. El cambio es de **tipo de campo Django**
(`CharField` -> `ImageField`), no de esquema físico: la columna sigue siendo
`referencia_logo` `varchar(500)`. Por eso son 5 `AlterField` **no destructivos de
datos** (los paths/keys existentes se preservan como texto).

Nota de backfill (E4.T5.2): no se incluye data migration. Se asume que el entorno
objetivo **no tiene logos cargados** con el flujo anterior (backend custom con keys
`{GCS_OBJECT_PREFIX}/{uuid4}-{nombre}`). Si hubiera datos productivos, esas keys NO
coinciden con el layout `upload_to` de `ImageField` (`<carpeta_entidad>/...`) ni con
el `GS_LOCATION` de django-storages, por lo que `.url` podría no resolver el binario;
en ese caso habría que recolocar/renombrar los objetos en el bucket y actualizar los
paths manualmente. `null=True` además permite normalizar `""` -> `NULL` si se desea.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('convenios', '0012_document_texto_extraido'),
    ]

    operations = [
        migrations.AlterField(
            model_name='executingunit',
            name='referencia_logo',
            field=models.ImageField(blank=True, help_text='Logo institucional (imagen almacenada en el repositorio de medios)', max_length=500, null=True, upload_to='unidad_ejecutora/', verbose_name='logo'),
        ),
        migrations.AlterField(
            model_name='ipress',
            name='referencia_logo',
            field=models.ImageField(blank=True, help_text='Logo institucional (imagen almacenada en el repositorio de medios)', max_length=500, null=True, upload_to='ipress/', verbose_name='logo'),
        ),
        migrations.AlterField(
            model_name='regionalgovernment',
            name='referencia_logo',
            field=models.ImageField(blank=True, help_text='Logo institucional (imagen almacenada en el repositorio de medios)', max_length=500, null=True, upload_to='gobierno_regional/', verbose_name='logo'),
        ),
        migrations.AlterField(
            model_name='regionalorgan',
            name='referencia_logo',
            field=models.ImageField(blank=True, help_text='Logo institucional (imagen almacenada en el repositorio de medios)', max_length=500, null=True, upload_to='organo_regional/', verbose_name='logo'),
        ),
        migrations.AlterField(
            model_name='university',
            name='referencia_logo',
            field=models.ImageField(blank=True, help_text='Logo institucional (imagen almacenada en el repositorio de medios)', max_length=500, null=True, upload_to='universidad/', verbose_name='logo'),
        ),
    ]
