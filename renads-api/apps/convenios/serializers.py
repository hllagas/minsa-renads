"""Serializers del módulo Convenios (bloque núcleo + entradas de flujo)."""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.convenios.models import (
    AuditLog,
    ClinicalFieldAllocation,
    ClinicalFieldRegistration,
    ConapresOpinion,
    Convention,
    ConventionParticipant,
    ConventionParty,
    ConventionStatusHistory,
    ConventionTemplate,
    Document,
    Faculty,
    LegalOpinion,
    OrganRepresentative,
    ProfessionalCareer,
    Publication,
    Signature,
    TechnicalEvaluation,
    UniversityCareer,
)


# ---------------------------------------------------------------------------
# Convenio
# ---------------------------------------------------------------------------
class ConventionReadSerializer(serializers.ModelSerializer):
    tipo_convenio = serializers.CharField(source="tipo_convenio.nombre", read_only=True)
    estado_actual = serializers.CharField(source="estado_actual.nombre", read_only=True)
    estado_codigo = serializers.CharField(source="estado_actual.codigo", read_only=True)
    solicitante = serializers.SerializerMethodField()
    # Universidad y órgano del directorio: id + nombre legible; el "tipo" se deriva de la
    # entidad (no se almacena en `convenio`), evitando redundancia en el esquema.
    organo_directorio_nombre = serializers.CharField(source="organo_directorio.nombre", read_only=True)
    # Categoría del órgano del directorio (discriminador), label español; ya no es un sub-tipo.
    tipo_organo_directorio = serializers.CharField(
        source="organo_directorio.get_categoria_display", read_only=True, allow_null=True,
    )
    universidad_nombre = serializers.CharField(source="universidad.nombre", read_only=True)
    tipo_entidad_universidad = serializers.CharField(
        source="universidad.tipo_entidad.nombre", read_only=True
    )
    unidad_ejecutora_detalle = serializers.SerializerMethodField()
    facultad_detalle = serializers.SerializerMethodField()
    gobierno_regional_detalle = serializers.SerializerMethodField()
    adendas = serializers.SerializerMethodField()
    vigencia_efectiva = serializers.SerializerMethodField()
    partes_firmantes = serializers.SerializerMethodField()

    class Meta:
        model = Convention
        fields = [
            "id", "tipo_convenio", "convenio_marco", "convenio_origen", "es_adenda",
            "plantilla", "nomenclatura", "titulo",
            "solicitante_tipo_contenido", "solicitante_id_objeto", "solicitante",
            "organo_directorio", "organo_directorio_nombre", "tipo_organo_directorio",
            "universidad", "universidad_nombre", "tipo_entidad_universidad",
            "unidad_ejecutora", "unidad_ejecutora_detalle", "facultad", "facultad_detalle",
            "gobierno_regional", "gobierno_regional_detalle",
            "estado_actual", "estado_codigo", "fecha_solicitud", "fecha_inicio", "fecha_fin",
            "vigencia_efectiva", "adendas", "partes_firmantes",
            "max_campos_clinicos", "creado_por", "creado_en", "actualizado_en",
        ]

    def get_solicitante(self, obj) -> str:
        return str(obj.solicitante) if obj.solicitante else ""

    def get_unidad_ejecutora_detalle(self, obj):
        return _detalle_fk(obj.unidad_ejecutora, "nombre", "codigo")

    def get_facultad_detalle(self, obj):
        return _detalle_fk(obj.facultad, "nombre")

    def get_gobierno_regional_detalle(self, obj):
        return _detalle_fk(obj.gobierno_regional, "nombre", "sigla")

    def get_adendas(self, obj) -> list:
        # Un nivel de adendas directas; el frontend recorre recursivamente si
        # necesita niveles profundos de la cadena.
        return [
            {
                "id": a.id,
                "titulo": a.titulo,
                "estado_codigo": a.estado_actual.codigo if a.estado_actual_id else None,
                "fecha_inicio": a.fecha_inicio,
                "fecha_fin": a.fecha_fin,
            }
            for a in obj.adendas.all()
        ]

    def get_vigencia_efectiva(self, obj):
        from apps.convenios import selectors
        return selectors.vigencia_efectiva(obj)

    def get_partes_firmantes(self, obj) -> list:
        return ConventionPartySerializer(obj.partes_firmantes.all(), many=True).data


