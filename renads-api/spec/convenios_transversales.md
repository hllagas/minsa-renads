# Spec — Módulo `convenios`: features de soporte transversales (Documento + Bitácora de consulta)

Lista de tareas exactas para cerrar las **dos brechas** del soporte del Módulo 1 según
[arquitectura](../docs/arquitectura_desarrollo.md) (§9 adjuntos, §10 auditoría) y
[schema M1](../docs/db_schema_modulo_01_convenios.md) (§10 `documento`, §11 `bitacora_auditoria`).
Producido por el agente **spec** (SDD). El agente **implement** ejecuta estas tareas en orden; el
**validator** revisa contra este documento y genera `spec/convenios_transversales.validacion.md`.

> **No tocar `spec/convenios.md`** (núcleo ya cerrado y validado). Este spec es aditivo.

## Resumen

El núcleo del convenio, catálogos, entidades (GORE/MINSA/CONAPRES/universidades), perfil
institucional y la **escritura** de auditoría ya están implementados y validados. Restan **dos
features de soporte**:

- **Feature A — Documento (RNF-DOC-01/02/03/04):** gestión documental polimórfica adjunta a cualquier
  entidad del flujo vía relación genérica (`tipo_contenido` + `id_objeto`), con **versionado**
  (`version`, `version_anterior`, `estado`) y almacenamiento por **referencia externa (stub)**. El
  modelo `Document` (`apps/convenios/models.py:788`, tabla `documento`) ya existe y está migrado; falta
  storage, service, serializers, ViewSet y endpoint.
- **Feature B — Bitácora de consulta (RNF-AUD-01/02):** endpoint **solo lectura** sobre `AuditLog`
  (`apps/convenios/models.py:819`, tabla `bitacora_auditoria`), restringido a Administrador RENADS /
  Auditor, con filtros por usuario, acción, entidad, objeto y rango de fechas. La **escritura** ya
  existe vía `registrar_auditoria` (`apps/common/services.py:8`).

**Convenciones (CLAUDE.md):** clases/funciones/endpoints en inglés; campos/tablas/`help_text`,
docstrings, comentarios y mensajes de error al usuario en español. ViewSets delgados: escritura vía
services, lectura vía selectors. Auditoría explícita desde services. Todo dentro de
`transaction.atomic()`.

**Entidades cubiertas:** `Document` (tabla `documento`), `AuditLog` (tabla `bitacora_auditoria`).

**Restricciones de alcance:**
- **No** crear migraciones nuevas (los modelos ya están migrados). `makemigrations` debe salir vacío.
- **No** crear archivos de tests automatizados (verificación por `/code-review` + guía manual, regla MVP).
- **No** integrar backend real de almacenamiento (S3/MinIO/boto3); solo el stub de referencia externa.

---

## Feature A — Documento

### T1 — Abstracción de almacenamiento (`apps/common/storage.py` — CREAR)

Crear el archivo `apps/common/storage.py` con:

- **T1.1** `DocumentStorage` como `typing.Protocol` (interfaz, sin herencia obligatoria), con la firma
  exacta de `docs/arquitectura_desarrollo.md` §9:
  ```python
  class DocumentStorage(Protocol):
      def subir(self, archivo, ruta: str) -> str: ...      # devuelve referencia_externa
      def url_firmada(self, referencia: str) -> str: ...
      def eliminar(self, referencia: str) -> None: ...
  ```
- **T1.2** `ReferenciaExternaStorage` — implementación **stub** que NO usa backend real:
  - `subir(self, archivo, ruta)`: en el stub el cliente ya envía la `referencia_externa`; este método
    devuelve la `ruta`/referencia recibida sin contactar ningún backend (no maneja binarios).
  - `url_firmada(self, referencia)`: devuelve la `referencia` tal cual (es ya una clave/URL externa).
    No firma criptográficamente; documentar en docstring que es un stub hasta integrar el repositorio real.
  - `eliminar(self, referencia)`: no-op (no hay backend); documentar como stub.
