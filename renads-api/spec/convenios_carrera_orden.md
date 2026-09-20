# Spec — convenios: campo `orden` en `ProfessionalCareer`

## Resumen del módulo

Cambio acotado al módulo `convenios` (`apps/convenios`). Agrega el campo `orden` (`IntegerField`, `default=0`) al modelo `ProfessionalCareer` (tabla `carrera_profesional`) para controlar el orden de visualización en el frontend. El endpoint `professional-careers` pasa a ordenar por `["orden", "nombre"]` por defecto y expone `orden` como campo editable para `Administrador RENADS`.

Entidades afectadas: `ProfessionalCareer` (tabla `carrera_profesional`).

---

## Tareas

### Capa: Modelo (`apps/convenios/models.py`)

**T1 — Agregar campo `orden` a `ProfessionalCareer`**

Ubicar la clase `ProfessionalCareer` (~línea 731) e insertar el campo **justo antes** de `activo`:

```python
orden = models.IntegerField(
    "orden",
    default=0,
    help_text="Orden de visualización en el listado (menor primero)",
)
```

El campo `activo` queda como último campo de datos del modelo.

Criterios de aceptación:
- La clase `ProfessionalCareer` declara `orden` entre `nivel_academico` y `activo`.
- `python manage.py check` no reporta errores en `apps.convenios`.
- `python manage.py makemigrations --check --dry-run` detecta exactamente un cambio pendiente (el `AddField`), antes de aplicar T2.

---

### Capa: Migración (`apps/convenios/migrations/`)

**T2 — Crear migración `0053_professionalcareer_orden.py`**

Generar (o escribir manualmente) una migración `AddField` sobre `carrera_profesional` con las siguientes características:

- Nombre de archivo: `0053_professionalcareer_orden.py`
- Dependencia única: `("convenios", "0052_university_entity_type")`
- Operación: `migrations.AddField(model_name="professionalcareer", name="orden", field=models.IntegerField(default=0, help_text="Orden de visualización en el listado (menor primero)", verbose_name="orden"))`
- No requiere `RunPython` ni `RunSQL`; el `default=0` del campo cubre las filas existentes en la migración automáticamente.

Criterios de aceptación:
- El archivo existe en `apps/convenios/migrations/0053_professionalcareer_orden.py`.
- `python manage.py makemigrations --check --dry-run` no detecta cambios pendientes tras aplicar esta migración (modelo y migración están sincronizados).
- La migración es reversible (`state_forwards` + `database_backwards` estándar de `AddField`).

---

### Capa: ViewSet (`apps/convenios/views.py`)

**T3 — Actualizar `_entity_viewset` de `professional-careers`**

Localizar la entrada `"professional-careers"` en el diccionario `ENTITY_VIEWSETS` (~línea 960) y modificar la llamada a `_entity_viewset`:

Cambios:
1. Agregar el parámetro `ordering=["orden", "nombre"]` para reemplazar el default `["id"]`.
2. Agregar `"ordering_fields": ["id", "orden", "nombre"]` dentro de los atributos del viewset generado.

La firma resultante debe ser equivalente a:

```python
"professional-careers": _entity_viewset(
    m.ProfessionalCareer,
    filterset_fields=["nivel_academico", "activo"],
    search_fields=["nombre"],
    ordering=["orden", "nombre"],
),
```

Adicionalmente, verificar que `_entity_viewset` propaga `ordering_fields` cuando se pasa `ordering`. Si `_entity_viewset` no acepta ni propaga `ordering_fields`, agregar ese parámetro al helper (análogo a como acepta `ordering`) para que el viewset generado lo incluya como atributo de clase.

Notas de implementación:
- El serializer automático (`_auto_serializer`) toma `fields = "__all__"`, por lo que incluirá `orden` en cuanto el campo exista en el modelo. No se requiere serializer explícito.
- Los permisos no cambian: `IsAuthenticated + IsAdminRoleOrReadOnly` (solo `Administrador RENADS` puede escribir, todos los autenticados pueden leer).

Criterios de aceptación:
- `GET /api/v1/professional-careers/` devuelve resultados ordenados por `orden ASC`, luego `nombre ASC`, sin parámetro `?ordering` explícito.
- `GET /api/v1/professional-careers/?ordering=orden` y `?ordering=nombre` responden 200 con el orden solicitado.
- `GET /api/v1/professional-careers/?ordering=-orden` devuelve orden descendente por `orden`.
- El campo `orden` aparece en el cuerpo JSON de las respuestas de lista y de detalle.
- `PATCH /api/v1/professional-careers/{id}/` con `{"orden": 5}` como `Administrador RENADS` responde 200 y persiste el valor.
- `PATCH /api/v1/professional-careers/{id}/` como usuario sin rol `Administrador RENADS` responde 403.

---

### Capa: Documentación (`docs/db_schema_modulo_01_convenios.md`)

**T4 — Actualizar schema de `carrera_profesional`**

Localizar la sección de la tabla `carrera_profesional` en `docs/db_schema_modulo_01_convenios.md` e insertar la fila del campo `orden` en la tabla de columnas, **entre `nivel_academico_id` y `activo`**:

| Columna | Tipo | Nulo | Descripción |
|---------|------|------|-------------|
| `orden` | `int` | No | Orden de visualización en el listado (default 0, menor primero) |

Criterios de aceptación:
- La tabla de columnas de `carrera_profesional` en el `.md` lista `orden` con tipo `int`, nulabilidad `No` y la descripción indicada.
- El orden de filas en la tabla del doc refleja el orden de campos en el modelo Django: `id`, `nombre`, `nivel_academico_id`, `orden`, `activo`.

---

## Criterios de aceptación globales

1. `python manage.py check` pasa sin errores ni warnings relevantes.
2. `python manage.py makemigrations --check --dry-run` no detecta cambios pendientes (modelo y migración están sincronizados).
3. `GET /api/v1/professional-careers/` ordena por `orden ASC, nombre ASC` por defecto.
4. `?ordering=orden` y `?ordering=nombre` funcionan; `?ordering=-orden` invierte el orden.
5. El campo `orden` aparece en la respuesta JSON (lista y detalle).
6. `PATCH` con `{"orden": 5}` funciona para `Administrador RENADS` (200) y es rechazado para otros roles (403).
7. `migrate` y `test` **no** los ejecuta el agente `implement`.

---

## Referencias

### Tablas / columnas del schema

- Tabla: `carrera_profesional` (`docs/db_schema_modulo_01_convenios.md`)
  - Columna nueva: `orden INT NOT NULL DEFAULT 0`
  - Columnas existentes: `id`, `nombre`, `nivel_academico_id`, `activo`

### Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `apps/convenios/models.py` | T1 — campo `orden` en `ProfessionalCareer` |
| `apps/convenios/migrations/0053_professionalcareer_orden.py` | T2 — migración `AddField` |
| `apps/convenios/views.py` | T3 — `ordering` y `ordering_fields` en `professional-careers` |
| `docs/db_schema_modulo_01_convenios.md` | T4 — fila `orden` en tabla `carrera_profesional` |

### Reglas de negocio aplicables

Ninguna regla de negocio de dominio (RN-*) involucrada. El cambio es puramente de presentación (campo de ordenación). Los permisos existentes (`IsAdminRoleOrReadOnly`) se mantienen sin modificación.