class ConventionBulkUploadSerializer(serializers.Serializer):
    """Entrada de la carga masiva de convenios (solo Administrador RENADS)."""

    archivo = serializers.FileField(help_text="Archivo Excel (.xlsx) con los convenios a registrar")


class ClinicalFieldRegistrationBulkUploadSerializer(serializers.Serializer):
    """Entrada de la carga masiva de determinación de campos clínicos (solo Administrador RENADS)."""

    archivo = serializers.FileField(
        help_text="Archivo Excel (.xlsx) con la determinación de campos — estructura de TramaDeterminacionCampos.xlsx"
    )


class ClinicalFieldAllocationBulkUploadSerializer(serializers.Serializer):
    """Entrada de la carga masiva de asignación de campos clínicos (solo Administrador RENADS)."""

    archivo = serializers.FileField(
        help_text="Archivo Excel (.xlsx) con la asignación de campos — estructura de TramaAsignacionCampos.xlsx"
    )



class ConventionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Convention
        # `nomenclatura` habilitado temporalmente para alta/edición directa (Específicos).
        # La asignación automática por validación técnica del Marco (RN A3) sigue vigente.
        fields = [
            "tipo_convenio", "convenio_marco", "plantilla", "titulo", "nomenclatura",
            "solicitante_tipo_contenido", "solicitante_id_objeto",
            "organo_directorio", "gobierno_regional", "universidad",
            "unidad_ejecutora", "facultad",
            "fecha_solicitud", "fecha_inicio", "fecha_fin", "max_campos_clinicos",
        ]


class AdendaWriteSerializer(serializers.Serializer):
    """Entrada de la acción `conventions/{id}/adenda` — nuevo periodo de la adenda."""

    titulo = serializers.CharField(required=False, allow_blank=True)
    nomenclatura = serializers.CharField(required=False, allow_blank=True)
    fecha_solicitud = serializers.DateField(required=False)
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField(required=False)


class SolicitanteContentTypeSerializer(serializers.Serializer):
    """Tipo de entidad elegible como solicitante de un convenio (`ContentType`).

    `id` es el valor que espera `solicitante_tipo_contenido`; `model` permite al cliente
    resolver el endpoint de la entidad concreta. Los ids dependen de la base de datos.
    """

    id = serializers.IntegerField(help_text="ID del ContentType (valor de solicitante_tipo_contenido)")
    app_label = serializers.CharField(help_text="App de Django (p. ej. convenios)")
    model = serializers.CharField(help_text="Modelo de Django (p. ej. university, conapres)")


class ConventionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConventionTemplate
        fields = "__all__"


class ConventionParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConventionParticipant
        fields = [
            "id", "convenio", "tipo_contenido", "id_objeto",
            "tipo_autoridad_firmante", "es_firmante", "creado_en",
        ]
        read_only_fields = ["convenio", "creado_en"]


class ConventionPartySerializer(serializers.ModelSerializer):
    """Parte firmante estructurada del convenio (rol + órgano + representante + cargo).

    El `convenio` se toma de la URL de la acción (read-only). La coherencia
    órgano↔representante↔cargo y la composición de roles las valida el service
    `sincronizar_partes`. Los campos `*_detalle` son de solo lectura para los listados.
    """

    rol_display = serializers.CharField(source="get_rol_display", read_only=True)
    organo_directorio_detalle = serializers.SerializerMethodField()
    organo_representante_detalle = serializers.SerializerMethodField()
    cargo_ejecutivo_detalle = serializers.SerializerMethodField()

    class Meta:
        model = ConventionParty
        fields = [
            "id", "convenio", "rol", "rol_display",
            "organo_directorio", "organo_directorio_detalle",
            "organo_representante", "organo_representante_detalle",
            "cargo_ejecutivo", "cargo_ejecutivo_detalle",
            "orden", "es_firmante", "creado_en",
        ]
        read_only_fields = ["id", "convenio", "creado_en"]

    def get_organo_directorio_detalle(self, obj):
        return _detalle_fk(obj.organo_directorio, "nombre", "siglas")

    def get_organo_representante_detalle(self, obj):
        return _detalle_fk(obj.organo_representante, "nombre", "numero_documento_identidad")

    def get_cargo_ejecutivo_detalle(self, obj):
        return _detalle_fk(obj.cargo_ejecutivo, "nombre_masculino", "nombre_femenino")