- **T1.3** Exponer una instancia o factory por defecto reutilizable (p. ej.
  `storage_por_defecto = ReferenciaExternaStorage()`) para inyectar en service y ViewSet.

**Reglas:** ninguna dependencia de S3/MinIO/boto3. Docstrings en español. Tipos anotados.

**Criterio de aceptación:** el módulo importa sin error; `ReferenciaExternaStorage` cumple
estructuralmente el `Protocol`; `url_firmada(ref)` devuelve la referencia recibida; no hay I/O de red.

---

### T2 — Service `adjuntar_documento` (`apps/common/services.py` — EDITAR)

Añadir al archivo existente (junto a `registrar_auditoria`):

- **T2.1** Firma exacta:
  ```python
  def adjuntar_documento(
      objeto, *, tipo_documento, nombre_archivo, referencia_externa, usuario,
  ) -> Document:
  ```
  donde `objeto` es la instancia destino (relación genérica), `tipo_documento` es una instancia de
  `DocumentType` (o su `id`), `nombre_archivo` y `referencia_externa` son `str`, `usuario` el actor.
- **T2.2** Toda la operación dentro de `transaction.atomic()`.
- **T2.3** **Versionado (RNF-DOC-04), comportamiento exacto y sin ambigüedad:**
  1. Resolver el `ContentType` del `objeto` con `ContentType.objects.get_for_model(type(objeto))`.
  2. Buscar el **documento activo previo** del mismo `(tipo_contenido, id_objeto, tipo_documento)` con
     `estado == "ACTIVO"`. Debe existir a lo sumo uno; si hubiera más de uno, tomar el de mayor
     `version` (y `select_for_update()` para evitar carreras).
  3. **Si NO existe previo:** crear `Document` con `version = 1`, `estado = "ACTIVO"`,
     `version_anterior = None`.
  4. **Si existe previo (`anterior`):** crear el nuevo `Document` con
     `version = anterior.version + 1`, `estado = "ACTIVO"`, `version_anterior = anterior`; y marcar
     `anterior.estado = "REEMPLAZADO"` guardándolo (solo el campo `estado`).
  5. En ambos casos fijar `referencia_externa`, `nombre_archivo`, `tipo_documento`, `tipo_contenido`,
     `id_objeto = objeto.pk`, `cargado_por = usuario`. `cargado_en` lo fija `auto_now_add`.
- **T2.4** **Auditoría:** tras crear el documento, llamar
  `registrar_auditoria(usuario, "CREAR", documento)`. Si hubo reemplazo, registrar además
  `registrar_auditoria(usuario, "CAMBIO_ESTADO", anterior, nombre_campo="estado",
  valor_anterior="ACTIVO", valor_nuevo="REEMPLAZADO")`.
- **T2.5** Devolver la nueva instancia `Document` creada.
- **T2.6** Import de `Document` desde `apps.convenios.models` (mismo patrón que `AuditLog`).

**Reglas de negocio (van en el service, no en serializer):** resolución de `version`, enlace
`version_anterior`, transición de estado del previo a `REEMPLAZADO`, atomicidad y auditoría.

**Criterio de aceptación:** primer adjunto de un `(objeto, tipo_documento)` queda `version=1` /
`ACTIVO` / `version_anterior=None`; segundo adjunto del mismo par queda `version=2` / `ACTIVO`
enlazado al primero, y el primero pasa a `REEMPLAZADO`; se generan los registros de auditoría
correspondientes; todo es atómico (si falla cualquier paso, no queda estado parcial).

---

### T3 — Serializers de Documento (`apps/convenios/serializers.py` — EDITAR)

