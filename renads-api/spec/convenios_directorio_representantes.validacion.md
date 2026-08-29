# Validación — Reorganización de directorio de órganos, representantes y gestión documental

> **Spec validado:** `spec/convenios_directorio_representantes.md` (T1–T32).
> **Fecha:** 2026-08-28. **Resultado global:** APROBADO (sin errores altos/medios).
> Un (1) hallazgo bajo de documentación (no bloqueante). Se genera guía de pruebas.

## Resumen ejecutivo

| Verificación | Resultado |
|---|---|
| `makemigrations --check --dry-run` | OK — «No changes detected» |
| `manage.py check` | OK — 0 issues |
| `spectacular` (OpenAPI) | OK — **0 errores** (85 warnings preexistentes, ajenos a este cambio) |
| Router: `organ-directories`/`executive-positions` en `ENTITY_VIEWSETS`, no en `CATALOG_VIEWSETS` | OK (True/True; `executive-positions` no en CATALOG) |
| Router: `regional-organs`/`minsa-organs`/`university-authorities`/`document-types` retirados | OK (no resuelven ruta) |
| Router: `organ-representatives`/`organ-representative-history` registrados | OK |
| Grep de referencias huérfanas en `apps/` | OK — sin usos rotos fuera de migraciones históricas |
| RN histórico (`registrar_organo_representante`) probada end-to-end | OK |

## Resultado por bloque / tarea

### Bloque A — Modelos `apps/convenios/models.py`

- **T1 `ExecutivePosition`** — OK. No hereda `Catalog`; FK `organo` (PROTECT, `db_column="organo_id"`, `related_name="cargos"`); `codigo` sin `unique` global; `unique_together (organo, codigo)`; `ordering=["organo","codigo"]`; `db_table="cargo_ejecutivo"`; `__str__` → `nombre`.
- **T2 `OrganDirectory`** — OK. Tabla `organo_directorio`; todos los campos exactos (`organo`, `tipo_organo` nullable, `gobierno_regional` nullable, `nombre`, `siglas`, `direccion`, `numero_ruc`, `correo`, `telefono_institucional`, `ubigeo`, `referencia_logo`, `activo`); `db_column`/`related_name`/`help_text` conformes. Standalone (sin FK inverso desde University/Ipress/Conapres). Ubicado tras `RegionalGovernment`.
- **T3 `ExecutingUnit.organo_directorio`** — OK. FK → `OrganDirectory`, `db_column="organo_directorio_id"`, `related_name="unidades_ejecutoras"`. Sin `organo_regional`.
- **T4 `Convention.organo_directorio`** — OK. FK → `OrganDirectory`, `related_name="convenios"`, obligatorio.
- **T5 `TechnicalEvaluation.organo_directorio`** — OK. FK → `OrganDirectory`, `SET_NULL`, `null/blank=True`, `related_name="+"`.
- **T6 Eliminar `RegionalOrgan`/`MinsaOrgan`** — OK. No existen en el modelo; `DeleteModel` en migración 0019.
- **T7 `OrganRepresentative`** — OK. Tabla `organo_representante`; FK directo a `OrganDirectory` (sin GenericForeignKey); `tipo_documento_identidad` → `"internados.IdentityDocumentType"` por string; `SEX=[("M","Masculino"),("F","Femenino")]` definido localmente; todos los campos y `Meta` (`ordering=["id"]`) conformes.
- **T8 `OrganRepresentativeHistory`** — OK. Tabla `historial_organo_representante`; snapshot denormalizado completo + `fecha_baja`, `motivo`, `creado_en`; `Meta.ordering=["-fecha_baja","-id"]`.
- **T9 Eliminar `Representative`/`UniversityAuthority`** — OK. No existen; `REPRESENTATIVE_ORIGIN` y `ENTIDADES_REPRESENTABLES` sin rastro en código activo.
- **T10 `Document`** — OK. Sin `nombre_archivo`/`texto_extraido`/`tipo_documento`; `documento_anexo` NOT NULL `PROTECT` (`related_name="documentos"`); `db_table="documento_adjunto"`; `verbose_name="documento adjunto"`.
- **T11 Eliminar `DocumentType`** — OK. Clase eliminada; `DeleteModel` en 0019.

