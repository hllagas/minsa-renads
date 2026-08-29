from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0011_seed_document_type_anexo"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="texto_extraido",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Texto extraído del PDF por Document AI (vacío si no aplica o falló)",
                verbose_name="texto extraído",
            ),
        ),
    ]