- **T3.1** `DocumentSerializer` (**lectura**): expone `id`, `tipo_documento` (id + nombre legible vía
  `source="tipo_documento.nombre"` en campo read-only auxiliar), `tipo_contenido` (id + label legible,
  p. ej. `tipo_contenido_label` con `source="tipo_contenido.model"` o `__str__`), `id_objeto`,
  `referencia_externa`, `nombre_archivo`, `version`, `estado`, `version_anterior`, `cargado_por`,
  `cargado_en`. Campos gestionados por el service (`version`, `estado`, `version_anterior`,
  `cargado_por`, `cargado_en`) en `read_only`.
- **T3.2** `DocumentWriteSerializer` (**escritura**): acepta `tipo_contenido`, `id_objeto`,
  `tipo_documento`, `nombre_archivo`, `referencia_externa`. **Validación (en serializer):**
  - `validate(...)` debe verificar que **el objeto destino existe**: el par
    `(tipo_contenido, id_objeto)` debe resolver a un registro real (usar
    `tipo_contenido.get_object_for_this_type(pk=id_objeto)` capturando `ObjectDoesNotExist` →
    `serializers.ValidationError` con mensaje en español, p. ej. «El objeto destino indicado no existe.»).
  - No exponer `version`, `estado`, `version_anterior`, `cargado_por` como editables (los fija el service).
- **T3.3** Importar `Document`, `DocumentType` y `ContentType` según se necesite.

**Reglas:** existencia del objeto destino = **validación de serializer** (T3.2). El versionado y el
estado = **service** (T2). FKs por `id`; representación legible solo en lectura.

**Criterio de aceptación:** `DocumentSerializer` serializa todos los campos del schema §10;
`DocumentWriteSerializer` rechaza con 400 un `(tipo_contenido, id_objeto)` inexistente y no permite
fijar `version`/`estado` manualmente.

---

### T4 — `DocumentViewSet` (`apps/convenios/views.py` — EDITAR)

- **T4.1** `DocumentViewSet(AuditedModelViewSet)` con acciones `list`, `retrieve`, `create`, `destroy`
  (sin `update`/`partial_update`: las nuevas versiones se generan creando otro documento vía service).
  - `queryset = m.Document.objects.select_related("tipo_documento", "tipo_contenido", "version_anterior", "cargado_por")`.
  - `get_serializer_class`: `DocumentSerializer` en `list`/`retrieve`; `DocumentWriteSerializer` en `create`.
  - `permission_classes = [IsAuthenticated, IsInstitutionalMember]`.
  - `filterset_fields = ["tipo_contenido", "id_objeto", "tipo_documento", "estado"]`.
  - `ordering = ["-id"]`.
- **T4.2** `create`: validar con `DocumentWriteSerializer`, resolver el `objeto` destino desde
  `tipo_contenido` + `id_objeto`, delegar en
  `adjuntar_documento(objeto, tipo_documento=..., nombre_archivo=..., referencia_externa=...,
  usuario=request.user)` y responder `201` con `DocumentSerializer`. **No** llamar a
  `perform_create` heredado (la auditoría la realiza el service); sobrescribir `create` directamente
  para evitar doble auditoría.
- **T4.3** `destroy`: hereda de `AuditedModelViewSet` (registra `ELIMINAR`). Antes de borrar, invocar
  `storage.eliminar(instance.referencia_externa)` (stub no-op) para dejar el punto de integración listo.
- **T4.4** `@action(detail=True, methods=["get"], url_path="url-descarga")` →
  devuelve `Response({"url": storage.url_firmada(documento.referencia_externa)})`. Permisos heredados
  del ViewSet.
- **T4.5** Importar `storage_por_defecto` (T1) y `adjuntar_documento` (T2); importar
  `DocumentSerializer`/`DocumentWriteSerializer`.

**Reglas:** ViewSet delgado; escritura vía service `adjuntar_documento`; ninguna lógica de versionado
en la vista. Resolver el objeto destino con la relación genérica.

**Criterio de aceptación:** `POST /api/v1/documents/` crea un documento versionado vía service;
`GET /api/v1/documents/{id}/url-descarga/` devuelve `{"url": <referencia>}`; los filtros
`tipo_contenido`, `id_objeto`, `tipo_documento`, `estado` operan en el listado; `DELETE` registra
auditoría `ELIMINAR`.

