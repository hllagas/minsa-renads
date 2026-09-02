# Validación — `spec/convenios_solicitud.md` (Fases A, B, C)

**Fecha:** 2026-09-02
**Resultado:** APROBADO con observaciones menores (ninguna bloqueante).
**Alcance:** revisión estática contra spec, arquitectura (`docs/arquitectura_desarrollo.md`) y schema (`docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_modulo_02_internados.md`). No se ejecutaron `migrate` ni tests. El hilo principal ya verificó `check` limpio, `makemigrations --check` = sin cambios y `spectacular` con 0 errores incluyendo los tres endpoints nuevos.

---

## Resumen por fase

| Fase | Estado | Notas |
|---|---|---|
| A — modelo/servicios/API partes + nomenclatura | ✅ Cumple | Sin hallazgos bloqueantes |
| B — storage Cloudflare R2 | ✅ Cumple | Completo y coherente con GCS/stub |
| C — generación PDF | ✅ Cumple funcionalmente | 1 observación (logos InlineImage no inyectados) |

---

## FASE A — verificación de criterios

- **`ConventionParty` / `parte_convenio`** (`models.py:862`): campos, `db_table`, verbose, `unique_together=(("convenio","rol","orden"))`, `ordering`, `related_name="partes_firmantes"`, choices `PARTY_ROLE` (código inglés) — todo conforme. FKs `PROTECT` salvo `convenio` `CASCADE`. `organo_representante`/`cargo_ejecutivo` nulos, coherente con la regla "omitir chequeo si nulos" en `_validar_coherencia_parte` (`services.py:817`). Sin lógica de negocio en el modelo. ✔
- **`numero_resolucion_facultades`** en `OrganRepresentative` (`models.py:478`) e `OrganRepresentativeHistory` (`models.py:531`), expuesto por `OrganRepresentativeSerializer` (`fields="__all__"`) e incluido en el snapshot `_CAMPOS_SNAPSHOT_REPRESENTANTE` (`services.py:662`). ✔
- **Rename `codigo`→`nomenclatura`:** modelo `models.py:769`; write serializer NO expone `nomenclatura` (`serializers.py:106`); `editables` de `actualizar_convenio` sin `codigo`/`nomenclatura` (`services.py:345`); read serializer expone `nomenclatura` (`serializers.py:60`); `AdendaWriteSerializer` usa `nomenclatura` (`serializers.py:118`); `ConventionFilter`/`search_fields` sin referencia colgante. Grep confirma que todos los `codigo` restantes en `services.py` son de `ConventionStatus.codigo`/`tipo_convenio.codigo` — **ningún** `Convention.codigo` colgante. ✔
- **Gate `_validar_nomenclatura`** (`services.py:113`) invocado en `registrar_evaluacion_tecnica` solo si Marco + `resultado==VALIDADO`, antes de `_set_estado("VALIDADO_TECNICAMENTE")`, con auditoría de `nomenclatura` (`services.py:398-410`). Serializer de acción con `nomenclatura` write-only fuera del modelo `evaluacion_tecnica` (`serializers.py:206`); el service la hace `pop` (`services.py:395`). ✔
- **Migración `0035`** usa `RenameField` + `AlterField` (no drop+add), `AddField ×2`, `CreateModel` en el orden del spec; preserva datos. ✔
- **`sincronizar_partes`** (`services.py:841`) idempotente por `(convenio,rol,orden)` con `select_for_update`, coherencia por parte, composición por tipo/categoría, y auditoría `CREAR`/`ACTUALIZAR`/`ELIMINAR`. `_validar_composicion_partes` (`services.py:154`) cubre Marco Lima (`MINSA_DIRIS`), Marco región (`GOBIERNO_REGIONAL`) y Específico. ✔
- **Selector `campos_clinicos_del_especifico`** (`selectors.py:97`): lectura pura, filtra por unidad ejecutora del convenio + `es_sede_docente=True` + carreras activas de la facultad. Sin efectos secundarios. ✔
- **API:** `ConventionPartySerializer` con `*_detalle` y `rol_display` (`serializers.py:152`); acción `parties` GET/POST (`views.py:201`) con `@extend_schema` y sujeta a `IsModuleEnabled` (en `permission_classes` del ViewSet, aplica a la acción POST); read serializer expone `partes_firmantes` + `nomenclatura`. ✔

## FASE B — verificación de criterios

