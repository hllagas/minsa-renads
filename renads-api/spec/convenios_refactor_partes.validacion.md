# Validación — Refactor del core `convenio`: FK `organo_regional` y `universidad`

**Módulo:** 1 — Gestionar Convenios
**Alcance:** agregado de dos FK obligatorias (`organo_regional` → `RegionalOrgan`, `universidad` → `University`) con derivación read-only de sus "tipos"; el `solicitante` polimórfico se mantiene.
**Fecha:** 2026-06-30

## Veredicto: APROBADO (sin errores altos ni medios)

El estado del modelo es coherente con las migraciones, el serializer, los services, el filtro, el selector y el schema doc. No se rompe el flujo existente.

---

## Verificaciones técnicas

| Verificación | Resultado |
|---|---|
| `makemigrations --check --dry-run` | `No changes detected` — modelo == migraciones |
| `manage.py check` | `System check identified no issues (0 silenced)` |
| Cadena de migraciones | Lineal 0001→0006; `0006` es la última |

---

## Hallazgos por criterio

### 1. Coherencia modelo ↔ migración ↔ serializer ↔ schema — OK
- `Convention.organo_regional` y `Convention.universidad`: ambas `ForeignKey`, `on_delete=PROTECT`, NOT NULL, `db_column` explícito (`organo_regional_id` / `universidad_id`), `related_name="convenios"`. No hay colisión de `related_name` porque apuntan a modelos destino distintos (`RegionalOrgan.convenios` vs `University.convenios`).
- Migración `0006`: patrón correcto AddField nullable → `RunPython(backfill, noop)` → AlterField NOT NULL para ambas columnas. Coincide con el estado final del modelo (confirmado por `--check`).
- Schema doc §8 `convenio`: filas `organo_regional_id` (FK → `organo_regional`, Null=No) y `universidad_id` (FK → `universidad`, Null=No) presentes, con la nota de derivación de tipos en el encabezado de la tabla. El mapa de relaciones (§12) mantiene `solicitante` polimórfico; las dos FK nuevas no rompen lo documentado.

### 2. Robustez y reversibilidad de la migración — OK
- Base nueva (sin convenios): `pendientes.exists()` es `False` → `backfill` retorna sin tocar nada; el `AlterField` a NOT NULL corre sobre tabla vacía. No rompe.
- Base con datos (5 convenios): valida que exista al menos un `RegionalOrgan` y una `University`; si falta alguno lanza `RuntimeError` con mensaje claro antes de imponer NOT NULL (evita un `IntegrityError` opaco). Rellena con `update(...)` y luego impone NOT NULL.
- Reversibilidad razonable: reverse de `RunPython` es `noop`, reverse de `AlterField` vuelve a nullable, reverse de `AddField` elimina columnas. Coherente.

### 3. Servicios `crear_convenio` / `actualizar_convenio` — OK
- `crear_convenio` persiste con `organo_regional=datos["organo_regional"]` y `universidad=datos["universidad"]` (acceso por clave obligatoria). `ConventionWriteSerializer` incluye ambos campos y, al ser FK NOT NULL del modelo, DRF los marca `required=True` por defecto → no se puede crear sin ellos.
- `actualizar_convenio` incluye `organo_regional` y `universidad` en `editables`; en PATCH se aplican solo si vienen en `datos`, en PUT el serializer los exige. Correcto.

### 4. Labels derivados sin N+1 — OK
- `ConventionReadSerializer` expone `organo_regional` + `organo_regional_nombre` + `tipo_organo_regional` y `universidad` + `universidad_nombre` + `tipo_entidad_universidad`, todos read-only vía `source` de cadena.
- `selectors.convenios_visibles` agrega `select_related("organo_regional__tipo_organo_regional", "universidad__tipo_entidad")`, por lo que `list` y `retrieve` (que pasan por `get_queryset`/`get_object`) resuelven los labels sin N+1.
- Al ser NOT NULL, las cadenas no quedan nulas en datos válidos.

### 5. Schema doc — OK
Refleja exactamente columnas, destinos de FK, nulabilidad y la nota de derivación (ver criterio 1).

### 6. Flujo existente no roto — OK
Acciones de flujo (`cambiar-estado`, `evaluacion-tecnica`, `opinion-conapres`, `campos-clinicos`, `opinion-juridica`, `firma`, `publicacion`, `participantes`, `historial`), el `solicitante` polimórfico y `ConventionParticipant` permanecen intactos. `ConventionFilter` agrega `organo_regional` y `universidad` como filtros `exact` sin alterar los previos.

---

## Observaciones menores (severidad BAJA / informativa — no bloquean)

1. **[BAJA — calidad de datos] Backfill arbitrario.** Las 5 filas existentes reciben el primer `RegionalOrgan` y la primera `University` por `id`. Son valores de relleno semánticamente arbitrarios; deben corregirse manualmente tras migrar (o vía un fixup posterior) para que cada convenio apunte a su órgano/universidad real. Es una decisión aceptada por el usuario, no un defecto técnico.

2. **[BAJA — micro-optimización] Respuestas de `create`/`update`.** `ConventionViewSet.create` y `_read` construyen `ConventionReadSerializer` sobre el objeto devuelto por el service (no recargado por el selector), por lo que los 4 labels derivados disparan ~2-4 queries adicionales para ese único objeto. No es N+1 de lista (las vistas `list`/`retrieve` sí usan el selector con `select_related`). Si se desea, recargar el objeto vía `selectors.convenios_visibles(...).get(pk=...)` antes de serializar la respuesta. Opcional.

---

## Conclusión

El refactor es correcto y consistente en las siete capas revisadas (modelo, migración, serializer read/write, service, filtro, selector, schema doc). No hay hallazgos de severidad alta o media. Se puede cerrar el cambio; las observaciones BAJAS son de calidad de datos y micro-optimización, no de conformidad.
