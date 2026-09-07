# Hand-written: unicidad de órgano del directorio por gobierno regional.
#
# 1) Fusiona duplicados existentes: por cada gobierno regional con >1 órgano del
#    directorio, conserva el de menor id (canónico), repunta todas las FK que
#    apuntaban a los duplicados hacia el canónico y borra los duplicados.
# 2) Añade la constraint parcial que impide futuros duplicados por GORE.

from collections import defaultdict

from django.db import migrations, models


def _repuntar_referencias(OrganDirectory, old_pk, new_pk):
    """Reapunta toda FK/O2O inversa de `old_pk` hacia `new_pk`.

    Genérico: recorre las relaciones inversas del modelo histórico, así no hay que
    enumerar a mano cada modelo que referencia a OrganDirectory (Convention,
    ConventionParty, TechnicalEvaluation, OrganRepresentative, ExecutivePosition,
    ExecutingUnit, University, …).
    """
    for rel in OrganDirectory._meta.related_objects:
        modelo_rel = rel.related_model
        campo = rel.field.name
        modelo_rel._default_manager.filter(**{campo: old_pk}).update(**{campo: new_pk})


def fusionar_duplicados(apps, schema_editor):
    OrganDirectory = apps.get_model("convenios", "OrganDirectory")

    grupos = defaultdict(list)
    for od in (
        OrganDirectory._default_manager.filter(gobierno_regional__isnull=False)
        .order_by("id")
    ):
        grupos[od.gobierno_regional_id].append(od)

    for filas in grupos.values():
        if len(filas) < 2:
            continue
        canonico, *duplicados = filas  # menor id = canónico
        for dup in duplicados:
            _repuntar_referencias(OrganDirectory, dup.pk, canonico.pk)
            dup.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('convenios', '0036_alter_ipress_codigo_renipress'),
    ]

    operations = [
        migrations.RunPython(fusionar_duplicados, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='organdirectory',
            constraint=models.UniqueConstraint(
                condition=models.Q(('gobierno_regional__isnull', False)),
                fields=('gobierno_regional',),
                name='uniq_organo_directorio_por_gore',
            ),
        ),
    ]