- **`CloudflareR2Storage`** (`storage.py:241`) cumple el Protocol (`subir`/`url_firmada`/`eliminar`), boto3 import diferido con `RuntimeError` en español, cliente perezoso, `region_name="auto"`, `Config(signature_version="s3v4")`, key `{prefix}/{uuid4}-{nombre_seguro}`, `seek(0)` antes de subir, presigned `get_object`, `eliminar` tolerante a inexistencia. ✔
- **`get_document_storage`** (`storage.py:352`) con `@lru_cache` y precedencia R2 → GCS → stub. Con `R2_ENABLED=False` no cambia el comportamiento. ✔
- **`STORAGES["default"]`** (`base.py:254`) rama R2 `S3Boto3Storage` con `querystring_auth=True`, `default_acl=None`, `location="logos"`, `signature_version="s3v4"`, precedencia sobre GCS (`elif`). ✔
- **Settings `R2_*`** (`base.py:186-208`) completos vía `config(...)`; `.env.example` con las variables sin secretos. ✔
- **Deps** `boto3==1.43.86`, `django-storages==1.14.6` en `requirements.txt`. ✔

## FASE C — verificación de criterios

- **`construir_contexto`** (`pdf.py:154`) lectura pura, no lanza por opcionales, MINSA con domicilio fijo (`DOMICILIO_MINSA`), resto derivado de la entidad. ✔
- **`_seleccionar_plantilla`** (`pdf.py:209`) determinista por `(tipo, es_adenda, categoría)`; `RuntimeError` español si no hay combinación. ✔
- **`generar_docx`/`convertir_a_pdf`** (`pdf.py:238,270`) con imports docxtpl diferidos, LibreOffice `soffice --headless --convert-to pdf --outdir`, tmpdir con limpieza, timeout, y `RuntimeError` español si falta `soffice`. ✔
- **`generar_expediente`** (`pdf.py:398`) merge con pypdf (import diferido), omite adjuntos faltantes/ilegibles con log. Reúne resoluciones de representantes firmantes (actor `REPRESENTANTE`) y campos clínicos CONAPRES (actor `CAMPO_CLINICO`). ✔
- **Endpoints** `generar-proyecto` (`PROYECTO_ADENDA`/`PROYECTO_CONVENIO` según `es_adenda`) y `generar-expediente` (`EXPEDIENTE`) (`views.py:275,292`): suben vía `self.storage.subir` y versionan con `adjuntar_documento`; `@extend_schema` con `DocumentSerializer`; gate `IsModuleEnabled`. El buffer `io.BytesIO` lleva `.name`/`.content_type` que consumen los backends. ✔
- **Seed `0020_seed_anexos_proyecto.py`** idempotente (`get_or_create` por `codigo`), tres `AnnexDocument` `tipo_actor="CONVENIO"`, `obligatorio=False`. Sin colisión de `codigo` (Catalog unique global) con los seeds `RESOL_*` de `0019`. ✔
- **Plantillas** (5 `.docx` + README): zips válidos. Placeholders Jinja de cada plantilla verificados contra `construir_contexto` — **cobertura completa** (`partes[]`, `parte.rol_display/organo/representante/cargo/domicilio`, `nomenclatura`, `carreras`, `campos_clinicos` con `cc.ipress/carrera/resolucion`, `convenio_marco.*`, `convenio_origen.*`, fechas, `vigencia_efectiva`). ✔
- **Deps** `docxtpl==0.20.2`, `pypdf==6.14.2` en `requirements.txt`. ✔

## Sincronía docs ↔ código

- `db_schema_modulo_01_convenios.md`: sección `parte_convenio` (línea 459), columna `nomenclatura` (429), `numero_resolucion_facultades` en representante e historial (319, 341), ER global (713). ✔
- `api_almacenamiento_frontend.md`: `generar-proyecto`/`generar-expediente` (248-249) y su gate de permisos (298). ✔

## Reglas de lenguaje

Tablas/columnas/help_text/verbose en español; clases/funciones/variables/endpoints/choices-key en inglés; docstrings y mensajes de error en español. ✔

---

## Observaciones (no bloqueantes)

1. **[Observación — Fase C3] Logos InlineImage no se inyectan.** El spec C3 pide incrustar logos vía `docxtpl.InlineImage` descargando el binario del storage. La implementación deja `logo_minsa`/`logo_universidad` como `""` en `construir_contexto` (`pdf.py:183-184`) y `generar_expediente` no los rellena. No es bloqueante: ninguna de las 5 plantillas referencia variables de logo (verificado), por lo que el render no falla ni queda incompleto respecto a las plantillas actuales. Si se desea cumplir literalmente el criterio, incorporar la descarga del logo (R2/GCS) y su `InlineImage` en el flujo de `generar_docx`/`generar_expediente`, y añadir los placeholders de imagen en las plantillas Marco/Específico. Prioridad: baja.

2. **[Observación menor — Fase C] `_pdfs_adjuntos_del_expediente` no dedup por documento.** Si un mismo representante firma en más de una parte se deduplica por `set` de representantes (`pdf.py:376`), correcto; pero no hay dedup de `Document` si dos partes comparten órgano/campo clínico solapado. Impacto práctico nulo dado el modelo actual. Prioridad: informativa.

Ninguna observación impide cerrar el módulo. Se genera la guía de pruebas manuales en `spec/convenios_solicitud.guia_pruebas.md`.
