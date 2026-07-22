"""Mixins transversales de adjunto real (Etapa 2 de `spec/almacenamiento.md`).

Dos mixins reutilizables por los ViewSets de entidades:

- `LogoStorageMixin`: sube/reemplaza el logo (imagen) de una entidad con columna
  `referencia_logo`, guardando una única key (sin versionado, sin `Document`) y
  devolviendo un signed URL efímero para mostrarlo.
- `AnnexAttachmentMixin`: adjunta el PDF real de un anexo (declaración jurada) del
  catálogo maestro `documentos_anexos` como `Document` versionado por
  `(objeto, documento_anexo)`, con enforcement del `tipo_actor` del anexo.

Ambos resuelven el backend de almacenamiento por settings (GCS o stub) vía
`get_document_storage()` y respetan los `permission_classes` del ViewSet destino
(no relajan permisos). Cada acción lleva `@extend_schema` para OpenAPI/Swagger.
Clases/acciones en inglés; docstrings/mensajes de error en español.
"""

from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.common.documentai import extraer_texto_pdf
from apps.common.services import adjuntar_documento, registrar_auditoria
from apps.common.storage import get_document_storage
from apps.convenios.serializers import (
    AnnexUploadSerializer,
    DocumentSerializer,
    LogoUploadSerializer,
)


