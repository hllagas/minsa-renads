# Validación — Módulo `convenios`: features de soporte transversales (Documento + Bitácora)

Revisión del agente **validator** contra `spec/convenios_transversales.md`,
`docs/db_schema_modulo_01_convenios.md` (§10/§11), `docs/arquitectura_desarrollo.md` (§9/§10)
y los modelos `Document`/`AuditLog` (`apps/convenios/models.py:788`/`819`).

## Resultado

**APROBADO — sin hallazgos altos ni medios.** Las nueve tareas (T1–T9) están implementadas
conforme al spec, sin campos inventados y respetando las convenciones de CLAUDE.md.
Se genera la guía de pruebas manuales en `spec/convenios_transversales.guia_pruebas.md`.

## Comprobaciones técnicas

| Comprobación | Comando | Resultado |
|--------------|---------|-----------|
| System check | `manage.py check` | `System check identified no issues (0 silenced).` |
| Sin migraciones nuevas | `manage.py makemigrations --check --dry-run` | `No changes detected` (exit 0) |

## Cobertura de tareas

| Tarea | Estado | Verificación |
|-------|--------|--------------|
| T1 — `DocumentStorage` (Protocol) + `ReferenciaExternaStorage` + `storage_por_defecto` | OK | `apps/common/storage.py`; firma exacta de §9; `url_firmada` devuelve la referencia; `eliminar` no-op; sin dependencias S3/MinIO/boto3 |
| T2 — `adjuntar_documento` | OK | `apps/common/services.py:33`; `@transaction.atomic`; firma exacta; `ContentType.get_for_model`, `select_for_update().order_by("-version").first()`; versionado v1→vN; `version_anterior`; previo→`REEMPLAZADO` con `update_fields=["estado"]`; auditoría `CREAR` + `CAMBIO_ESTADO`; retorna el `Document` |
| T3 — `DocumentSerializer` / `DocumentWriteSerializer` | OK | `apps/convenios/serializers.py:166`/`185`; lectura con `tipo_documento_nombre` y `tipo_contenido_label`; `read_only_fields` correctos; `validate()` verifica existencia con `get_object_for_this_type` capturando `ObjectDoesNotExist` con mensaje en español |
| T4 — `DocumentViewSet` | OK | `apps/convenios/views.py:346`; `AuditedModelViewSet`; `http_method_names` sin `put`/`patch`; `select_related` completo; `create` sobrescrito delega en `adjuntar_documento` (sin doble auditoría); `perform_destroy` invoca `storage.eliminar` y registra `ELIMINAR`; action `url-descarga`; permisos `IsAuthenticated, IsInstitutionalMember`; filtros y `ordering` correctos |
| T5 — Ruta `documents` | OK | `apps/convenios/urls.py:14`, basename `document` |
| T6 — `AuditLogSerializer` | OK | `apps/convenios/serializers.py:210`; todos los campos `read_only`; `usuario_nombre` (maneja `None`→`""`); `tipo_contenido_label` |
| T7 — `AuditLogFilter` | OK | `apps/convenios/filters.py:37`; `accion_contiene` (icontains), `creado_en_desde/hasta` (DateTimeFilter gte/lte); `Meta.fields` dict con `usuario`/`accion`/`tipo_contenido`/`id_objeto` |
| T8 — `AuditLogViewSet` | OK | `apps/convenios/views.py:392`; `ReadOnlyModelViewSet`; `IsAuthenticated, IsAdminRole`; `filterset_class`; `search_fields=["accion"]`; `ordering=["-creado_en"]` |
| T9 — Ruta `audit-logs` | OK | `apps/convenios/urls.py:15`, basename `audit-log` |

## Consistencia con schema (§10/§11)

- `Document`: todos los campos serializados (`tipo_documento`, `tipo_contenido`, `id_objeto`,
  `referencia_externa`, `nombre_archivo`, `version`, `estado`, `version_anterior`, `cargado_por`,
  `cargado_en`) coinciden con la tabla `documento`. Sin campos inventados.
- `AuditLog`: campos (`usuario`, `accion`, `tipo_contenido`, `id_objeto`, `nombre_campo`,
  `valor_anterior`, `valor_nuevo`, `direccion_ip`, `creado_en`) coinciden con `bitacora_auditoria`.
- Estados usados (`ACTIVO`/`REEMPLAZADO`) pertenecen a `DOCUMENT_STATUS` (`models.py:782`).

## Convenciones (CLAUDE.md)

- Código en inglés; docstrings, `help_text` y mensajes de error al usuario en español. OK.
- ViewSets delgados: la escritura/versionado vive en el service `adjuntar_documento`; la auditoría
  se emite desde el service; `transaction.atomic()` presente. OK.
- Sin migraciones nuevas; sin tests automatizados; sin backend real de almacenamiento. OK.

## Notas informativas (severidad: baja — no requieren acción)

1. `AuditLogViewSet` usa `IsAdminRole`, que solo cubre superusuario y grupo «Administrador RENADS».
   El spec lo solicitó explícitamente así (T8.1); la mención de «Auditor» en el encabezado es
   contextual. Si en el futuro se desea habilitar el rol Auditor para consulta de bitácora, deberá
   ampliarse `IsAdminRole` o crearse un permiso dedicado. No es un defecto contra este spec.
2. En `DocumentViewSet.create` se re-resuelve el objeto destino con `get_object_for_this_type`
   tras haberlo validado el serializer; redundancia menor y segura (el serializer ya garantiza su
   existencia). Aceptable.