class ConventionStatusHistorySerializer(serializers.ModelSerializer):
    estado = serializers.CharField(source="estado.nombre", read_only=True)
    estado_codigo = serializers.CharField(source="estado.codigo", read_only=True)

    class Meta:
        model = ConventionStatusHistory
        fields = ["id", "estado", "estado_codigo", "cambiado_por", "cambiado_en", "observacion"]


# ---------------------------------------------------------------------------
# Entradas de las acciones de flujo (convenio se toma de la URL)
# ---------------------------------------------------------------------------
class CambiarEstadoSerializer(serializers.Serializer):
    estado_codigo = serializers.CharField()
    observacion = serializers.CharField(required=False, allow_blank=True, default="")


class TechnicalEvaluationSerializer(serializers.ModelSerializer):
    # `nomenclatura` es entrada de la acción `validar-tecnica`: se exige y persiste en
    # el convenio (solo Marco validado); NO es campo de `evaluacion_tecnica`.
    nomenclatura = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = TechnicalEvaluation
        fields = [
            "resultado", "observaciones", "subsanacion", "organo_directorio",
            "fecha_evaluacion", "nomenclatura",
        ]


class ConapresOpinionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConapresOpinion
        fields = ["fecha_solicitud", "estado_atencion", "resultado_opinion", "fecha_respuesta"]


def _detalle_fk(rel, *campos: str):
    """Detalle legible de una FK (o ``None``): ``{id, <campos…>}``.

    Permite que los listados del frontend muestren nombres sin resolver ids.
    """
    if rel is None:
        return None
    # `pk` soporta tanto PK numérica como textual (p. ej. ExecutingUnit.codigo, mig 0045).
    detalle = {"id": rel.pk}
    for campo in campos:
        detalle[campo] = getattr(rel, campo, None)
    return detalle


class ClinicalFieldRegistrationSerializer(serializers.ModelSerializer):
    """Registro (CONAPRES) del total de campos clínicos por sede + carrera.

    `campos_clinicos_asignados` es un acumulador de solo lectura (lo mantiene el
    service); `disponibilidad` = registrados − asignados. Los campos `*_detalle`
    son de solo lectura para poblar los listados del frontend.
    """

    disponibilidad = serializers.SerializerMethodField()
    ipress_detalle = serializers.SerializerMethodField()
    carrera_profesional_detalle = serializers.SerializerMethodField()
    especialidad_detalle = serializers.SerializerMethodField()

    class Meta:
        model = ClinicalFieldRegistration
        fields = [
            "id", "ipress", "carrera_profesional", "especialidad",
            "campos_clinicos_registrados", "campos_clinicos_asignados", "disponibilidad",
            "numero_resolucion_conapres", "fecha_resolucion_conapres",
            "ipress_detalle", "carrera_profesional_detalle", "especialidad_detalle",
            "creado_en", "creado_por", "actualizado_en", "actualizado_por",
        ]
        read_only_fields = [
            "id", "campos_clinicos_asignados", "creado_en", "creado_por",
            "actualizado_en", "actualizado_por",
        ]

    def get_disponibilidad(self, obj) -> int:
        return obj.campos_clinicos_registrados - obj.campos_clinicos_asignados

    def get_ipress_detalle(self, obj):
        ip = obj.ipress
        if ip is None:
            return None
        ue = ip.unidad_ejecutora
        ags = ip.ambito_geografico_sanitario
        return {
            "id": ip.pk,
            "nombre": ip.nombre,
            "codigo_renipress": ip.codigo_renipress,
            "unidad_ejecutora": {"id": ue.pk, "nombre": ue.nombre} if ue else None,
            "ambito_geografico_sanitario": {"id": ags.pk, "nombre": ags.nombre} if ags else None,
        }

    def get_carrera_profesional_detalle(self, obj):
        return _detalle_fk(obj.carrera_profesional, "nombre")

    def get_especialidad_detalle(self, obj):
        return _detalle_fk(obj.especialidad, "nombre")

    def validate_campos_clinicos_registrados(self, value):
        if value <= 0:
            raise serializers.ValidationError("Debe ser un entero positivo.")
        return value


