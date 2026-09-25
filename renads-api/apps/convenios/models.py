"""Modelos del Módulo 1: Gestionar Convenios.

Nombres de clases en inglés; tablas, columnas y descripciones en español.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


# ---------------------------------------------------------------------------
# Base de catálogos
# ---------------------------------------------------------------------------
class Catalog(models.Model):
    """Base abstracta para tablas paramétricas (RNF-MAN-01)."""

    codigo = models.CharField("código", max_length=50, unique=True, help_text="Código único")
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre")
    activo = models.BooleanField("activo", default=True, help_text="Indica si está activo")

    class Meta:
        abstract = True

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------------------
class Region(Catalog):
    class Meta:
        db_table = "region"
        verbose_name = "región"
        verbose_name_plural = "regiones"


class HealthGeographicScope(Catalog):
    gobierno_regional = models.ForeignKey(
        "RegionalGovernment",
        on_delete=models.PROTECT,
        db_column="gobierno_regional_id",
        null=True,
        blank=True,
        related_name="ambitos",
        help_text=(
            "Gobierno regional al que corresponde el ámbito sanitario "
            "(nulo para los 4 DIRIS de Lima Metropolitana)"
        ),
    )

    class Meta:
        db_table = "ambito_geografico_sanitario"
        verbose_name = "ámbito geográfico sanitario"


class Red(models.Model):
    """Red de salud que cuelga de un ámbito geográfico sanitario.

    No hereda de ``Catalog`` porque su ``codigo`` no es único global sino por
    ámbito (``unique_together``).
    """

    ambito_geografico_sanitario = models.ForeignKey(
        HealthGeographicScope, on_delete=models.PROTECT,
        db_column="ambito_geografico_sanitario_id", related_name="redes",
        help_text="Ámbito geográfico sanitario al que pertenece la red",
    )
    codigo = models.CharField("código", max_length=50, help_text="Código de la red (único dentro del ámbito)")
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la red")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "red"
        verbose_name = "red"
        verbose_name_plural = "redes"
        unique_together = (("ambito_geografico_sanitario", "codigo"),)
        ordering = ["ambito_geografico_sanitario", "codigo"]

    def __str__(self):
        return self.nombre


class Microred(models.Model):
    """Microred que cuelga de una red.

    No hereda de ``Catalog``: su ``codigo`` es único por red (``unique_together``).
    """

    red = models.ForeignKey(
        Red, on_delete=models.PROTECT, db_column="red_id", related_name="microredes",
        help_text="Red a la que pertenece la microred",
    )
    codigo = models.CharField("código", max_length=50, help_text="Código de la microred (único dentro de la red)")
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la microred")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "microred"
        verbose_name = "microred"
        verbose_name_plural = "microredes"
        unique_together = (("red", "codigo"),)
        ordering = ["red", "codigo"]

    def __str__(self):
        return self.nombre


class ConventionType(Catalog):
    anios_vigencia = models.PositiveSmallIntegerField(
        "años de vigencia", help_text="Vigencia en años (Marco=4, Específico=3)"
    )

    class Meta:
        db_table = "tipo_convenio"
        verbose_name = "tipo de convenio"


APLICA_A = [("TODOS", "Todos"), ("ESPECIFICO", "Específico")]


class ConventionStatus(Catalog):
    aplica_a = models.CharField(
        "aplica a", max_length=20, choices=APLICA_A, default="TODOS",
        help_text="Tipo de convenio al que aplica el estado",
    )
    orden = models.PositiveSmallIntegerField("orden", default=0, help_text="Orden en el flujo")

    class Meta:
        db_table = "estado_convenio"
        verbose_name = "estado de convenio"


class UniversityManagementType(Catalog):
    class Meta:
        db_table = "tipo_gestion_universidad"
        verbose_name = "tipo de gestión de universidad"


class AuthorizationType(Catalog):
    class Meta:
        db_table = "tipo_autorizacion"
        verbose_name = "tipo de autorización"


class AcademicLevel(Catalog):
    class Meta:
        db_table = "nivel_academico"
        verbose_name = "nivel académico"


class Specialty(Catalog):
    class Meta:
        db_table = "especialidad"
        verbose_name = "especialidad"


class SigningAuthorityType(Catalog):
    class Meta:
        db_table = "tipo_autoridad_firmante"
        verbose_name = "tipo de autoridad firmante"


# Categorías de la unidad orgánica (`unidad_organica.categoria`). Los labels
# replican los nombres canónicos de la tabla `organo` (fuente de la coherencia
# cargo↔categoría en `OrganRepresentativeSerializer`). RN-1: GOBIERNO_REGIONAL
# agrupa GERESA+DIRESA (pueden solicitar Marco); MINSA_DIRIS (DIRIS) está exenta.
ORGAN_DIRECTORY_CATEGORY = [
    ("ORGANO_MINSA", "Órgano del MINSA"),
    ("UNIVERSIDAD", "Universidad"),
    ("GOBIERNO_REGIONAL", "Gobierno Regional"),
    ("MINSA_DIRIS", "MINSA DIRIS"),
    ("UNIDAD_EJECUTORA", "Unidad Ejecutora"),
]


class Organ(models.Model):
    """Categoría de órgano institucional (tabla normalizada que reemplaza el CharField discriminador).

    Las cinco categorías canónicas son: Órgano del MINSA, Universidad,
    Gobierno Regional, MINSA DIRIS y Unidad Ejecutora.
    """

    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del órgano")
    estado = models.BooleanField("estado", default=True, help_text="Indica si está activo")

    class Meta:
        db_table = "organo"
        verbose_name = "órgano"
        verbose_name_plural = "órganos"

    def __str__(self):
        return self.nombre


class ExecutivePosition(models.Model):
    """Cargo ejecutivo perteneciente a una unidad orgánica concreta.

    Cada cargo referencia una ``unidad_organica`` (`unidad_organica`) — una unidad
    orgánica tiene varios cargos (1:N). No hereda de ``Catalog`` porque su
    ``nombre_masculino`` es único por ``unidad_organica``, no global.
    """

    organo = models.ForeignKey(
        "Organ", on_delete=models.PROTECT, db_column="organo_id",
        related_name="cargos_ejecutivos", null=False, verbose_name="órgano",
        help_text=(
            "Categoría de órgano (FK a la tabla canónica `organo`) a la que pertenece "
            "el cargo; debe coincidir con unidad_organica.organo cuando este está seteado"
        ),
    )
    unidad_organica = models.ForeignKey(
        "OrganicUnit", on_delete=models.PROTECT, db_column="unidad_organica_id",
        related_name="cargos", null=True, blank=True, verbose_name="unidad orgánica",
        help_text="Unidad orgánica a la que pertenece el cargo",
    )
    nombre_masculino = models.CharField(
        "nombre (masculino)", max_length=255,
        help_text="Nombre del cargo en masculino",
    )
    nombre_femenino = models.CharField(
        "nombre (femenino)", max_length=255, blank=True,
        help_text="Nombre del cargo en femenino",
    )
    activo = models.BooleanField("activo", default=True, help_text="Indica si está activo")

    class Meta:
        db_table = "cargo_ejecutivo"
        verbose_name = "cargo ejecutivo"
        unique_together = (("unidad_organica", "nombre_masculino"),)
        ordering = ["unidad_organica", "nombre_masculino"]

    def __str__(self):
        return self.nombre_masculino


class ObservationReason(Catalog):
    class Meta:
        db_table = "motivo_observacion"
        verbose_name = "motivo de observación"


class RejectionReason(Catalog):
    class Meta:
        db_table = "motivo_rechazo"
        verbose_name = "motivo de rechazo"


class ClosureReason(Catalog):
    class Meta:
        db_table = "motivo_cierre"
        verbose_name = "motivo de cierre"


class Category(Catalog):
    class Meta:
        db_table = "tipo_categoria"
        verbose_name = "categoría"
        verbose_name_plural = "categorías"


class ClassificationType(Catalog):
    class Meta:
        db_table = "tipo_clasificacion"
        verbose_name = "tipo de clasificación"
        verbose_name_plural = "tipos de clasificación"


# ---------------------------------------------------------------------------
# Ubigeo (INEI)
# ---------------------------------------------------------------------------
class Ubigeo(models.Model):
    """Ubicación geográfica del Perú a nivel distrito (código UBIGEO del INEI)."""

    codigo = models.CharField("código", max_length=6, primary_key=True, help_text="Código UBIGEO INEI (6 dígitos, clave primaria)")
    departamento = models.CharField("departamento", max_length=100, help_text="Departamento")
    provincia = models.CharField("provincia", max_length=100, help_text="Provincia")
    distrito = models.CharField("distrito", max_length=100, help_text="Distrito")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "ubigeo"
        verbose_name = "ubigeo"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.departamento} / {self.provincia} / {self.distrito}"


# ---------------------------------------------------------------------------
# Entidades — Gobiernos Regionales (GORE)
# ---------------------------------------------------------------------------
class RegionalGovernment(models.Model):
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del gobierno regional")
    region = models.ForeignKey(Region, on_delete=models.PROTECT, db_column="region_id", help_text="Región")
    numero_ruc = models.CharField(
        "número de RUC", max_length=11, blank=True,
        help_text="RUC (11 dígitos; texto para conservar ceros a la izquierda)",
    )
    direccion = models.CharField("dirección", max_length=500, blank=True, help_text="Dirección")
    correo = models.EmailField("correo", blank=True, help_text="Correo institucional")
    telefono = models.CharField("teléfono", max_length=30, blank=True, help_text="Teléfono institucional")
    sigla = models.CharField("sigla", max_length=50, blank=True, help_text="Sigla del gobierno regional")
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    referencia_logo = models.ImageField(
        "logo", upload_to="gobierno_regional/", max_length=500, null=True, blank=True,
        help_text="Logo institucional (imagen almacenada en el repositorio de medios)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "gobierno_regional"
        verbose_name = "gobierno regional"

    def __str__(self):
        return self.nombre


class OrganicUnit(models.Model):
    """Directorio unificado de unidades orgánicas/tipos institucionales.

    Cataloga órganos del MINSA, universidades, gobiernos regionales, DIRIS y unidades
    ejecutoras en una única tabla. La categoría se deriva del FK ``organo`` (→ ``Organ``).
    """

    # Mapeo Organ.nombre → código de categoría (mirror del definido en migración 0039).
    _NOMBRE_A_CATEGORIA: dict[str, str] = {
        "MINSA Administrativo": "ORGANO_MINSA",
        "Universidad": "UNIVERSIDAD",
        "Gobierno Regional": "GOBIERNO_REGIONAL",
        "Unidad Ejecutora": "UNIDAD_EJECUTORA",
        "MINSA DIRIS": "MINSA_DIRIS",
    }

    organo = models.ForeignKey(
        Organ, on_delete=models.PROTECT, db_column="organo_id",
        related_name="organos_directorio_por_categoria",
        help_text="Categoría del órgano (FK a la tabla canónica `organo`)",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del órgano")
    siglas = models.CharField("siglas", max_length=50, blank=True, help_text="Siglas")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "unidad_organica"
        verbose_name = "unidad orgánica"
        verbose_name_plural = "unidades orgánicas"
        constraints = [
            # RN-GORE-3: único por (organo, nombre). El GORE dejó de vivir en la
            # unidad orgánica (se trasladó a `convenio.gobierno_regional`), por
            # lo que la unicidad colapsa a un único constraint por (organo, nombre).
            models.UniqueConstraint(
                fields=["organo", "nombre"],
                name="uniq_unidad_organica_organo_nombre",
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def categoria(self) -> str | None:
        """Código de categoría derivado del FK ``organo`` (compat. con call sites legacy)."""
        return self._NOMBRE_A_CATEGORIA.get(self.organo.nombre)

    def get_categoria_display(self) -> str | None:
        """Label español de la categoría (para serializers con source=...get_categoria_display)."""
        code = self.categoria
        return dict(ORGAN_DIRECTORY_CATEGORY).get(code) if code else None


class ExecutingUnit(models.Model):
    codigo = models.CharField(
        max_length=4, primary_key=True,
        db_column="codigo",
        help_text="Código presupuestal de 4 dígitos (PK)",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la unidad ejecutora")
    ambito_geografico_sanitario = models.ForeignKey(
        HealthGeographicScope,
        on_delete=models.PROTECT,
        db_column="ambito_geografico_sanitario_id",
        related_name="unidades_ejecutoras",
        help_text="Ámbito geográfico sanitario al que pertenece",
    )
    activo = models.BooleanField("activo", default=True, help_text="Indica si está activa")

    class Meta:
        db_table = "unidad_ejecutora"
        verbose_name = "unidad ejecutora"

    def __str__(self):
        return self.nombre


class Ipress(models.Model):
    unidad_ejecutora = models.ForeignKey(
        ExecutingUnit, on_delete=models.PROTECT, db_column="unidad_ejecutora_id",
        to_field="codigo",
        related_name="ipress", help_text="Unidad ejecutora a la que pertenece",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del establecimiento")
    codigo_renipress = models.CharField(
        "código RENIPRESS", max_length=8, primary_key=True,
        help_text="Código RENIPRESS de 8 caracteres (clave primaria)",
    )
    direccion = models.CharField("dirección", max_length=500, blank=True, help_text="Dirección")
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    ambito_geografico_sanitario = models.ForeignKey(
        HealthGeographicScope, on_delete=models.PROTECT, db_column="ambito_geografico_sanitario_id",
        help_text="Ámbito geográfico sanitario",
    )
    categoria = models.ForeignKey(
        Category, on_delete=models.PROTECT, db_column="categoria_id", null=True, blank=True,
        related_name="ipress_por_categoria", help_text="Categoría del establecimiento",
    )
    tipo_clasificacion = models.ForeignKey(
        ClassificationType, on_delete=models.PROTECT, db_column="tipo_clasificacion_id", null=True, blank=True,
        related_name="ipress_por_clasificacion", help_text="Tipo de clasificación del establecimiento",
    )
    microred = models.ForeignKey(
        Microred, on_delete=models.PROTECT, db_column="microred_id", null=True, blank=True,
        related_name="ipress_por_microred", help_text="Microred a la que pertenece el establecimiento",
    )
    latitud = models.DecimalField(
        "latitud", max_digits=9, decimal_places=6, null=True, blank=True,
        help_text="Latitud (coordenada geográfica)",
    )
    longitud = models.DecimalField(
        "longitud", max_digits=9, decimal_places=6, null=True, blank=True,
        help_text="Longitud (coordenada geográfica)",
    )
    cantidad_camas = models.PositiveIntegerField(
        "cantidad de camas", null=True, blank=True, help_text="Número de camas del establecimiento",
    )
    numero_ruc = models.CharField(
        "número de RUC", max_length=11, blank=True,
        validators=[RegexValidator(r"^\d{11}$", message="El RUC debe tener exactamente 11 dígitos numéricos.")],
        help_text="RUC (11 dígitos; texto para conservar ceros a la izquierda)",
    )
    es_sede_docente = models.BooleanField(
        "es sede docente", default=False,
        help_text="Autorizada por CONAPRES como sede docente (asistencial, MINSA/FF.AA.-FF.PP., pública)",
    )
    referencia_logo = models.ImageField(
        "logo", upload_to="ipress/", max_length=500, null=True, blank=True,
        help_text="Logo institucional (imagen almacenada en el repositorio de medios)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "ipress"
        verbose_name = "IPRESS"
        verbose_name_plural = "IPRESS"

    def clean(self):
        """Valida la coherencia geográfica microred ↔ ámbito (denormalización deliberada).

        Si la IPRESS cuelga de una microred, el ámbito geográfico sanitario de esa
        microred (vía `microred.red.ambito_geografico_sanitario`) debe coincidir con
        el ámbito directo de la IPRESS. El ámbito directo es la fuente autoritativa;
        aquí solo se valida coherencia, nunca se sobrescribe. Si `microred` es nula,
        no se valida (muchas IPRESS RENIPRESS no cuelgan de microred).
        """
        super().clean()
        if self.microred_id and self.ambito_geografico_sanitario_id:
            ambito_microred_id = self.microred.red.ambito_geografico_sanitario_id
            if ambito_microred_id != self.ambito_geografico_sanitario_id:
                raise ValidationError({
                    "microred": "La microred seleccionada pertenece a un ámbito "
                                "geográfico sanitario distinto al de la IPRESS.",
                })

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Entidades — CONAPRES
# ---------------------------------------------------------------------------
class Conapres(models.Model):
    nombre = models.CharField("nombre", max_length=255, help_text="Denominación")
    descripcion = models.TextField("descripción", blank=True, help_text="Descripción")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "conapres"
        verbose_name = "CONAPRES"

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Representantes de órgano (directorio) y su histórico de bajas
# ---------------------------------------------------------------------------
SEX = [("M", "Masculino"), ("F", "Femenino")]


class OrganRepresentative(models.Model):
    """Representante/autoridad de una entidad del proceso docencia-servicio.

    Relación **polimórfica** (`entidad`): un representante pertenece a cualquiera de las
    entidades participantes — unidades orgánicas (MINSA/GORE/DIRIS), universidades,
    unidades ejecutoras, CONAPRES o IPRESS —, referenciada por `tipo_contenido` +
    `id_objeto`. Antes tenía una FK directa a `OrganicUnit` (migrada a los campos
    genéricos en la migración 0038).
    """

    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, db_column="tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad representada (ContentType)",
    )
    id_objeto = models.PositiveIntegerField(
        "id del objeto", db_column="id_objeto", help_text="Id de la entidad representada",
    )
    entidad = GenericForeignKey("tipo_contenido", "id_objeto")
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del representante")
    tipo_documento_identidad = models.ForeignKey(
        "internados.IdentityDocumentType", on_delete=models.PROTECT,
        db_column="tipo_documento_identidad_id", related_name="+",
        help_text="Tipo de documento de identidad",
    )
    numero_documento_identidad = models.CharField(
        "número de documento de identidad", max_length=20,
        help_text="Número de documento de identidad",
    )
    sexo = models.CharField("sexo", max_length=1, choices=SEX, help_text="Sexo (M/F)")
    cargo_ejecutivo = models.ForeignKey(
        ExecutivePosition, on_delete=models.PROTECT, db_column="cargo_ejecutivo_id",
        related_name="+", help_text="Cargo ejecutivo",
    )
    fecha_inicio_designacion = models.DateField(
        "fecha de inicio de designación", help_text="Inicio de la designación",
    )
    numero_resolucion_designacion = models.CharField(
        "número de resolución de designación", max_length=100, blank=True,
        help_text="Número de resolución de designación",
    )
    numero_resolucion_facultades = models.CharField(
        "número de resolución de facultades", max_length=100, blank=True,
        help_text="Número de resolución que otorga facultades al representante",
    )
    fecha_inicio_facultades = models.DateField(
        "fecha de inicio de facultades", null=True, blank=True,
        help_text="Otorgamiento de facultades",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "organo_representante"
        verbose_name = "representante de entidad"
        verbose_name_plural = "representantes de entidad"
        ordering = ["id"]
        indexes = [
            models.Index(
                fields=["tipo_contenido", "id_objeto"],
                name="idx_org_repr_entidad",
            ),
        ]

    def __str__(self):
        return self.nombre


class OrganRepresentativeHistory(models.Model):
    """Snapshot histórico de un representante dado de baja (denormalizado, preserva el estado)."""

    representante = models.ForeignKey(
        OrganRepresentative, on_delete=models.PROTECT, db_column="representante_id",
        related_name="historial", help_text="Representante dado de baja",
    )
    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, db_column="tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad representada (ContentType)",
    )
    id_objeto = models.PositiveIntegerField(
        "id del objeto", db_column="id_objeto", help_text="Id de la entidad representada",
    )
    entidad = GenericForeignKey("tipo_contenido", "id_objeto")
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del representante")
    tipo_documento_identidad = models.ForeignKey(
        "internados.IdentityDocumentType", on_delete=models.PROTECT,
        db_column="tipo_documento_identidad_id", related_name="+",
        help_text="Tipo de documento de identidad",
    )
    numero_documento_identidad = models.CharField(
        "número de documento de identidad", max_length=20,
        help_text="Número de documento de identidad",
    )
    sexo = models.CharField("sexo", max_length=1, choices=SEX, help_text="Sexo (M/F)")
    cargo_ejecutivo = models.ForeignKey(
        ExecutivePosition, on_delete=models.PROTECT, db_column="cargo_ejecutivo_id",
        related_name="+", help_text="Cargo ejecutivo",
    )
    fecha_inicio_designacion = models.DateField(
        "fecha de inicio de designación", help_text="Inicio de la designación",
    )
    numero_resolucion_designacion = models.CharField(
        "número de resolución de designación", max_length=100, blank=True,
        help_text="Número de resolución de designación",
    )
    numero_resolucion_facultades = models.CharField(
        "número de resolución de facultades", max_length=100, blank=True,
        help_text="Número de resolución que otorga facultades al representante",
    )
    fecha_inicio_facultades = models.DateField(
        "fecha de inicio de facultades", null=True, blank=True,
        help_text="Otorgamiento de facultades",
    )
    fecha_baja = models.DateField(
        "fecha de baja", help_text="Fecha en que se dio de baja al representante",
    )
    motivo = models.CharField("motivo", max_length=255, blank=True, help_text="Motivo de la baja")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "historial_organo_representante"
        verbose_name = "historial de representante de órgano"
        verbose_name_plural = "historiales de representante de órgano"
        ordering = ["-fecha_baja", "-id"]

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Entidades — Universidades
# ---------------------------------------------------------------------------
class UniversityEntityType(models.Model):
    """Tipo de entidad universitaria (catálogo fijo: Universidad, Instituto, etc.)."""

    nombre = models.CharField(
        "nombre", max_length=100, unique=True,
        help_text="Nombre del tipo de entidad universitaria",
    )
    activo = models.BooleanField(
        "activo", default=True,
        help_text="Indica si el tipo está activo",
    )

    class Meta:
        db_table = "tipo_entidad_universidad"
        verbose_name = "tipo de entidad universitaria"
        verbose_name_plural = "tipos de entidad universitaria"
        ordering = ["id"]

    def __str__(self):
        return self.nombre


class University(models.Model):
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la universidad")
    siglas = models.CharField("siglas", max_length=50, blank=True, help_text="Siglas")
    numero_ruc = models.CharField("número de RUC", max_length=11, blank=True, help_text="Número de RUC")
    tipo_gestion = models.ForeignKey(
        UniversityManagementType, on_delete=models.PROTECT, db_column="tipo_gestion_id",
        help_text="Pública / privada",
    )
    tipo_entidad = models.ForeignKey(
        UniversityEntityType,
        on_delete=models.PROTECT,
        db_column="tipo_entidad_id",
        help_text="Tipo de entidad universitaria",
    )
    tipo_autorizacion = models.ForeignKey(
        AuthorizationType, on_delete=models.PROTECT, db_column="tipo_autorizacion_id",
        help_text="Licenciada / Denegada / Pendiente",
    )
    codigo_inei = models.CharField("código INEI", max_length=20, blank=True, help_text="Código INEI")
    fecha_constitucion = models.DateField("fecha de constitución", null=True, blank=True, help_text="Fecha de constitución")
    fecha_autorizacion = models.DateField("fecha de autorización", null=True, blank=True, help_text="Fecha de autorización")
    numero_resolucion = models.CharField("número de resolución", max_length=100, blank=True, help_text="Número de resolución")
    direccion_legal = models.CharField("dirección legal", max_length=500, blank=True, help_text="Dirección legal")
    telefono = models.CharField("teléfono", max_length=30, blank=True, help_text="Teléfono")
    correo_institucional = models.CharField("correo institucional", max_length=255, blank=True, help_text="Correo institucional")
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    referencia_logo = models.ImageField(
        "logo", upload_to="universidad/", max_length=500, null=True, blank=True,
        help_text="Logo institucional (imagen almacenada en el repositorio de medios)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "universidad"
        verbose_name = "universidad"

    def __str__(self):
        return self.nombre


class Faculty(models.Model):
    universidad = models.ForeignKey(
        University, on_delete=models.CASCADE, db_column="universidad_id",
        related_name="facultades", help_text="Universidad",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la facultad")
    direccion = models.CharField(
        "dirección", max_length=255, blank=True, help_text="Dirección de la facultad",
    )
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    referencia_logo = models.ImageField(
        "logo", upload_to="facultad/", max_length=500, null=True, blank=True,
        help_text="Logo institucional (imagen almacenada en el repositorio de medios)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "facultad"
        verbose_name = "facultad"

    def __str__(self):
        return self.nombre


class ProfessionalCareer(models.Model):
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la carrera o programa")
    nivel_academico = models.ForeignKey(
        AcademicLevel, on_delete=models.PROTECT, db_column="nivel_academico_id",
        help_text="Carrera profesional / segunda especialidad / maestría / doctorado",
    )
    orden = models.IntegerField(
        "orden",
        default=0,
        help_text="Orden de visualización en el listado (menor primero)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "carrera_profesional"
        verbose_name = "carrera profesional"

    def __str__(self):
        return self.nombre


class UniversityCareer(models.Model):
    """Tabla puente universidad ↔ carrera profesional (carreras que dicta cada universidad), asociada a la facultad que la imparte."""

    universidad = models.ForeignKey(
        University, on_delete=models.PROTECT, db_column="universidad_id",
        related_name="carreras", help_text="Universidad",
    )
    carrera_profesional = models.ForeignKey(
        ProfessionalCareer, on_delete=models.PROTECT, db_column="carrera_profesional_id",
        related_name="universidades", help_text="Carrera profesional",
    )
    facultad = models.ForeignKey(
        Faculty, on_delete=models.PROTECT, db_column="facultad_id",
        related_name="carreras_facultad",
        help_text="Facultad de la universidad a la que pertenece la carrera",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "universidad_carrera"
        verbose_name = "carrera de universidad"
        verbose_name_plural = "carreras de universidad"
        unique_together = (("universidad", "carrera_profesional"),)

    def __str__(self):
        return f"{self.universidad_id} — {self.carrera_profesional_id}"


class UniversityCampus(models.Model):
    universidad = models.ForeignKey(
        University, on_delete=models.CASCADE, db_column="universidad_id",
        related_name="locales", help_text="Universidad",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del local")
    direccion = models.CharField("dirección", max_length=500, blank=True, help_text="Dirección")
    region = models.ForeignKey(
        Region, on_delete=models.SET_NULL, db_column="region_id", null=True, blank=True,
        related_name="+", help_text="Región",
    )
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "local_universidad"
        verbose_name = "local de universidad"

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Seguridad y perfil institucional
# ---------------------------------------------------------------------------
class UserEntityProfile(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column="usuario_id",
        related_name="perfiles_entidad", help_text="Usuario",
    )
    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, db_column="tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad asociada",
    )
    id_objeto = models.CharField("id objeto", max_length=64, help_text="Identificador de la entidad asociada")
    entidad = GenericForeignKey("tipo_contenido", "id_objeto")
    grupo = models.ForeignKey(
        "auth.Group", on_delete=models.PROTECT, db_column="grupo_id",
        related_name="+", help_text="Rol institucional",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "perfil_usuario_entidad"
        verbose_name = "perfil de usuario por entidad"
        unique_together = [("usuario", "tipo_contenido", "id_objeto", "grupo")]


# ---------------------------------------------------------------------------
# Núcleo de convenios
# ---------------------------------------------------------------------------
class ConventionTemplate(models.Model):
    tipo_convenio = models.ForeignKey(
        ConventionType, on_delete=models.PROTECT, db_column="tipo_convenio_id",
        help_text="Tipo al que aplica",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la plantilla")
    referencia_externa = models.CharField(
        "referencia externa", max_length=500, help_text="Referencia externa del archivo de plantilla",
    )
    version = models.PositiveIntegerField("versión", default=1, help_text="Versión")
    activo = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "plantilla_convenio"
        verbose_name = "plantilla de convenio"

    def __str__(self):
        return self.nombre


class Convention(models.Model):
    tipo_convenio = models.ForeignKey(
        ConventionType, on_delete=models.PROTECT, db_column="tipo_convenio_id",
        help_text="Marco / Específico",
    )
    convenio_marco = models.ForeignKey(
        "self", on_delete=models.PROTECT, db_column="convenio_marco_id", null=True, blank=True,
        related_name="convenios_especificos",
        help_text="Convenio Marco vigente del que depende el Específico (RN-3)",
    )
    convenio_origen = models.ForeignKey(
        "self", on_delete=models.PROTECT, db_column="convenio_origen_id", null=True, blank=True,
        related_name="adendas",
        help_text="Convenio (Marco o Específico) que esta adenda amplía",
    )
    es_adenda = models.BooleanField(
        "es adenda", default=False,
        help_text="Marca la fila como adenda de ampliación (derivable de convenio_origen; explícito para filtros)",
    )
    plantilla = models.ForeignKey(
        ConventionTemplate, on_delete=models.SET_NULL, db_column="plantilla_id", null=True, blank=True,
        help_text="Plantilla utilizada",
    )
    nomenclatura = models.CharField(
        "nomenclatura", max_length=50, blank=True,
        help_text="Nomenclatura oficial del Convenio Marco (se asigna al aprobar DIGEP)",
    )
    titulo = models.CharField("título", max_length=255, help_text="Título / denominación")
    solicitante_tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, db_column="solicitante_tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad solicitante",
    )
    solicitante_id_objeto = models.PositiveBigIntegerField(
        "id objeto solicitante", help_text="Identificador de la entidad solicitante"
    )
    solicitante = GenericForeignKey("solicitante_tipo_contenido", "solicitante_id_objeto")
    unidad_organica = models.ForeignKey(
        OrganicUnit, on_delete=models.PROTECT, db_column="unidad_organica_id",
        related_name="convenios",
        help_text="Unidad orgánica (GERESA/DIRESA/DIRIS) parte del convenio.",
    )
    gobierno_regional = models.ForeignKey(
        RegionalGovernment, on_delete=models.PROTECT, db_column="gobierno_regional_id",
        null=True, blank=True, related_name="convenios",
        help_text="Gobierno Regional del convenio (solo Convenio Marco regional).",
    )
    universidad = models.ForeignKey(
        University, on_delete=models.PROTECT, db_column="universidad_id",
        related_name="convenios",
        help_text="Universidad parte del convenio. Su tipo de entidad se deriva de esta relación.",
    )
    unidad_ejecutora = models.ForeignKey(
        ExecutingUnit, on_delete=models.PROTECT, db_column="unidad_ejecutora_id", null=True, blank=True,
        to_field="codigo",
        related_name="convenios",
        help_text="Unidad ejecutora parte del Convenio Específico",
    )
    facultad = models.ForeignKey(
        Faculty, on_delete=models.PROTECT, db_column="facultad_id", null=True, blank=True,
        related_name="convenios",
        help_text="Facultad (de la universidad del Marco) parte del Convenio Específico",
    )
    estado_actual = models.ForeignKey(
        ConventionStatus, on_delete=models.PROTECT, db_column="estado_actual_id",
        help_text="Estado actual",
    )
    fecha_solicitud = models.DateField("fecha de solicitud", help_text="Fecha de solicitud")
    fecha_inicio = models.DateField("fecha de inicio", null=True, blank=True, help_text="Inicio de vigencia")
    fecha_fin = models.DateField("fecha de fin", null=True, blank=True, help_text="Fin de vigencia")
    max_campos_clinicos = models.PositiveIntegerField(
        "máximo de campos clínicos", null=True, blank=True,
        help_text="Cantidad máxima de campos clínicos (solo Específico)",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="creado_por",
        related_name="+", help_text="Usuario que registró",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        db_table = "convenio"
        verbose_name = "convenio"

    def __str__(self):
        return self.titulo


class ConventionParticipant(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="participantes", help_text="Convenio",
    )
    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, db_column="tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad participante",
    )
    id_objeto = models.PositiveBigIntegerField("id objeto", help_text="Identificador de la entidad participante")
    entidad = GenericForeignKey("tipo_contenido", "id_objeto")
    tipo_autoridad_firmante = models.ForeignKey(
        SigningAuthorityType, on_delete=models.SET_NULL, db_column="tipo_autoridad_firmante_id",
        null=True, blank=True, help_text="Tipo de autoridad firmante",
    )
    es_firmante = models.BooleanField("es firmante", default=False, help_text="Indica si firma el convenio")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "participante_convenio"
        verbose_name = "participante de convenio"
        unique_together = [("convenio", "tipo_contenido", "id_objeto")]


# Roles institucionales de una parte firmante del convenio (código en inglés).
PARTY_ROLE = [
    ("MINSA", "MINSA"),
    ("UNIVERSIDAD", "Universidad"),
    ("GOBIERNO_REGIONAL", "Gobierno regional"),
    ("UNIDAD_EJECUTORA", "Unidad ejecutora"),
    ("FACULTAD", "Facultad"),
]


class ConventionParty(models.Model):
    """Parte firmante estructurada de un convenio (rol + órgano + representante + cargo).

    Reemplaza el uso polimórfico para las partes firmantes con una relación explícita
    por rol institucional. La coherencia órgano↔representante↔cargo se valida en el
    service ``sincronizar_partes`` (no en ``clean()``): este modelo no lleva lógica de
    negocio.
    """

    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="partes_firmantes", help_text="Convenio al que pertenece la parte",
    )
    rol = models.CharField(
        "rol de la parte", max_length=20, choices=PARTY_ROLE, db_column="rol",
        help_text="Rol institucional de la parte firmante",
    )
    unidad_organica = models.ForeignKey(
        OrganicUnit, on_delete=models.PROTECT, db_column="unidad_organica_id",
        related_name="+", help_text="Unidad orgánica que representa la parte",
    )
    organo_representante = models.ForeignKey(
        OrganRepresentative, on_delete=models.PROTECT, db_column="organo_representante_id",
        null=True, blank=True, related_name="+",
        help_text="Representante que firma por la parte",
    )
    cargo_ejecutivo = models.ForeignKey(
        ExecutivePosition, on_delete=models.PROTECT, db_column="cargo_ejecutivo_id",
        null=True, blank=True, related_name="+",
        help_text="Cargo ejecutivo del representante",
    )
    orden = models.PositiveSmallIntegerField(
        "orden de firma", default=1, db_column="orden",
        help_text="Orden de firma dentro del rol (apoderado = 2)",
    )
    es_firmante = models.BooleanField(
        "es firmante", default=True, db_column="es_firmante",
        help_text="Indica si la parte firma el convenio",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True, db_column="creado_en")

    class Meta:
        db_table = "parte_convenio"
        verbose_name = "parte de convenio"
        verbose_name_plural = "partes de convenio"
        unique_together = (("convenio", "rol", "orden"),)
        ordering = ["convenio", "orden"]

    def __str__(self):
        return f"{self.convenio_id} — {self.rol} ({self.orden})"


class ConventionStatusHistory(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="historial_estados", help_text="Convenio",
    )
    estado = models.ForeignKey(
        ConventionStatus, on_delete=models.PROTECT, db_column="estado_id", help_text="Estado registrado",
    )
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="cambiado_por",
        related_name="+", help_text="Responsable del cambio",
    )
    cambiado_en = models.DateTimeField("cambiado en", auto_now_add=True, help_text="Fecha y hora")
    observacion = models.TextField("observación", blank=True, help_text="Observaciones")

    class Meta:
        db_table = "historial_estado_convenio"
        verbose_name = "historial de estado de convenio"


# ---------------------------------------------------------------------------
# Flujo del convenio
# ---------------------------------------------------------------------------
EVALUATION_RESULT = [("VALIDADO", "Validado"), ("OBSERVADO", "Observado"), ("RECHAZADO", "Rechazado")]
OPINION_RESULT = [("FAVORABLE", "Favorable"), ("OBSERVADO", "Observado")]
SIGNATURE_STATUS = [("PENDIENTE", "Pendiente"), ("FIRMADO", "Firmado"), ("DEVUELTO", "Devuelto")]


class TechnicalEvaluation(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="evaluaciones_tecnicas", help_text="Convenio",
    )
    resultado = models.CharField("resultado", max_length=20, choices=EVALUATION_RESULT, help_text="Resultado de la evaluación")
    observaciones = models.TextField("observaciones", blank=True, help_text="Observaciones")
    subsanacion = models.TextField("subsanación", blank=True, help_text="Subsanación")
    evaluado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="evaluado_por",
        related_name="+", help_text="Responsable",
    )
    unidad_organica = models.ForeignKey(
        OrganicUnit, on_delete=models.SET_NULL, db_column="unidad_organica_id",
        null=True, blank=True, related_name="+",
        help_text="Unidad evaluadora (DIGEP) — unidad orgánica",
    )
    fecha_evaluacion = models.DateField("fecha de evaluación", help_text="Fecha de evaluación")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "evaluacion_tecnica"
        verbose_name = "evaluación técnica"


class ConapresOpinion(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="opiniones_conapres", help_text="Convenio (solo Específico)",
    )
    fecha_solicitud = models.DateField("fecha de solicitud", help_text="Fecha de solicitud de opinión")
    estado_atencion = models.CharField("estado de atención", max_length=20, help_text="Estado de atención")
    resultado_opinion = models.CharField(
        "resultado de la opinión", max_length=20, choices=OPINION_RESULT, blank=True, help_text="Resultado",
    )
    fecha_respuesta = models.DateField("fecha de respuesta", null=True, blank=True, help_text="Fecha de respuesta")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "opinion_conapres"
        verbose_name = "opinión CONAPRES"


class ClinicalFieldRegistration(models.Model):
    """Registro (CONAPRES) del total de campos clínicos por sede docente + carrera.

    Tabla `campo_clinico_ipress`. CONAPRES registra el total de campos clínicos
    disponibles por IPRESS (sede docente) y carrera profesional. Las asignaciones
    por universidad se llevan en `ClinicalFieldAllocation`.
    """

    ipress = models.ForeignKey(
        Ipress, on_delete=models.PROTECT, db_column="ipress_id", help_text="Sede docente (establecimiento)",
    )
    carrera_profesional = models.ForeignKey(
        ProfessionalCareer, on_delete=models.PROTECT, db_column="carrera_profesional_id",
        help_text="Carrera / programa académico",
    )
    especialidad = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, db_column="especialidad_id", null=True, blank=True,
        related_name="+", help_text="Especialidad",
    )
    campos_clinicos_registrados = models.PositiveIntegerField(
        "campos clínicos registrados",
        help_text="Total de campos clínicos registrados por CONAPRES para la sede y carrera",
    )
    campos_clinicos_asignados = models.PositiveIntegerField(
        "campos clínicos asignados",
        default=0,
        help_text=(
            "Acumulador Σ de los campos autorizados en las asignaciones por universidad; "
            "recalculado por el service (solo lectura en la API)"
        ),
    )
    numero_resolucion_conapres = models.CharField(
        "número de resolución CONAPRES", max_length=100, blank=True,
        help_text="Número de la resolución CONAPRES que autoriza los campos clínicos de la sede",
    )
    fecha_resolucion_conapres = models.DateField(
        "fecha de resolución CONAPRES", null=True, blank=True,
        help_text="Fecha de la resolución CONAPRES",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, db_column="creado_por",
        null=True, blank=True, related_name="+", help_text="Usuario que creó el registro",
    )
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, db_column="actualizado_por",
        null=True, blank=True, related_name="+", help_text="Usuario que actualizó el registro",
    )

    class Meta:
        db_table = "campo_clinico_ipress"
        verbose_name = "registro de campos clínicos por sede"
        verbose_name_plural = "registros de campos clínicos por sede"
        unique_together = (("ipress", "carrera_profesional", "especialidad"),)


class ClinicalFieldAllocation(models.Model):
    """Asignación (Órgano Regional) de campos clínicos por universidad.

    Tabla `campo_clinico_ipress_universidad`. El Órgano Regional (grupo
    `Gobierno Regional`) asigna cupos por universidad contra un registro
    (`ClinicalFieldRegistration`), sujeto a la disponibilidad del registro padre.
    """

    campo_clinico_ipress = models.ForeignKey(
        ClinicalFieldRegistration, on_delete=models.PROTECT, db_column="campo_clinico_ipress_id",
        related_name="asignaciones", help_text="Registro de campos clínicos (sede + carrera)",
    )
    convenio = models.ForeignKey(
        Convention, on_delete=models.PROTECT, db_column="convenio_id",
        related_name="+", help_text="Convenio Específico vigente que respalda la asignación",
    )
    ipress = models.ForeignKey(
        Ipress, on_delete=models.PROTECT, db_column="ipress_id", help_text="Sede docente (establecimiento)",
    )
    carrera_profesional = models.ForeignKey(
        ProfessionalCareer, on_delete=models.PROTECT, db_column="carrera_profesional_id",
        help_text="Carrera / programa académico",
    )
    especialidad = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, db_column="especialidad_id", null=True, blank=True,
        related_name="+", help_text="Especialidad",
    )
    universidad = models.ForeignKey(
        University, on_delete=models.PROTECT, db_column="universidad_id",
        related_name="campos_clinicos_asignados", help_text="Universidad a la que se asignan los cupos",
    )
    fecha_inicio = models.DateField("fecha de inicio", help_text="Inicio de vigencia de la asignación")
    fecha_fin = models.DateField("fecha de fin", help_text="Fin de vigencia de la asignación")
    campos_clinicos_autorizados = models.PositiveIntegerField(
        "campos clínicos autorizados",
        help_text="Cupos autorizados para la universidad",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, db_column="creado_por",
        null=True, blank=True, related_name="+", help_text="Usuario que creó la asignación",
    )
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, db_column="actualizado_por",
        null=True, blank=True, related_name="+", help_text="Usuario que actualizó la asignación",
    )

    class Meta:
        db_table = "campo_clinico_ipress_universidad"
        verbose_name = "asignación de campos clínicos por universidad"
        verbose_name_plural = "asignaciones de campos clínicos por universidad"
        unique_together = (("campo_clinico_ipress", "universidad", "convenio"),)


class LegalOpinion(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="opiniones_juridicas", help_text="Convenio",
    )
    fecha_envio = models.DateField("fecha de envío", help_text="Fecha de envío a OGAJ")
    resultado_opinion = models.CharField(
        "resultado de la opinión", max_length=20, choices=OPINION_RESULT, blank=True, help_text="Resultado",
    )
    observaciones_legales = models.TextField("observaciones legales", blank=True, help_text="Observaciones legales")
    subsanacion = models.TextField("subsanación", blank=True, help_text="Subsanación")
    fecha_respuesta = models.DateField("fecha de respuesta", null=True, blank=True, help_text="Fecha de respuesta")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "opinion_juridica"
        verbose_name = "opinión jurídica"


class Signature(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="firmas", help_text="Convenio",
    )
    firmante_tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, db_column="firmante_tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad firmante",
    )
    firmante_id_objeto = models.PositiveBigIntegerField(
        "id objeto firmante", help_text="Identificador de la entidad firmante"
    )
    firmante = GenericForeignKey("firmante_tipo_contenido", "firmante_id_objeto")
    tipo_autoridad_firmante = models.ForeignKey(
        SigningAuthorityType, on_delete=models.SET_NULL, db_column="tipo_autoridad_firmante_id",
        null=True, blank=True, help_text="Tipo de autoridad firmante",
    )
    orden_firma = models.PositiveSmallIntegerField("orden de firma", null=True, blank=True, help_text="Orden en el circuito")
    fecha_envio = models.DateField("fecha de envío", null=True, blank=True, help_text="Fecha de envío")
    fecha_recepcion = models.DateField("fecha de recepción", null=True, blank=True, help_text="Fecha de recepción")
    estado_firma = models.CharField("estado de firma", max_length=20, choices=SIGNATURE_STATUS, help_text="Estado de firma")
    observaciones = models.TextField("observaciones", blank=True, help_text="Observaciones o devoluciones")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "firma"
        verbose_name = "firma"


class Publication(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="publicaciones", help_text="Convenio",
    )
    fecha_publicacion = models.DateField("fecha de publicación", help_text="Fecha de publicación")
    referencia_publicacion = models.CharField(
        "referencia de publicación", max_length=255, blank=True, help_text="Enlace, código o constancia",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="creado_por", related_name="+",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "publicacion"
        verbose_name = "publicación"


# ---------------------------------------------------------------------------
# Documento (adjuntos en repositorio externo) y auditoría
# ---------------------------------------------------------------------------
DOCUMENT_STATUS = [
    ("ACTIVO", "Activo"), ("REEMPLAZADO", "Reemplazado"), ("ANULADO", "Anulado"),
    ("OBSERVADO", "Observado"), ("VALIDADO", "Validado"),
]


class Document(models.Model):
    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, db_column="tipo_contenido_id",
        related_name="+", help_text="Tabla destino",
    )
    id_objeto = models.PositiveBigIntegerField("id objeto", help_text="Registro destino")
    objeto = GenericForeignKey("tipo_contenido", "id_objeto")
    referencia_externa = models.CharField(
        "referencia externa", max_length=500, help_text="Clave/URL del archivo en el repositorio externo",
    )
    version = models.PositiveIntegerField("versión", default=1, help_text="Versión")
    estado = models.CharField("estado", max_length=20, choices=DOCUMENT_STATUS, default="ACTIVO", help_text="Estado")
    version_anterior = models.ForeignKey(
        "self", on_delete=models.SET_NULL, db_column="version_anterior_id", null=True, blank=True,
        related_name="versiones_siguientes", help_text="Versión previa reemplazada",
    )
    documento_anexo = models.ForeignKey(
        "internados.AnnexDocument", on_delete=models.PROTECT,
        db_column="documento_anexo_id", related_name="documentos",
        help_text="Anexo/tipo al que corresponde este documento (único discriminador de versionado)",
    )
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="cargado_por", related_name="+",
        help_text="Usuario que cargó",
    )
    cargado_en = models.DateTimeField("cargado en", auto_now_add=True, help_text="Fecha y hora de carga")

    class Meta:
        db_table = "documento_adjunto"
        verbose_name = "documento adjunto"


class AuditLog(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, db_column="usuario_id", null=True, blank=True,
        related_name="+", help_text="Usuario que ejecutó la acción",
    )
    accion = models.CharField("acción", max_length=30, help_text="CREAR / ACTUALIZAR / ELIMINAR / CAMBIO_ESTADO / …")
    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, db_column="tipo_contenido_id",
        related_name="+", help_text="Entidad afectada",
    )
    id_objeto = models.CharField("id objeto", max_length=64, help_text="Registro afectado")
    objeto = GenericForeignKey("tipo_contenido", "id_objeto")
    nombre_campo = models.CharField("nombre del campo", max_length=100, blank=True, help_text="Campo modificado")
    valor_anterior = models.TextField("valor anterior", blank=True, help_text="Valor anterior")
    valor_nuevo = models.TextField("valor nuevo", blank=True, help_text="Valor nuevo")
    direccion_ip = models.CharField("dirección IP", max_length=45, blank=True, help_text="IP de origen")
    creado_en = models.DateTimeField("creado en", auto_now_add=True, help_text="Fecha y hora")

    class Meta:
        db_table = "bitacora_auditoria"
        verbose_name = "bitácora de auditoría"