class LogoStorageMixin:
    """Sube/consulta el logo de una entidad con columna `referencia_logo`.

    La entidad destino es `self.get_object()` (debe exponer `referencia_logo`).
    El logo se guarda como una única key en `referencia_logo`; al reemplazarlo se
    borra la key anterior. No versiona ni usa `Document`.
    """

    @property
    def storage(self):
        """Backend de almacenamiento seleccionado por settings (GCS o stub)."""
        return get_document_storage()

    @extend_schema(
        request=LogoUploadSerializer,
        responses=inline_serializer(
            name="LogoUploadResponse",
            fields={
                "referencia_logo": drf_serializers.CharField(),
                "url": drf_serializers.CharField(),
            },
        ),
        summary="Subir/reemplazar el logo de la entidad",
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="upload-logo",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_logo(self, request, pk=None):
        """Sube (o reemplaza) el logo de la entidad y devuelve un signed URL.

        Sube la nueva imagen primero; si la entidad ya tenía un logo, se borra la
        key anterior **después** de subir la nueva (no dejar la entidad sin logo si
        la subida falla). Persiste la nueva key en `referencia_logo` y registra
        auditoría. Responde `{referencia_logo, url}` (signed URL efímero).
        """
        entidad = self.get_object()
        ser = LogoUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        archivo = ser.validated_data["archivo"]

        logo_anterior = entidad.referencia_logo
        nueva_key = self.storage.subir(archivo, ruta=archivo.name)
        if logo_anterior:
            # Tolerante a inexistencia (el backend hace no-op si el objeto ya no está).
            self.storage.eliminar(logo_anterior)

        entidad.referencia_logo = nueva_key
        entidad.save(update_fields=["referencia_logo"])
        registrar_auditoria(
            request.user,
            "ACTUALIZAR",
            entidad,
            nombre_campo="referencia_logo",
            valor_anterior=logo_anterior,
            valor_nuevo=nueva_key,
        )
        return Response(
            {"referencia_logo": nueva_key, "url": self.storage.url_firmada(nueva_key)}
        )

    @extend_schema(
        responses=inline_serializer(
            name="LogoUrlResponse",
            fields={"url": drf_serializers.CharField()},
        ),
        summary="Obtener el signed URL del logo de la entidad",
    )
    @action(detail=True, methods=["get"], url_path="logo-url")
    def logo_url(self, request, pk=None):
        """Devuelve un signed URL efímero del logo, o 404 si no hay logo cargado."""
        entidad = self.get_object()
        if not entidad.referencia_logo:
            raise NotFound("La entidad no tiene un logo cargado.")
        return Response({"url": self.storage.url_firmada(entidad.referencia_logo)})


class AnnexAttachmentMixin:
    """Adjunta y lista los PDFs de anexos (declaraciones juradas) por actor.

    Atributo de clase obligatorio `annex_actor` (uno de `ANNEX_ACTOR`:
    `"INTERNO"` / `"AUTORIDAD_UNIVERSIDAD"` / `"REPRESENTANTE"`): restringe qué
    anexos del catálogo maestro puede adjuntar la entidad destino. Cada anexo se
    guarda como `Document` versionado por `(objeto, documento_anexo)`.
    """

    annex_actor: str = ""

    @property
    def storage(self):
        """Backend de almacenamiento seleccionado por settings (GCS o stub)."""
        return get_document_storage()

    def _tipo_documento_anexo(self):
        """Resuelve el `DocumentType` `ANEXO` por `codigo` (no por PK)."""
        from apps.convenios.models import DocumentType

        return DocumentType.objects.get(codigo="ANEXO")

    @extend_schema(
        request=AnnexUploadSerializer,
        responses=DocumentSerializer,
        summary="Adjuntar el PDF de un anexo (declaración jurada)",
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="annex-upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def annex_upload(self, request, pk=None):
        """Sube el PDF de un anexo y lo adjunta versionado a la entidad.

        Valida (solo PDF, tamaño), verifica que el `documento_anexo` sea del
        `tipo_actor` de este ViewSet (`annex_actor`), sube el binario al backend
        seleccionado por settings y llama `adjuntar_documento(..., documento_anexo=...)`
        (versionado por anexo + auditoría). Responde `201` con el `Document`.
        """
        entidad = self.get_object()
        ser = AnnexUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        anexo = ser.validated_data["documento_anexo"]

        if anexo.tipo_actor != self.annex_actor:
            raise ValidationError(
                {"documento_anexo": "El anexo seleccionado no corresponde a este tipo de actor."}
            )

        nombre_archivo = ser.validated_data["nombre_archivo"]
        archivo = ser.validated_data["archivo"]
        referencia = self.storage.subir(archivo, ruta=nombre_archivo)
        # El anexo siempre es PDF: se extrae su texto con Document AI (best-effort).
        texto_extraido = extraer_texto_pdf(archivo)
        documento = adjuntar_documento(
            entidad,
            tipo_documento=self._tipo_documento_anexo(),
            nombre_archivo=nombre_archivo,
            referencia_externa=referencia,
            usuario=request.user,
            documento_anexo=anexo,
            texto_extraido=texto_extraido,
        )
        return Response(DocumentSerializer(documento).data, status=201)

    @extend_schema(
        responses=OpenApiResponse(
            response=inline_serializer(
                name="AnnexChecklistItem",
                fields={
                    "documento_anexo": drf_serializers.IntegerField(),
                    "codigo": drf_serializers.CharField(),
                    "nombre": drf_serializers.CharField(),
                    "obligatorio": drf_serializers.BooleanField(),
                    "adjuntado": drf_serializers.BooleanField(),
                    "documento_id": drf_serializers.IntegerField(allow_null=True),
                    "version": drf_serializers.IntegerField(allow_null=True),
                    "referencia_externa": drf_serializers.CharField(allow_null=True),
                },
            ),
            description="Lista de anexos requeridos del actor con su estado de adjunto.",
        ),
        summary="Checklist de anexos requeridos vs. adjuntados",
    )
    @action(detail=True, methods=["get"], url_path="annex-checklist")
    def annex_checklist(self, request, pk=None):
        """Lista los anexos activos del actor con su estado de adjunto por versión activa.

        Cruza el catálogo maestro (`AnnexDocument` activos de `tipo_actor ==
        annex_actor`) con los `Document` `ACTIVO` de esta entidad que apuntan a
        cada anexo. Es la base del checklist requeridos (`obligatorio=True`) vs.
        adjuntados.
        """
        from apps.convenios.models import Document
        from apps.internados.models import AnnexDocument

        entidad = self.get_object()
        tipo_contenido = ContentType.objects.get_for_model(type(entidad))

        anexos = AnnexDocument.objects.filter(
            activo=True, tipo_actor=self.annex_actor
        ).order_by("id")
        documentos = {
            doc.documento_anexo_id: doc
            for doc in Document.objects.filter(
                tipo_contenido=tipo_contenido,
                id_objeto=entidad.pk,
                estado="ACTIVO",
                documento_anexo__isnull=False,
            )
        }

        items = []
        for anexo in anexos:
            doc = documentos.get(anexo.pk)
            items.append(
                {
                    "documento_anexo": anexo.pk,
                    "codigo": anexo.codigo,
                    "nombre": anexo.nombre,
                    "obligatorio": anexo.obligatorio,
                    "adjuntado": doc is not None,
                    "documento_id": doc.pk if doc else None,
                    "version": doc.version if doc else None,
                    "referencia_externa": doc.referencia_externa if doc else None,
                }
            )
        return Response(items)