### Bloque B — Modelos `apps/internados/models.py`

- **T12 `AnnexDocument`** — OK. Sin `descripcion`; `tipo_actor` con `blank=True` (choices/default intactos); `db_table="documento_anexo"`.

### Bloque C — Services

- **T13 `registrar_organo_representante`** — OK. `@transaction.atomic`; da de baja al anterior activo del par `(organo_directorio, cargo_ejecutivo)`, copia snapshot a histórico con `fecha_baja=hoy` y motivo por defecto «Reemplazo de representante»; doble auditoría (`CAMBIO_ESTADO` sobre el anterior + `CREAR` del histórico) + `CREAR` del nuevo. **Probado end-to-end**: A activo → crear B ⇒ A `activo=False`, B `activo=True`, fila en `historial_organo_representante` con snapshot y `fecha_baja`.
- **T15 `adjuntar_documento`** — OK. Firma `(objeto, *, referencia_externa, usuario, documento_anexo)`; `documento_anexo` obligatorio keyword-only, único discriminador del versionado; sin `tipo_documento`/`nombre_archivo`/`texto_extraido`; docstring actualizado.
- **T16 `internados/services.py`** — OK. `_declaraciones_completas`/`recalcular_estado_declaraciones` compilan y filtran por `documento_anexo`/`tipo_actor="INTERNO"`; import de `Document` intacto (tabla renombrada, misma clase).

### Bloque D — Serializers

- **T17 `OrganRepresentativeSerializer`** — OK. `fields="__all__"`; `validate` rechaza documento duplicado activo (excluye `self.instance`) y valida coherencia `cargo.organo_id == organo_directorio.organo_id` con mensaje en español.
- **T18 Eliminar `RepresentativeSerializer`/`ENTIDADES_REPRESENTABLES`** — OK. Sin import de `Representative`.
- **T19 Serializers de documento** — OK. `DocumentSerializer` sin `tipo_documento*`/`nombre_archivo`/`texto_extraido`, con `documento_anexo` + `documento_anexo_nombre`; `DocumentWriteSerializer` con `documento_anexo` y `validate` de objeto destino; `DocumentUploadSerializer` sin `tipo_documento`, con `documento_anexo` (`ActiveAnnexDocumentField`), conserva `nombre_archivo` como ruta de storage (decisión explícita del spec).
- **T20 `AnnexUploadSerializer`** — OK. Solo `documento_anexo` + `archivo`; sin `nombre_archivo`.

### Bloque D (mixins) — T21

- **T21 `AnnexAttachmentMixin.annex_upload`** — OK. Sin `_tipo_documento_anexo`, sin import de `DocumentType` ni `extraer_texto_pdf`; deriva ruta de `archivo.name`; llama `adjuntar_documento(..., documento_anexo=anexo)`; conserva enforcement `anexo.tipo_actor != self.annex_actor`. `annex_checklist` intacto.

### Bloque E — Views