class ClinicalFieldAllocationSerializer(serializers.ModelSerializer):
    """Asignación (Órgano Regional) de campos clínicos por universidad.

    El cliente solo envía `campo_clinico_ipress`, `convenio`, las fechas y
    `campos_clinicos_autorizados`. La sede (`ipress`), la carrera, la especialidad y
    la `universidad` se **derivan** en el service (del registro padre y del convenio),
    por lo que aquí son de solo lectura. La disponibilidad, la coherencia con el
    registro y el convenio vigente se validan en el service.
    """

    convenio_detalle = serializers.SerializerMethodField()
    ipress_detalle = serializers.SerializerMethodField()
    carrera_profesional_detalle = serializers.SerializerMethodField()
    especialidad_detalle = serializers.SerializerMethodField()
    universidad_detalle = serializers.SerializerMethodField()

    class Meta:
        model = ClinicalFieldAllocation
        fields = [
            "id", "campo_clinico_ipress", "convenio", "ipress", "carrera_profesional",
            "especialidad", "universidad", "fecha_inicio", "fecha_fin",
            "campos_clinicos_autorizados",
            "convenio_detalle", "ipress_detalle", "carrera_profesional_detalle",
            "especialidad_detalle", "universidad_detalle",
            "creado_en", "creado_por", "actualizado_en", "actualizado_por",
        ]
        read_only_fields = [
            "id", "ipress", "carrera_profesional", "especialidad", "universidad",
            "creado_en", "creado_por", "actualizado_en", "actualizado_por",
        ]

    def get_convenio_detalle(self, obj):
        return _detalle_fk(obj.convenio, "titulo", "nomenclatura")

    def get_ipress_detalle(self, obj):
        ip = obj.ipress
        if ip is None:
            return None
        ue = ip.unidad_ejecutora
        ags = ip.ambito_geografico_sanitario
        return {
            "id": ip.pk,
            "nombre": ip.nombre,
            "codigo_renipress": ip.codigo_renipress,
            "unidad_ejecutora": {"id": ue.pk, "nombre": ue.nombre} if ue else None,
            "ambito_geografico_sanitario": {"id": ags.pk, "nombre": ags.nombre} if ags else None,
        }

    def get_carrera_profesional_detalle(self, obj):
        return _detalle_fk(obj.carrera_profesional, "nombre")

    def get_especialidad_detalle(self, obj):
        return _detalle_fk(obj.especialidad, "nombre")

    def get_universidad_detalle(self, obj):
        return _detalle_fk(obj.universidad, "nombre", "siglas")

    def validate_campos_clinicos_autorizados(self, value):
        if value <= 0:
            raise serializers.ValidationError("Debe ser un entero positivo.")
        return value

    def validate(self, attrs):
        fecha_inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        fecha_fin = attrs.get("fecha_fin", getattr(self.instance, "fecha_fin", None))
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha de fin no puede ser anterior a la de inicio."}
            )
        return attrs


class LegalOpinionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalOpinion
        fields = [
            "fecha_envio", "resultado_opinion", "observaciones_legales",
            "subsanacion", "fecha_respuesta",
        ]


class SignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signature
        fields = [
            "firmante_tipo_contenido", "firmante_id_objeto", "tipo_autoridad_firmante",
            "orden_firma", "fecha_envio", "fecha_recepcion", "estado_firma", "observaciones",
        ]


