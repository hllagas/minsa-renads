# Módulo 1 — CRUD de soporte transversales (Documento + Bitácora de auditoría)

> Documento de solicitud y alcance. Metodología: **SDD (Spec Driven Development)**.
> Fuentes de verdad: `docs/alcance_mvp.md`, `docs/arquitectura_desarrollo.md`,
> `docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_er_global.md`.

## 1. Solicitud original

> «Ahora que ya tenemos definido el schema de base de datos y arquitectura del proyecto, vamos a
> crear los CRUD del módulo 1 correspondientes a catálogos, entidades (Gobiernos Regionales, MINSA,
> CONAPRES y Universidades), seguridad, perfil institucional, documento y auditoría transversal.
> No incluyen los del núcleo del convenio porque ya están desarrollados. Crea un documento MD con lo
> que te estoy pidiendo, trabajaremos con la metodología SDD y luego publicaremos en Railway.»

## 2. Hallazgo del análisis previo

Al revisar el código (`apps/convenios/views.py`, `apps/convenios/urls.py`) contra
`spec/convenios.validacion.md`, se confirma que la mayor parte del soporte del Módulo 1 **ya está
implementada y validada**. Solo restan dos brechas reales.

### 2.1. Inventario «ya existe vs. falta»

| Bloque | Tablas / endpoints | Estado |
|--------|--------------------|--------|
| **Catálogos** (solo lectura) | 18 catálogos (`region`, `tipo_convenio`, `estado_convenio`, …) + `ubigeo` | ✅ Implementado (`CATALOG_VIEWSETS`, `UbigeoViewSet`) |
| **Entidades — Gobiernos Regionales** | `gobierno_regional`, `organo_regional`, `unidad_ejecutora`, `ipress` | ✅ Implementado (`ENTITY_VIEWSETS`) |
| **Entidades — MINSA** | `organo_minsa` | ✅ Implementado (`minsa-organs`) |
| **Entidades — CONAPRES** | `conapres` | ✅ Implementado (`conapres`) |
| **Entidades — Universidades** | `universidad`, `autoridad_universidad`, `facultad`, `carrera_profesional`, `local_universidad` | ✅ Implementado |
| **Representantes** | `representante` (polimórfico) | ✅ Implementado (`RepresentativeViewSet`) |
| **Seguridad / perfil institucional** | `perfil_usuario_entidad` | ✅ Implementado (`user-entity-profiles`, `IsAdminRole`) |
| **Auditoría — escritura** | `bitacora_auditoria` (registro automático) | ✅ Implementado (`AuditedModelViewSet` + `registrar_auditoria`) |
| **Documento** | `documento` (gestión documental polimórfica) | ❌ **Falta** — modelo existe, sin serializer/service/storage/endpoint |
| **Auditoría — consulta** | `bitacora_auditoria` (lectura/filtros) | ❌ **Falta** — se escribe, pero no hay endpoint de consulta |

### 2.2. Alcance acordado con el usuario

- **Trabajo a realizar:** solo **Documento** + **consulta de Bitácora**. No se rehace lo ya validado.
- **Almacenamiento de documentos:** **referencia externa (stub)** — la BD guarda
  `referencia_externa`, `nombre_archivo`, `version`, `estado`; con abstracción `Protocol` sin backend
  real (S3/MinIO queda fuera del MVP, según `docs/arquitectura_desarrollo.md`).
- **Railway:** preparar configuración de despliegue; el deploy lo ejecuta el usuario después.

## 3. Features a construir

### Feature A — Documento (RNF-DOC-01/02/03)

Gestión documental polimórfica adjunta a cualquier entidad (convenio, actividad, etc.) vía
`tipo_contenido` + `id_objeto`. Incluye **versionado** (`version`, `version_anterior`, `estado`).

- Abstracción de almacenamiento `DocumentStorage` (Protocol) + impl. stub `ReferenciaExternaStorage`.
- Service `adjuntar_documento(...)` transaccional, con versionado y auditoría.
- Serializers lectura/escritura, `DocumentViewSet` (list/retrieve/create/destroy + acción `url-descarga`).
- Endpoint `documents`. Permisos: miembro institucional autenticado.

### Feature B — Bitácora de auditoría — consulta (RNF-AUD-01/02)

Endpoint de **solo lectura** para consultar la bitácora: usuario, acción, entidad afectada, valores,
IP y fecha. Filtros por usuario, acción, entidad, objeto y rango de fechas.

- `AuditLogSerializer` (read-only), `AuditLogViewSet` (`ReadOnlyModelViewSet`).
- Acceso restringido a **Administrador RENADS / Auditor** (`IsAdminRole`).
- Endpoint `audit-logs`. Ordenado por `creado_en` desc.

## 4. Criterio de cierre (SDD)

1. **Spec** — tareas exactas en `spec/convenios_transversales.md`.
2. **Implement** — código en `apps/convenios/` y `apps/common/` según spec, arquitectura y schema.
3. **Validator** — revisa y genera `spec/convenios_transversales.validacion.md`; se itera
   `implement ↔ validator` hasta validación sin errores. Luego `/code-review`.
4. Verificación: `python manage.py check` sin errores y `makemigrations` sin migraciones nuevas
   (modelos ya migrados). Guía de pruebas manuales en `spec/convenios_transversales.guia_pruebas.md`.

El módulo de soporte se considera cerrado solo con validación sin errores.

## 5. Fuera de alcance

Rehacer catálogos/entidades/seguridad (ya validados), backend real de almacenamiento (S3/MinIO),
y la ejecución del despliegue en Railway (solo se prepara la configuración).
