from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0028_rename_periodo_academico_to_periodo_internado"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="student",
            name="codigo_universitario",
        ),
    ]