class PublicationSerializer(serializers.ModelSerializer):
    fecha_inicio = serializers.DateField(required=False, allow_null=True, write_only=True)
    fecha_fin = serializers.DateField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Publication
        fields = ["fecha_publicacion", "referencia_publicacion", "fecha_inicio", "fecha_fin"]


# Modelos que un representante puede representar (relación polimórfica `entidad`).
# Se validan por `app_label.model` para no depender de ids de ContentType.
REPRESENTANTE_MODELOS_PERMITIDOS = {
    "convenios.organdirectory",
    "convenios.university",
    "convenios.executingunit",
    "convenios.conapres",
    "convenios.ipress",
}


class OrganRepresentativeSerializer(serializers.ModelSerializer):
    """Representante de una entidad (relación polimórfica `entidad`).

    Valida: (a) unicidad del documento entre representantes activos, (b) que la entidad
    (`tipo_contenido`) sea uno de los modelos permitidos, y (c) la coherencia cargo↔entidad
    (cargo por órgano ⇒ la entidad debe ser ese OrganDirectory; cargo global ⇒ cualquiera).
    La baja del representante anterior (histórico) la resuelve el service
    ``registrar_organo_representante``.
    """

    entidad_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OrganRepresentative
        fields = "__all__"

    def get_entidad_detalle(self, obj):
        """`{tipo, id, nombre}` de la entidad representada (para mostrar sin joins)."""
        entidad = obj.entidad
        if entidad is None:
            return None
        return {
            "tipo": obj.tipo_contenido.model,
            "id": obj.id_objeto,
            "nombre": str(entidad),
        }

    def validate(self, attrs):
        tipo_doc = attrs.get(
            "tipo_documento_identidad", getattr(self.instance, "tipo_documento_identidad", None)
        )
        numero = attrs.get(
            "numero_documento_identidad", getattr(self.instance, "numero_documento_identidad", None)
        )
        if tipo_doc is not None and numero:
            qs = OrganRepresentative.objects.filter(
                tipo_documento_identidad=tipo_doc,
                numero_documento_identidad=numero,
                activo=True,
            )
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"numero_documento_identidad": "Ya existe un representante activo con ese documento."}
                )

        tipo_contenido = attrs.get(
            "tipo_contenido", getattr(self.instance, "tipo_contenido", None)
        )
        id_objeto = attrs.get("id_objeto", getattr(self.instance, "id_objeto", None))

        # (b) La entidad debe ser uno de los modelos permitidos y existir.
        if tipo_contenido is not None:
            etiqueta = f"{tipo_contenido.app_label}.{tipo_contenido.model}"
            if etiqueta not in REPRESENTANTE_MODELOS_PERMITIDOS:
                raise serializers.ValidationError(
                    {"tipo_contenido": "Tipo de entidad no permitido para representantes."}
                )
            if id_objeto is not None:
                modelo = tipo_contenido.model_class()
                if modelo is None or not modelo._default_manager.filter(pk=id_objeto).exists():
                    raise serializers.ValidationError(
                        {"id_objeto": "La entidad referenciada no existe."}
                    )

        # (c) Coherencia cargo↔entidad (D4): un cargo con órgano directivo asignado solo
        # aplica a ese OrganDirectory; un cargo global (sin órgano) aplica a cualquiera.
        cargo = attrs.get("cargo_ejecutivo", getattr(self.instance, "cargo_ejecutivo", None))
        if cargo is not None and cargo.organo_directivo_id:
            es_organ_directory = (
                tipo_contenido is not None
                and tipo_contenido.model == "organdirectory"
            )
            if not es_organ_directory or cargo.organo_directivo_id != id_objeto:
                raise serializers.ValidationError(
                    {"cargo_ejecutivo": "El cargo no corresponde a la entidad seleccionada."}
                )
        return attrs