---

### T5 — Registro de ruta `documents` (`apps/convenios/urls.py` — EDITAR)

- **T5.1** En el bloque «Núcleo» del router, registrar:
  `router.register("documents", views.DocumentViewSet, basename="document")`.

**Criterio de aceptación:** el endpoint aparece bajo `/api/v1/documents/` y en el esquema OpenAPI
(`/api/schema/`).

---

## Feature B — Bitácora de consulta

### T6 — `AuditLogSerializer` (`apps/convenios/serializers.py` — EDITAR)

- **T6.1** `AuditLogSerializer` **solo lectura** sobre `AuditLog`, exponiendo:
  - `id`,
  - `usuario` (id) y `usuario_nombre` (read-only, `source="usuario.get_username"` o
    `username`/nombre completo; manejar `usuario = None` devolviendo cadena vacía),
  - `accion`,
  - `tipo_contenido` (id) y `tipo_contenido_label` (read-only, label legible vía
    `source="tipo_contenido.model"` o `__str__` del `ContentType`),
  - `id_objeto`,
  - `nombre_campo`, `valor_anterior`, `valor_nuevo`, `direccion_ip`, `creado_en`.
- **T6.2** Todos los campos `read_only` (la escritura ocurre solo vía `registrar_auditoria`).
- **T6.3** Importar `AuditLog`.

**Criterio de aceptación:** el serializer expone los campos del schema §11 más el nombre de usuario y
el label de la entidad afectada; ningún campo es escribible por API.

---

### T7 — `AuditLogFilter` (`apps/convenios/filters.py` — EDITAR)

- **T7.1** `AuditLogFilter(filters.FilterSet)` con:
  - `usuario` (`exact`), `accion` (`exact`; opcional `icontains` adicional `accion_contiene`),
    `tipo_contenido` (`exact`), `id_objeto` (`exact`).
  - Rango de fechas sobre `creado_en`:
    `creado_en_desde = DateTimeFilter(field_name="creado_en", lookup_expr="gte")` y
    `creado_en_hasta = DateTimeFilter(field_name="creado_en", lookup_expr="lte")`.
  - `class Meta`: `model = AuditLog`, `fields` mapeando `usuario`, `accion`, `tipo_contenido`,
    `id_objeto` (estilo dict como `ConventionFilter`).
- **T7.2** Importar `AuditLog`.

**Criterio de aceptación:** el listado de bitácora filtra por usuario, acción, entidad
(`tipo_contenido`), objeto (`id_objeto`) y rango `creado_en_desde`/`creado_en_hasta` (RNF-REN-02).

---

### T8 — `AuditLogViewSet` (`apps/convenios/views.py` — EDITAR)

- **T8.1** `AuditLogViewSet(viewsets.ReadOnlyModelViewSet)`:
  - `queryset = m.AuditLog.objects.select_related("usuario", "tipo_contenido").all()`.
  - `serializer_class = AuditLogSerializer`.
  - `permission_classes = [IsAuthenticated, IsAdminRole]` (Administrador RENADS / Auditor; superusuario
    pasa por la lógica de `IsAdminRole`).
  - `filterset_class = AuditLogFilter`.
  - `search_fields = ["accion"]`.
  - `ordering_fields = ["creado_en", "id"]` y `ordering = ["-creado_en"]`.
- **T8.2** Importar `AuditLogSerializer` y `AuditLogFilter`.

**Reglas:** solo lectura; acceso restringido por rol; no expone escritura.

**Criterio de aceptación:** `GET /api/v1/audit-logs/` lista la bitácora ordenada por `creado_en` desc;
un usuario sin rol Administrador recibe `403`; los filtros de T7 y la búsqueda por `accion` funcionan.

---

### T9 — Registro de ruta `audit-logs` (`apps/convenios/urls.py` — EDITAR)

