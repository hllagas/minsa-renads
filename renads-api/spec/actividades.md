# Spec — Módulo `actividades` (Registrar Actividades Docente-Asistenciales)

Tareas exactas para `apps/actividades/` según [arquitectura](../docs/arquitectura_desarrollo.md) y [schema M3](../docs/db_schema_modulo_03_actividades.md). Producido por el agente **spec** (SDD). Reutiliza el patrón ya consolidado (services/selectors, ViewSets delgados, JWT + alcance institucional, `AuditedModelViewSet`, `_catalog_viewset`).

## Resumen

Exponer vía DRF (bajo `/api/v1/`) el registro y validación de actividades docente-asistenciales de los internos. Módulo pequeño: 2 catálogos + `TeachingActivity` con validación e historial. Reutiliza módulos 1 y 2 (`Intern`, `Internship`, `Rotation`, `Tutor`, `Ipress`, `ServiceArea`).

**Convenciones:** clases inglés; campos/tablas/`help_text` español; endpoints inglés; docstrings español. Sin tests (fuera de alcance MVP).

**Entidades** (modelos en `apps/actividades/models.py`):
- Catálogos: `ActivityType`, `ActivityStatus`.
- Núcleo: `TeachingActivity`, `ActivityValidation`, `ActivityStatusHistory`.

Bloque único (módulo pequeño): núcleo + services + catálogos juntos.

---

## T1 — Serializers (`apps/actividades/serializers.py`)
- `TeachingActivityReadSerializer` (interno, internado, ipress, tutor, estado legibles) / `TeachingActivityWriteSerializer` (FKs; `estado_actual`, `creado_por` solo lectura).
- `ActivityValidationSerializer` (entrada de la acción `validar`: `resultado`, `comentario`).
- `SubsanarSerializer` (opcional: `descripcion`, `carga_horaria` para reenviar al subsanar).
- `ActivityStatusHistorySerializer`.
- Catálogos: serializers read-only (vía factory).

## T2 — Selectors (`apps/actividades/selectors.py`)
- `actividades_visibles(usuario)`: alcance por universidad del interno o sede (`ipress`), como en `internados`. Superusuario ve todo.
- `historial_actividad(actividad)`.

## T3 — Services (`apps/actividades/services.py`)
Escritura en `transaction.atomic()`, con auditoría e historial de estado.
- **`registrar_actividad(datos, usuario)`:**
  - **RN-1:** el `internado` debe estar en estado `ACTIVO`.
  - **RN-2:** `fecha_actividad` dentro de `[internado.fecha_inicio, internado.fecha_fin]`.
  - **RN-3/4:** si se envía `rotacion`, debe pertenecer al internado y estar `AUTORIZADA` o `EN_CURSO` (no `RECHAZADA`/`CANCELADA`/sin autorizar).
  - **RN-9:** rechazar duplicado por (`interno`, `fecha_actividad`, `ipress`, `servicio_area`).
  - Estado inicial `REGISTRADA`.
- **`validar_actividad(actividad, datos, usuario)`** (rol `Tutor`): crea `ActivityValidation`; estado → `VALIDADA`/`OBSERVADA`/`RECHAZADA` según `resultado`.
- **`subsanar_actividad(actividad, datos, usuario)`** (**RN-7**): solo si estado `OBSERVADA`; actualiza campos permitidos y estado → `SUBSANADA`.
- **`actualizar_actividad`/edición (RN-8):** no permitir modificar una actividad `VALIDADA` salvo rol con permiso especial; todo cambio queda en historial + auditoría.
- **`cambiar_estado_actividad`** (rol `Administrador RENADS`) para transiciones administrativas (`CERRADA`).

## T4 — ViewSets (`apps/actividades/views.py`)
- `TeachingActivityViewSet` (`ModelViewSet`): `get_queryset = selectors.actividades_visibles`; create/update vía services; acciones `validar`, `subsanar`, `cambiar-estado`, `historial`.
- Catálogos `activity-types`, `activity-statuses`: `ReadOnlyModelViewSet` (factory `_catalog_viewset`).

## T5 — Permissions (`apps/actividades/permissions.py`)
- Global `IsAuthenticated` + `IsInstitutionalMember`.
- `ActivityScope` (objeto): universidad del interno o sede (`ipress`) en el ámbito del usuario.
- Roles: registrar → `Universidad`/`Tutor`/`Sede docente`; `validar` → `Tutor`; `cambiar-estado` → `Administrador RENADS`.

## T6 — Filters (`apps/actividades/filters.py`)
- `TeachingActivityFilter`: por `interno`, `internado`, `ipress`, `tutor`, `rotacion`, `tipo_actividad`, `estado_actual`, rango de `fecha_actividad`.

## T7 — URLs / router
- `DefaultRouter`: `teaching-activities`, `activity-types`, `activity-statuses`. Incluir en `config/api_urls.py`. Verificar OpenAPI.

---

## Referencias
- **RN (§5 módulo 3):** RN-1 (internado activo), RN-2 (periodo), RN-3/4 (rotación autorizada), RN-5/6 (sede/tutor, modelo), RN-7 (subsanación), RN-8 (validadas no se modifican sin trazabilidad), RN-9 (duplicidad), RN-10 (evidencia PDF → fuera de alcance: storage externo).
- **RF:** RF-DA-01..20.
- **Schema:** `docs/db_schema_modulo_03_actividades.md`. No inventar campos.
- **Reutilización:** `apps/common` (permisos, auditoría), `AuditedModelViewSet`/`_catalog_viewset` de `apps/convenios`, modelos de `apps/internados`.

## Fuera de alcance
Testing automatizado; evidencia documental (`Document`/storage externo); reportes/exportación/consolidados.