# ---------------------------------------------------------------------------
# Documento (gestión documental polimórfica con versionado)
# ---------------------------------------------------------------------------
class DocumentSerializer(serializers.ModelSerializer):
    """Lectura de documentos: incluye etiquetas legibles del anexo y la entidad destino."""

    documento_anexo_nombre = serializers.CharField(source="documento_anexo.nombre", read_only=True)
    tipo_contenido_label = serializers.CharField(source="tipo_contenido.model", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "documento_anexo", "documento_anexo_nombre",
            "tipo_contenido", "tipo_contenido_label", "id_objeto",
            "referencia_externa",
            "version", "estado",
            "version_anterior", "cargado_por", "cargado_en",
        ]
        read_only_fields = [
            "version", "estado", "version_anterior",
            "cargado_por", "cargado_en",
        ]


class DocumentWriteSerializer(serializers.ModelSerializer):
    """Escritura de documentos: el versionado y el estado los fija el service."""

    class Meta:
        model = Document
        fields = [
            "tipo_contenido", "id_objeto", "documento_anexo",
            "referencia_externa",
        ]

    def validate(self, attrs):
        tipo_contenido = attrs.get("tipo_contenido")
        id_objeto = attrs.get("id_objeto")
        try:
            tipo_contenido.get_object_for_this_type(pk=id_objeto)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                {"id_objeto": "El objeto destino indicado no existe."}
            )
        return attrs


# Extensiones aceptadas por content-type, como refuerzo a la validación MIME.
EXTENSIONES_POR_CONTENT_TYPE = {
    "application/pdf": {".pdf"},
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
}


class ActiveAnnexDocumentField(serializers.PrimaryKeyRelatedField):
    """PK del anexo activo (`documento_anexo`), con queryset perezoso.

    Resuelve el modelo `internados.AnnexDocument` en `get_queryset` (import
    perezoso) para evitar el ciclo de import convenios <-> internados.
    """

    def get_queryset(self):
        from apps.internados.models import AnnexDocument

        return AnnexDocument.objects.filter(activo=True)


class DocumentUploadSerializer(serializers.Serializer):
    """Subida real de un documento (multipart): valida tipo y tamaño del binario.

    Recibe el binario en `archivo` junto con los metadatos necesarios para
    adjuntarlo a un objeto (relación genérica). El discriminador de versionado es
    el `documento_anexo` (obligatorio). El `nombre_archivo` se usa solo como ruta
    de storage; no se persiste en `Document`. El versionado y la auditoría los
    resuelve el service `adjuntar_documento`; este serializer solo valida la
    entrada. Mensajes de error en español.
    """

    archivo = serializers.FileField(help_text="Binario a subir (PDF o imagen)")
    documento_anexo = ActiveAnnexDocumentField(
        pk_field=serializers.IntegerField(),
        help_text="Anexo/tipo del catálogo maestro (documento_anexo) que se adjunta",
    )
    tipo_contenido = serializers.PrimaryKeyRelatedField(
        queryset=ContentType.objects.all(), help_text="Tabla destino"
    )
    id_objeto = serializers.IntegerField(min_value=1, help_text="Registro destino")
    nombre_archivo = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Nombre del archivo (si falta, se deriva del archivo subido)",
    )

    def validate_archivo(self, archivo):
        content_type = getattr(archivo, "content_type", "") or ""
        if content_type not in settings.GCS_ALLOWED_CONTENT_TYPES:
            permitidos = ", ".join(settings.GCS_ALLOWED_CONTENT_TYPES)
            raise serializers.ValidationError(
                f"Tipo de archivo no permitido. Se aceptan únicamente: {permitidos}."
            )
        extension = ("." + archivo.name.rsplit(".", 1)[-1].lower()) if "." in archivo.name else ""
        extensiones_validas = EXTENSIONES_POR_CONTENT_TYPE.get(content_type, set())
        if extension not in extensiones_validas:
            raise serializers.ValidationError(
                "La extensión del archivo no corresponde con su tipo de contenido."
            )
        if archivo.size > settings.GCS_MAX_UPLOAD_BYTES:
            maximo_mb = settings.GCS_MAX_UPLOAD_BYTES / (1024 * 1024)
            raise serializers.ValidationError(
                f"El archivo supera el tamaño máximo permitido ({maximo_mb:.0f} MiB)."
            )
        return archivo

    def validate(self, attrs):
        tipo_contenido = attrs.get("tipo_contenido")
        id_objeto = attrs.get("id_objeto")
        try:
            tipo_contenido.get_object_for_this_type(pk=id_objeto)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                {"id_objeto": "El objeto destino indicado no existe."}
            )
        if not attrs.get("nombre_archivo"):
            attrs["nombre_archivo"] = attrs["archivo"].name
        return attrs


