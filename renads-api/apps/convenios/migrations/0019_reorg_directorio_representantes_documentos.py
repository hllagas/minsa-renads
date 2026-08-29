"""Reorganización de directorio de órganos, representantes y gestión documental.

Cambios:
1. `cargo_ejecutivo` deja de heredar `Catalog`: añade FK `organo`, `unique_together`
   (organo, codigo).
2. Unifica `organo_regional` + `organo_minsa` en `organo_directorio` (`OrganDirectory`).
   Repunta las FKs de `unidad_ejecutora`, `convenio` y `evaluacion_tecnica`.
3. Unifica `representante` + `autoridad_universidad` en `organo_representante`
   (`OrganRepresentative`) con FK directo al directorio, más el histórico de bajas
   `historial_organo_representante` (`OrganRepresentativeHistory`).
4. Renombra `documento` → `documento_adjunto`; `documento_anexo` pasa a NOT NULL
   (único discriminador de versionado); elimina `nombre_archivo`, `texto_extraido`,
   `tipo_documento`. Elimina `DocumentType` y su tabla `tipo_documento`.

BD de desarrollo recreable limpia: sin transferencia fila por fila. La migración
resiembra cargos ejecutivos por órgano y los anexos genéricos absorbidos de
`tipo_documento`.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


# ---------------------------------------------------------------------------
# Reseed — cargos ejecutivos por órgano y anexos genéricos
# ---------------------------------------------------------------------------
def _slug(texto: str) -> str:
    """Código estable en mayúsculas a partir del nombre del cargo."""
    import unicodedata

    normal = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return "_".join(normal.upper().split())


CARGOS_POR_ORGANO = {
    "Universidad": ["Rector", "Vicerrector", "Decano", "Secretario General"],
    "Órgano Regional": [
        "Director General",
        "Gerente General",
        "Director Regional de Salud",
        "Director de Hospital III",
        "Director de DIRIS",
    ],
    "Órgano del MINSA": [
        "Ministro",
        "Viceministro",
        "Director General de Personal de Salud",
    ],
}

ANEXOS_GENERICOS = [
    ("ANEXO", "Anexo / declaración jurada"),
    ("CONVENIO", "Documento de convenio"),
    ("RESOLUCION", "Resolución"),
]


def reseed(apps, schema_editor):
    Organ = apps.get_model("convenios", "Organ")
    ExecutivePosition = apps.get_model("convenios", "ExecutivePosition")
    AnnexDocument = apps.get_model("internados", "AnnexDocument")

    for nombre_organo, cargos in CARGOS_POR_ORGANO.items():
        organo = Organ.objects.filter(nombre=nombre_organo).first()
        if organo is None:
            continue
        for cargo in cargos:
            ExecutivePosition.objects.get_or_create(
                organo=organo,
                codigo=_slug(cargo),
                defaults={"nombre": cargo, "activo": True},
            )

    for codigo, nombre in ANEXOS_GENERICOS:
        AnnexDocument.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "tipo_actor": "",
                "obligatorio": False,
                "activo": True,
            },
        )


def reseed_reverse(apps, schema_editor):
    AnnexDocument = apps.get_model("internados", "AnnexDocument")
    AnnexDocument.objects.filter(codigo__in=[c for c, _ in ANEXOS_GENERICOS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0018_normalize_organ_table"),
        ("internados", "0018_annexdocument_documento_anexo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ----------------------------------------------------------------
        # 1 — cargo_ejecutivo: dejar de heredar Catalog, añadir FK organo
        # ----------------------------------------------------------------
        migrations.AlterField(
            model_name="executiveposition",
            name="codigo",
            field=models.CharField(
                help_text="Código del cargo (único dentro del órgano)",
                max_length=50,
                verbose_name="código",
            ),
        ),
        migrations.AlterField(
            model_name="executiveposition",
            name="nombre",
            field=models.CharField(
                help_text="Nombre del cargo",
                max_length=255,
                verbose_name="nombre",
            ),
        ),
        migrations.AddField(
            model_name="executiveposition",
            name="organo",
            field=models.ForeignKey(
                default=1,
                db_column="organo_id",
                help_text="Categoría del órgano al que pertenece el cargo",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cargos",
                to="convenios.organ",
                verbose_name="órgano",
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="executiveposition",
            options={
                "ordering": ["organo", "codigo"],
                "verbose_name": "cargo ejecutivo",
            },
        ),
        migrations.AlterUniqueTogether(
            name="executiveposition",
            unique_together={("organo", "codigo")},
        ),
        # ----------------------------------------------------------------
        # 2 — Crear OrganDirectory (organo_directorio)
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="OrganDirectory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(help_text="Nombre del órgano", max_length=255, verbose_name="nombre")),
                ("siglas", models.CharField(blank=True, help_text="Siglas", max_length=50, verbose_name="siglas")),
                ("direccion", models.CharField(blank=True, help_text="Dirección", max_length=500, verbose_name="dirección")),
                ("numero_ruc", models.CharField(blank=True, help_text="RUC (11 dígitos; texto para conservar ceros a la izquierda)", max_length=11, verbose_name="número de RUC")),
                ("correo", models.EmailField(blank=True, help_text="Correo institucional", max_length=254, verbose_name="correo")),
                ("telefono_institucional", models.CharField(blank=True, help_text="Teléfono institucional", max_length=30, verbose_name="teléfono institucional")),
                ("referencia_logo", models.ImageField(blank=True, help_text="Logo institucional (imagen almacenada en el repositorio de medios)", max_length=500, null=True, upload_to="organo_directorio/", verbose_name="logo")),
                ("activo", models.BooleanField(default=True, verbose_name="activo")),
                ("gobierno_regional", models.ForeignKey(blank=True, db_column="gobierno_regional_id", help_text="GORE (solo órganos regionales)", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="organos_directorio", to="convenios.regionalgovernment")),
                ("organo", models.ForeignKey(db_column="organo_id", help_text="Categoría del órgano (discriminador)", on_delete=django.db.models.deletion.PROTECT, related_name="directorios", to="convenios.organ", verbose_name="órgano")),
                ("tipo_organo", models.ForeignKey(blank=True, db_column="tipo_organo_id", help_text="Tipo de órgano (GERESA/DIRESA/DIGEP…); nulo para órganos sin tipo", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="convenios.organtype")),
                ("ubigeo", models.ForeignKey(blank=True, db_column="ubigeo_id", help_text="Ubicación geográfica (UBIGEO)", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="convenios.ubigeo")),
            ],
            options={
                "verbose_name": "órgano del directorio",
                "verbose_name_plural": "órganos del directorio",
                "db_table": "organo_directorio",
            },
        ),
        # ----------------------------------------------------------------
        # 3 — Repuntar FKs (BD limpia, sin transferencia)
        # ----------------------------------------------------------------
        migrations.RemoveField(model_name="executingunit", name="organo_regional"),
        migrations.AddField(
            model_name="executingunit",
            name="organo_directorio",
            field=models.ForeignKey(
                default=1,
                db_column="organo_directorio_id",
                help_text="Órgano del directorio que la administra",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="unidades_ejecutoras",
                to="convenios.organdirectory",
            ),
            preserve_default=False,
        ),
        migrations.RemoveField(model_name="convention", name="organo_regional"),
        migrations.AddField(
            model_name="convention",
            name="organo_directorio",
            field=models.ForeignKey(
                default=1,
                db_column="organo_directorio_id",
                help_text="Órgano del directorio (GERESA/DIRESA/DIRIS) parte del convenio.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="convenios",
                to="convenios.organdirectory",
            ),
            preserve_default=False,
        ),
        migrations.RemoveField(model_name="technicalevaluation", name="organo_minsa"),
        migrations.AddField(
            model_name="technicalevaluation",
            name="organo_directorio",
            field=models.ForeignKey(
                blank=True,
                db_column="organo_directorio_id",
                help_text="Unidad evaluadora (DIGEP) del directorio",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="convenios.organdirectory",
            ),
        ),
        # ----------------------------------------------------------------
        # 4 — Eliminar RegionalOrgan y MinsaOrgan
        # ----------------------------------------------------------------
        migrations.DeleteModel(name="RegionalOrgan"),
        migrations.DeleteModel(name="MinsaOrgan"),
        # ----------------------------------------------------------------
        # 5 — Crear OrganRepresentative + OrganRepresentativeHistory
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="OrganRepresentative",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(help_text="Nombre del representante", max_length=255, verbose_name="nombre")),
                ("numero_documento_identidad", models.CharField(help_text="Número de documento de identidad", max_length=20, verbose_name="número de documento de identidad")),
                ("sexo", models.CharField(choices=[("M", "Masculino"), ("F", "Femenino")], help_text="Sexo (M/F)", max_length=1, verbose_name="sexo")),
                ("fecha_inicio_designacion", models.DateField(help_text="Inicio de la designación", verbose_name="fecha de inicio de designación")),
                ("numero_resolucion_designacion", models.CharField(blank=True, help_text="Número de resolución de designación", max_length=100, verbose_name="número de resolución de designación")),
                ("fecha_inicio_facultades", models.DateField(blank=True, help_text="Otorgamiento de facultades", null=True, verbose_name="fecha de inicio de facultades")),
                ("activo", models.BooleanField(default=True, verbose_name="activo")),
                ("cargo_ejecutivo", models.ForeignKey(db_column="cargo_ejecutivo_id", help_text="Cargo ejecutivo", on_delete=django.db.models.deletion.PROTECT, related_name="+", to="convenios.executiveposition")),
                ("organo_directorio", models.ForeignKey(db_column="organo_directorio_id", help_text="Órgano del directorio representado", on_delete=django.db.models.deletion.PROTECT, related_name="representantes", to="convenios.organdirectory")),
                ("tipo_documento_identidad", models.ForeignKey(db_column="tipo_documento_identidad_id", help_text="Tipo de documento de identidad", on_delete=django.db.models.deletion.PROTECT, related_name="+", to="internados.identitydocumenttype")),
            ],
            options={
                "verbose_name": "representante de órgano",
                "verbose_name_plural": "representantes de órgano",
                "db_table": "organo_representante",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="OrganRepresentativeHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(help_text="Nombre del representante", max_length=255, verbose_name="nombre")),
                ("numero_documento_identidad", models.CharField(help_text="Número de documento de identidad", max_length=20, verbose_name="número de documento de identidad")),
                ("sexo", models.CharField(choices=[("M", "Masculino"), ("F", "Femenino")], help_text="Sexo (M/F)", max_length=1, verbose_name="sexo")),
                ("fecha_inicio_designacion", models.DateField(help_text="Inicio de la designación", verbose_name="fecha de inicio de designación")),
                ("numero_resolucion_designacion", models.CharField(blank=True, help_text="Número de resolución de designación", max_length=100, verbose_name="número de resolución de designación")),
                ("fecha_inicio_facultades", models.DateField(blank=True, help_text="Otorgamiento de facultades", null=True, verbose_name="fecha de inicio de facultades")),
                ("fecha_baja", models.DateField(help_text="Fecha en que se dio de baja al representante", verbose_name="fecha de baja")),
                ("motivo", models.CharField(blank=True, help_text="Motivo de la baja", max_length=255, verbose_name="motivo")),
                ("creado_en", models.DateTimeField(auto_now_add=True, verbose_name="creado en")),
                ("cargo_ejecutivo", models.ForeignKey(db_column="cargo_ejecutivo_id", help_text="Cargo ejecutivo", on_delete=django.db.models.deletion.PROTECT, related_name="+", to="convenios.executiveposition")),
                ("organo_directorio", models.ForeignKey(db_column="organo_directorio_id", help_text="Órgano del directorio representado", on_delete=django.db.models.deletion.PROTECT, related_name="+", to="convenios.organdirectory")),
                ("representante", models.ForeignKey(db_column="representante_id", help_text="Representante dado de baja", on_delete=django.db.models.deletion.PROTECT, related_name="historial", to="convenios.organrepresentative")),
                ("tipo_documento_identidad", models.ForeignKey(db_column="tipo_documento_identidad_id", help_text="Tipo de documento de identidad", on_delete=django.db.models.deletion.PROTECT, related_name="+", to="internados.identitydocumenttype")),
            ],
            options={
                "verbose_name": "historial de representante de órgano",
                "verbose_name_plural": "historiales de representante de órgano",
                "db_table": "historial_organo_representante",
                "ordering": ["-fecha_baja", "-id"],
            },
        ),
        # ----------------------------------------------------------------
        # 6 — Eliminar Representative y UniversityAuthority
        # ----------------------------------------------------------------
        migrations.DeleteModel(name="Representative"),
        migrations.DeleteModel(name="UniversityAuthority"),
        # ----------------------------------------------------------------
        # 7 — Document: quitar columnas, documento_anexo NOT NULL, renombrar tabla
        # ----------------------------------------------------------------
        migrations.RemoveField(model_name="document", name="nombre_archivo"),
        migrations.RemoveField(model_name="document", name="texto_extraido"),
        migrations.RemoveField(model_name="document", name="tipo_documento"),
        migrations.AlterField(
            model_name="document",
            name="documento_anexo",
            field=models.ForeignKey(
                db_column="documento_anexo_id",
                default=1,
                help_text="Anexo/tipo al que corresponde este documento (único discriminador de versionado)",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="documentos",
                to="internados.annexdocument",
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="document",
            options={"verbose_name": "documento adjunto"},
        ),
        migrations.AlterModelTable(
            name="document",
            table="documento_adjunto",
        ),
        # ----------------------------------------------------------------
        # 8 — Eliminar DocumentType
        # ----------------------------------------------------------------
        migrations.DeleteModel(name="DocumentType"),
        # ----------------------------------------------------------------
        # 9 — Reseed de cargos ejecutivos y anexos genéricos
        # ----------------------------------------------------------------
        migrations.RunPython(reseed, reseed_reverse),
    ]