- **T9.1** En el bloque «Núcleo» del router, registrar:
  `router.register("audit-logs", views.AuditLogViewSet, basename="audit-log")`.

**Criterio de aceptación:** el endpoint aparece bajo `/api/v1/audit-logs/` y en el esquema OpenAPI.

---

## Verificación (cierre)

1. `python manage.py check` sin errores (recordar activar `.venv\Scripts\Activate.ps1`).
2. `python manage.py makemigrations` **no** debe generar migraciones nuevas (los modelos `Document` y
   `AuditLog` ya están migrados; este spec no altera el schema).
3. `python manage.py spectacular --file schema.yml` (o `/api/schema/`) genera sin error e incluye los
   paths `documents` y `audit-logs`.
4. Ejecutar `/code-review` antes de cerrar (sin tests automatizados, regla MVP).
5. **Guía de pruebas manuales** (criterio de aceptación funcional, registrar en
   `spec/convenios_transversales.guia_pruebas.md`):
   - `POST /api/v1/documents/` con un `(tipo_contenido, id_objeto)` válido → `201`, `version=1`,
     `estado=ACTIVO`.
   - Repetir con el mismo `(objeto, tipo_documento)` → nuevo doc `version=2` `ACTIVO`,
     `version_anterior` apuntando al anterior, y el anterior en `REEMPLAZADO`.
   - `POST` con `id_objeto` inexistente → `400` con mensaje en español.
   - `GET /api/v1/documents/{id}/url-descarga/` → `{"url": <referencia_externa>}`.
   - `GET /api/v1/documents/?tipo_contenido=&id_objeto=&estado=` filtra correctamente.
   - `GET /api/v1/audit-logs/` como Administrador RENADS → `200` ordenado por `creado_en` desc;
     como usuario sin rol → `403`.
   - Verificar en `bitacora_auditoria` los registros `CREAR` (documento) y `CAMBIO_ESTADO`
     (reemplazo del anterior).

## Endpoints resultantes

| Método(s) | Endpoint | ViewSet | Permisos |
|-----------|----------|---------|----------|
| GET / POST / DELETE | `/api/v1/documents/` | `DocumentViewSet` | `IsAuthenticated`, `IsInstitutionalMember` |
| GET / DELETE | `/api/v1/documents/{id}/` | `DocumentViewSet` | idem |
| GET | `/api/v1/documents/{id}/url-descarga/` | `DocumentViewSet` (action) | idem |
| GET | `/api/v1/audit-logs/` | `AuditLogViewSet` | `IsAuthenticated`, `IsAdminRole` |
| GET | `/api/v1/audit-logs/{id}/` | `AuditLogViewSet` | idem |

## Referencias

- **Schema:** `docs/db_schema_modulo_01_convenios.md` §10 (`documento`) y §11 (`bitacora_auditoria`).
  Modelos: `apps/convenios/models.py` líneas 788 (`Document`) y 819 (`AuditLog`). No inventar campos.
- **Arquitectura:** `docs/arquitectura_desarrollo.md` §9 (storage `DocumentStorage` Protocol + service
  `adjuntar_documento`) y §10 (auditoría explícita desde services, `transaction.atomic()`).
- **RNF:** RNF-DOC-01/02/03/04 (gestión documental + versionado) → Feature A;
  RNF-AUD-01/02 (bitácora) y RNF-REN-02 (filtros eficientes) → Feature B.
- **Reutilización existente:** `registrar_auditoria` (`apps/common/services.py:8`),
  `documentos_de` (`apps/convenios/selectors.py:61`), `IsInstitutionalMember`
  (`apps/common/permissions.py`), `IsAdminRole` (`apps/convenios/permissions.py`),
  patrón `AuditedModelViewSet` y read/write serializers (`Convention*`).

## Fuera de alcance (este spec)

Tests automatizados; backend real de almacenamiento (S3/MinIO/boto3); migraciones nuevas; cambios al
núcleo del convenio o a los CRUD ya validados; despliegue en Railway (solo se prepara configuración).