# ---------------------------------------------------------------------------
# Subida de logos institucionales (imágenes) — Etapa 2
# ---------------------------------------------------------------------------
# Content-types aceptados para logos: solo imágenes (se excluye PDF a propósito).
LOGO_CONTENT_TYPES = ["image/png", "image/jpeg", "image/webp"]


class LogoUploadSerializer(serializers.Serializer):
    """Subida del logo de una entidad (multipart): valida tipo y tamaño del binario.

    Solo acepta imágenes (`image/png`, `image/jpeg`, `image/webp`); rechaza PDF.
    El logo se guarda como una única key en `referencia_logo` de la entidad (sin
    versionado, sin `Document`). Mensajes de error en español.
    """

    archivo = serializers.FileField(help_text="Imagen del logo (PNG, JPEG o WEBP)")

    def validate_archivo(self, archivo):
        content_type = getattr(archivo, "content_type", "") or ""
        if content_type not in LOGO_CONTENT_TYPES:
            permitidos = ", ".join(LOGO_CONTENT_TYPES)
            raise serializers.ValidationError(
                f"Tipo de imagen no permitido. Se aceptan únicamente: {permitidos}."
            )
        extension = ("." + archivo.name.rsplit(".", 1)[-1].lower()) if "." in archivo.name else ""
        extensiones_validas = EXTENSIONES_POR_CONTENT_TYPE.get(content_type, set())
        if extension not in extensiones_validas:
            raise serializers.ValidationError(
                "La extensión del archivo no corresponde con su tipo de contenido."
            )
        if archivo.size > settings.GCS_MAX_UPLOAD_BYTES:
            maximo_mb = settings.GCS_MAX_UPLOAD_BYTES / (1024 * 1024)
            raise serializers.ValidationError(
                f"El archivo supera el tamaño máximo permitido ({maximo_mb:.0f} MiB)."
            )
        return archivo


# ---------------------------------------------------------------------------
# Subida de anexos (PDFs de declaraciones juradas por actor) — Etapa 2
# ---------------------------------------------------------------------------
class AnnexUploadSerializer(serializers.Serializer):
    """Subida del PDF de un anexo (declaración jurada) por actor (multipart).

    Solo acepta `application/pdf`. El anexo (`documento_anexo`) referencia el
    catálogo maestro `internados.AnnexDocument`; el enforcement de que su
    `tipo_actor` coincide con la entidad destino lo hace el mixin (necesita el
    `annex_actor` del ViewSet). El versionado por `(objeto, documento_anexo)` lo
    resuelve el service `adjuntar_documento`. La ruta de storage se deriva del
    archivo subido dentro del mixin. Mensajes de error en español.
    """

    documento_anexo = ActiveAnnexDocumentField(
        pk_field=serializers.IntegerField(),
        help_text="Anexo del catálogo maestro (documento_anexo) que se adjunta",
    )
    archivo = serializers.FileField(help_text="Archivo PDF del anexo")

    def validate_archivo(self, archivo):
        content_type = getattr(archivo, "content_type", "") or ""
        if content_type != "application/pdf":
            raise serializers.ValidationError(
                "Tipo de archivo no permitido. El anexo debe adjuntarse en formato PDF."
            )
        extension = ("." + archivo.name.rsplit(".", 1)[-1].lower()) if "." in archivo.name else ""
        if extension != ".pdf":
            raise serializers.ValidationError(
                "La extensión del archivo no corresponde con su tipo de contenido (se espera .pdf)."
            )
        if archivo.size > settings.GCS_MAX_UPLOAD_BYTES:
            maximo_mb = settings.GCS_MAX_UPLOAD_BYTES / (1024 * 1024)
            raise serializers.ValidationError(
                f"El archivo supera el tamaño máximo permitido ({maximo_mb:.0f} MiB)."
            )
        return archivo