- **T22 `OrganRepresentativeViewSet`** — OK. `(AnnexAttachmentMixin, AuditedModelViewSet)`; `annex_actor="REPRESENTANTE"`; `select_related`; `permission_classes=[IsAuthenticated, IsAdminRoleOrReadOnly]`; filtros/búsqueda conformes; `perform_create` delega en el service (sin doble auditoría).
- **T23 `OrganRepresentativeHistoryViewSet`** — OK. `ReadOnlyModelViewSet`; `_auto_serializer`; filtros `organo_directorio`/`cargo_ejecutivo`/`representante`; `ordering=["-fecha_baja","-id"]`.
- **T24 Eliminar `RepresentativeViewSet`** — OK. No existe; sin import de `RepresentativeSerializer`.
- **T25 `CATALOG_VIEWSETS`/`ENTITY_VIEWSETS`** — OK. `executive-positions` movido a `ENTITY_VIEWSETS` (filtro `organo`/`activo`); `document-types`/`regional-organs`/`minsa-organs`/`university-authorities` eliminados; `organ-directories` añadido (logo, filtros `organo`/`tipo_organo`/`gobierno_regional`/`activo`); `executing-units` filtra por `organo_directorio`.
- **T26 `DocumentViewSet`** — OK. `select_related` sin `tipo_documento`; `filterset_fields=["tipo_contenido","id_objeto","documento_anexo","estado"]`; `create`/`upload` pasan `documento_anexo`; sin `extraer_texto_pdf`.
- **T27 `SOLICITANTE_MODELS`** — OK. Sin `RegionalOrgan`/`MinsaOrgan`; incluye `OrganDirectory` (entrada única).
- **T28 Barrido de referencias** — OK. `filters.py` (`ConventionFilter.organo_directorio`), `serializers.py`, `services.py`, `permissions.py`, `selectors.py` sin referencias rotas. `check` limpio.

### Bloque F — URLs

- **T29 Router** — OK. Sin `representatives`; `organ-representatives` y `organ-representative-history` registrados; `organ-directories`/`executive-positions` registrados vía `ENTITY_VIEWSETS`. Endpoints viejos no resuelven ruta.

### Bloque G — Migraciones

- **T30 `convenios/0019_reorg_directorio_representantes_documentos.py`** — OK. Depende de `convenios.0018` + `internados.0018` + `AUTH_USER_MODEL`. Orden de operaciones conforme (cargo_ejecutivo → OrganDirectory → repunte FKs → delete RegionalOrgan/MinsaOrgan → create OrganRepresentative/History → delete Representative/UniversityAuthority → Document → delete DocumentType → reseed). Reseed de cargos por órgano (Universidad/Órgano Regional/Órgano del MINSA) y anexos genéricos (ANEXO/CONVENIO/RESOLUCION con `tipo_actor=""`) vía `apps.get_model`.
- **T31 `internados/0018_annexdocument_documento_anexo.py`** — OK. `RemoveField descripcion`, `AlterField tipo_actor` (blank), `AlterModelTable → documento_anexo`. `convenios.0019` declara la dependencia cruzada correctamente.

### Bloque H — Documentación

- **T32** — OK con 1 hallazgo bajo:
  - `docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_modulo_02_internados.md`, `docs/db_schema_er_global.md`, `docs/api_almacenamiento_frontend.md` y `CLAUDE.md` reflejan las tablas nuevas y listan las eliminadas como retiradas.
  - **[BAJO] `docs/db_schema_modulo_01_convenios.md` líneas 588–589** — el «Mapa de relaciones» (ASCII) todavía dibuja `organo_regional` como tabla activa: `ubigeo … >──< organo_regional / …` y `gobierno_regional ──< organo_regional ──< unidad_ejecutora`. Corrección sugerida: reemplazar `organo_regional` por `organo_directorio` en esas dos líneas (el resto del mapa ya usa `organo_directorio`). No bloqueante (schema, modelos y endpoints son correctos).

## Notas

- Las coincidencias de `organo_regional`/`organo_minsa`/`DocumentType`/`tipo_documento`/`nombre_archivo`/`texto_extraido` restantes en `apps/` viven **solo en migraciones históricas** (0001, 0006, 0011, 0012, 0013, 0016) — intactas a propósito, no se ejecutan sobre el estado final. `extraer_texto_pdf` sigue **definido** en `apps/common/documentai.py` pero **ya no se importa** en mixins/views (verificado); su permanencia es inocua.
- `nombre_archivo` en `DocumentUploadSerializer` es intencional (ruta de storage, decisión documentada en T19), distinto del campo `nombre_archivo` eliminado del modelo `Document`.