# ---------------------------------------------------------------------------
# Carreras por universidad (puente universidad ↔ carrera ↔ facultad)
# ---------------------------------------------------------------------------
class UniversityCareerSerializer(serializers.ModelSerializer):
    """Carrera que dicta una universidad, asociada a la facultad que la imparte.

    `facultad` es opcional a nivel de modelo (filas históricas), pero **requerida**
    en la API (RN-FC-03). Se valida que la facultad pertenezca a la universidad del
    registro (RN-FC-02). Los campos `*_detalle` son de solo lectura para poblar los
    listados del frontend sin resolver ids.
    """

    facultad = serializers.PrimaryKeyRelatedField(
        queryset=Faculty.objects.all(), required=True, allow_null=False,
    )
    universidad_detalle = serializers.SerializerMethodField()
    carrera_profesional_detalle = serializers.SerializerMethodField()
    facultad_detalle = serializers.SerializerMethodField()

    class Meta:
        model = UniversityCareer
        fields = "__all__"
        validators = [
            # RN-FC-04: una carrera profesional pertenece a UNA sola facultad por
            # universidad; una vez asignada no puede elegirse desde otra facultad.
            UniqueTogetherValidator(
                queryset=UniversityCareer.objects.all(),
                fields=["universidad", "carrera_profesional"],
                message=(
                    "La carrera profesional ya está asignada a una facultad de esta "
                    "universidad; no puede asignarse a otra facultad."
                ),
            ),
        ]

    def get_universidad_detalle(self, obj):
        return _detalle_fk(obj.universidad, "nombre")

    def get_carrera_profesional_detalle(self, obj):
        return _detalle_fk(obj.carrera_profesional, "nombre")

    def get_facultad_detalle(self, obj):
        return _detalle_fk(obj.facultad, "nombre")

    def validate(self, data):
        """RN-FC-02: la facultad debe pertenecer a la universidad del registro."""
        # En PATCH parcial se toma el valor entrante o el de la instancia.
        universidad = data.get("universidad") or getattr(self.instance, "universidad", None)
        facultad = data.get("facultad") or getattr(self.instance, "facultad", None)
        if universidad is not None and facultad is not None:
            if facultad.universidad_id != universidad.id:
                raise serializers.ValidationError(
                    "La facultad seleccionada no pertenece a la universidad indicada."
                )
        return data


class FacultyCareersSyncSerializer(serializers.Serializer):
    """Entrada de la acción en lote `POST /faculties/{id}/careers`.

    Recibe la lista de carreras profesionales a asociar a la facultad; se permite
    lista vacía para dar de baja todas las carreras activas de la facultad.
    """

    carreras = serializers.PrimaryKeyRelatedField(
        queryset=ProfessionalCareer.objects.all(), many=True, allow_empty=True,
    )


# ---------------------------------------------------------------------------
# Bitácora de auditoría (solo lectura)
# ---------------------------------------------------------------------------
class AuditLogSerializer(serializers.ModelSerializer):
    """Lectura de la bitácora de auditoría (RNF-AUD-01/02). Todos los campos read-only."""

    usuario_nombre = serializers.SerializerMethodField()
    tipo_contenido_label = serializers.CharField(source="tipo_contenido.model", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id", "usuario", "usuario_nombre", "accion",
            "tipo_contenido", "tipo_contenido_label", "id_objeto",
            "nombre_campo", "valor_anterior", "valor_nuevo",
            "direccion_ip", "creado_en",
        ]
        read_only_fields = fields

    def get_usuario_nombre(self, obj) -> str:
        return obj.usuario.get_username() if obj.usuario else ""
