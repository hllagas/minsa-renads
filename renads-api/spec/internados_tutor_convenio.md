# Spec — Refactor Tutor ↔ Convenio ↔ Ipress (`internados`)

## 1. Resumen

El campo `tutor.ipress_id` modela la pertenencia del tutor a una IPRESS como dato fijo
del tutor, sin relacionarlo con el convenio específico en el que opera. El nuevo diseño
introduce la tabla `tutor_convenio` para registrar esa relación **por convenio**: un tutor
puede estar asignado a distintas IPRESS en distintos Convenios Específicos.

### Entidades afectadas

| Entidad / Tabla | Cambio |
|---|---|
| `tutor` | Eliminar columna `ipress_id` |
| `tutor_convenio` (nueva) | Tabla puente tutor ↔ convenio ↔ ipress |
| Modelo `Tutor` | Quitar campo `ipress` |
| Modelo `TutorConvenio` (nuevo) | Nuevo modelo |
| `TutorSerializer` | Quitar `ipress` e `ipress_detalle` |
| `TutorViewSet` | Quitar filtro `ipress`; agregar acción anidada `convenios` |
| `apps/internados/services.py` | Nueva función `_validar_tutor_convenio` |
| `apps/internados/serializers.py` | Nuevo `TutorConvenioSerializer` |
| `docs/db_schema_modulo_02_internados.md` | Actualizar §4 Tutor / docente |
| Migración `0027` | Única migración de un solo paso |

---

## 2. Tareas numeradas por capa

### Capa 0 — Modelo

**Tarea 1 — Quitar `ipress` de `Tutor`**

Archivo: `apps/internados/models.py`

- Eliminar el campo `ipress = models.ForeignKey(Ipress, ...)` (línea 194-197).
- Eliminar el `related_name="tutores"` que apuntaba desde `Ipress` a `Tutor` (ese
  `related_name` deja de existir).
- Ajustar el `select_related` de los comentarios de `__str__` si aplica (el `__str__`
  actual no usa `ipress`, por lo que no requiere cambio de lógica).

Criterio de aceptación: la clase `Tutor` no contiene ninguna referencia a `ipress`.

---

**Tarea 2 — Crear modelo `TutorConvenio`**

Archivo: `apps/internados/models.py`

Agregar la clase inmediatamente después de `TutorUniversity` (después de la línea 228):

```
class TutorConvenio(models.Model):
    tutor        FK → Tutor       (CASCADE)
    convenio     FK → Convention  (PROTECT)
    ipress       FK → Ipress      (PROTECT)  — NOT NULL, varchar(8) PK textual
```

Especificaciones del modelo:

- `tutor`: `ForeignKey(Tutor, on_delete=CASCADE, db_column="tutor_id", related_name="convenios_tutor", help_text="Tutor")`
- `convenio`: `ForeignKey(Convention, on_delete=PROTECT, db_column="convenio_id", related_name="tutores_convenio", help_text="Convenio Específico")`
- `ipress`: `ForeignKey(Ipress, on_delete=PROTECT, db_column="ipress_id", related_name="tutores_convenio", help_text="Establecimiento (código RENIPRESS de 8 chars, PK textual de ipress)")`
- `Meta.db_table = "tutor_convenio"`
- `Meta.verbose_name = "convenio del tutor"`
- `Meta.verbose_name_plural = "convenios del tutor"`
- `Meta.unique_together = [("tutor", "convenio")]`
- `__str__` retorna `f"Tutor {self.tutor_id} — Convenio {self.convenio_id}"`

Importaciones necesarias: `Convention` ya se importa en `apps.convenios.models`; verificar
que esté en el bloque `from apps.convenios.models import (...)` al inicio del archivo.
Agregar `Convention` si no está presente.

Criterio de aceptación: `TutorConvenio` tiene exactamente los tres FK indicados, la
restricción `unique_together` y el `db_table` correcto.

---

### Capa 1 — Migración

**Tarea 3 — Crear migración `0027_tutor_convenio`**

Archivo: `apps/internados/migrations/0027_tutor_convenio.py`

La migración es de **un solo paso** (no multi-paso), porque:
- La columna `tutor.ipress_id` es nullable (`SET_NULL`); su eliminación no requiere
  backfill ni pasos intermedios.
- No hay datos de producción que deban preservarse (entorno de desarrollo con SQLite).
- En PostgreSQL el `RemoveField` es un `ALTER TABLE ... DROP COLUMN`, operación atómica.

Dependencias de la migración:
- `("internados", "0026_student_nota_decimal3")`
- `("convenios", "<última_migración_de_convenios>")` — verificar el último número de la
  carpeta `apps/convenios/migrations/` antes de escribir la migración.

Operaciones (en este orden):

1. `RemoveField(model_name="tutor", name="ipress")` — elimina la columna `ipress_id` de la
   tabla `tutor`.
2. `CreateModel` para `TutorConvenio` con los tres ForeignKey, la restricción
   `unique_together` y `db_table="tutor_convenio"`.

No se requiere migración de datos: el campo era nullable y la asignación de tutores a
IPRESS se rehará por convenio a través del nuevo endpoint.

Criterio de aceptación: `python manage.py migrate` aplica sin errores; `python manage.py
makemigrations --check` no detecta diferencias adicionales.

---

### Capa 2 — Serializers

**Tarea 4 — Limpiar `TutorSerializer`**

Archivo: `apps/internados/serializers.py`

- Eliminar el campo `ipress_detalle = serializers.SerializerMethodField(read_only=True)`
  (línea 95).
- Eliminar el método `get_ipress_detalle` (líneas 106-108).
- Mantener intacto el resto de `TutorSerializer` (campos `universidades`,
  `profesion_detalle`, `especialidad_detalle`, `validate_universidades`, `create`,
  `update`).
- Ajustar el `queryset` del `TutorViewSet` (Tarea 7) para que ya no haga
  `select_related("ipress")`.

Criterio de aceptación: `TutorSerializer` no referencia `ipress` en ningún campo ni método.

---

**Tarea 5 — Crear `TutorConvenioSerializer`**

Archivo: `apps/internados/serializers.py`

Agregar el serializer después de `TutorSerializer`:

Campos:
- `id` — lectura automática (PK).
- `tutor` — `PrimaryKeyRelatedField` (read_only=True); se inyecta desde la vista.
- `convenio` — `PrimaryKeyRelatedField(queryset=Convention.objects.all())` — escritura;
  lectura expone el id.
- `ipress` — `PrimaryKeyRelatedField(queryset=Ipress.objects.all())` — escritura; el
  queryset no filtra por `es_sede_docente` en el serializer (la validación de negocio
  está en el service).
- `convenio_detalle` — `SerializerMethodField(read_only=True)`: devuelve
  `{"id": obj.convenio.id, "titulo": obj.convenio.titulo, "tipo": obj.convenio.tipo_convenio.codigo}`.
- `ipress_detalle` — `SerializerMethodField(read_only=True)`: devuelve
  `{"id": obj.ipress.pk, "nombre": obj.ipress.nombre}`.

Meta:
- `model = TutorConvenio`
- `fields = ["id", "tutor", "convenio", "ipress", "convenio_detalle", "ipress_detalle"]`

Validaciones en el serializer (nivel campo, no negocio):
- Ninguna adicional; la regla de tipo de convenio es responsabilidad del service.

Importaciones necesarias: agregar `TutorConvenio` al bloque de imports de modelos del
módulo internados; agregar `Convention` al bloque de imports de `apps.convenios.models`
si no está ya presente en el archivo.

Criterio de aceptación: el serializer serializa y deserializa un `TutorConvenio` con los
cinco campos expuestos; `convenio_detalle` e `ipress_detalle` son solo lectura.

---

### Capa 3 — Services

**Tarea 6 — Agregar service `crear_tutor_convenio` y `eliminar_tutor_convenio`**

Archivo: `apps/internados/services.py`

Agregar dos funciones después de `validar_universidades_tutor`:

**`crear_tutor_convenio(*, tutor, convenio, ipress, usuario) -> TutorConvenio`**

Reglas de negocio (todas lanzan `ValidationError` en español):
- **RN-TC-01:** `convenio.tipo_convenio.codigo` debe ser `"ESPECIFICO"`. Mensaje:
  `"Solo se pueden asociar Convenios Específicos a un tutor."`.
- **RN-TC-02:** No debe existir ya un `TutorConvenio` con `(tutor, convenio)` (duplicado).
  Mensaje: `"El tutor ya está asociado a este convenio."`. (La `unique_together` lo
  garantiza en BD; esta validación anticipa el error con mensaje legible antes del
  `IntegrityError`.)
- La función ejecuta la creación dentro de `@transaction.atomic` (o hereda la transacción
  del llamador).
- Llama a `registrar_auditoria(usuario, "CREAR", tutor_convenio)` tras crear.

Retorna la instancia `TutorConvenio` recién creada.

**`eliminar_tutor_convenio(*, tutor_convenio, usuario) -> None`**

- Llama a `registrar_auditoria(usuario, "ELIMINAR", tutor_convenio)` antes de borrar.
- Ejecuta `tutor_convenio.delete()`.
- No hay restricciones adicionales de negocio en el MVP; el `PROTECT` de `convenio` e
  `ipress` lo protege en BD.

Importaciones: agregar `TutorConvenio` al bloque de imports de modelos de internados en
`services.py` (líneas 32-45).

Criterio de aceptación:
- `crear_tutor_convenio` rechaza convenios Marco con `ValidationError`.
- `crear_tutor_convenio` rechaza duplicados con `ValidationError` antes del hit a BD.
- Ambas funciones registran auditoría.

---

### Capa 4 — Views

**Tarea 7 — Actualizar `TutorViewSet` y agregar acción `convenios`**

Archivo: `apps/internados/views.py`

Cambios en `TutorViewSet`:

1. Actualizar `queryset`:
   ```
   # Antes:
   queryset = im.Tutor.objects.select_related("especialidad", "ipress").prefetch_related("universidades")
   # Después:
   queryset = im.Tutor.objects.select_related("especialidad").prefetch_related("universidades")
   ```

2. Actualizar `filterset_fields`: quitar `"ipress"` de la lista.
   ```
   # Antes:
   filterset_fields = ["especialidad", "ipress", "universidades", "numero_documento", "activo"]
   # Después:
   filterset_fields = ["especialidad", "universidades", "numero_documento", "activo"]
   ```

3. Agregar dos acciones anidadas bajo `TutorViewSet` usando `@action(detail=True, ...)`:

   **Acción `convenios` (list + create)**

   ```
   @action(detail=True, methods=["get", "post"], url_path="convenios")
   def convenios(self, request, pk=None):
   ```

   - `GET`: retorna todos los `TutorConvenio` del tutor, usando
     `TutorConvenioSerializer(qs, many=True).data`. El queryset se obtiene con
     `im.TutorConvenio.objects.filter(tutor=tutor).select_related("convenio", "convenio__tipo_convenio", "ipress")`.
   - `POST`: exige rol `Universidad` o `Administrador RENADS` (llamar `exigir_roles(request, "Universidad", "Administrador RENADS")`).
     Valida con `TutorConvenioSerializer(data=request.data)`. Llama a
     `services.crear_tutor_convenio(tutor=tutor, convenio=ser.validated_data["convenio"], ipress=ser.validated_data["ipress"], usuario=request.user)`.
     Retorna `TutorConvenioSerializer(tc).data` con status 201.

   **Acción `convenio_detail` (retrieve + delete)**

   ```
   @action(detail=True, methods=["get", "delete"], url_path="convenios/(?P<convenio_pk>[^/.]+)")
   def convenio_detail(self, request, pk=None, convenio_pk=None):
   ```

   - Resuelve el objeto: `tc = get_object_or_404(im.TutorConvenio, tutor=tutor, convenio_id=convenio_pk)`.
   - `GET`: retorna `TutorConvenioSerializer(tc).data`.
   - `DELETE`: exige rol `Universidad` o `Administrador RENADS`. Llama a
     `services.eliminar_tutor_convenio(tutor_convenio=tc, usuario=request.user)`.
     Retorna `Response(status=204)`.

   Importaciones necesarias en `views.py`:
   - `from django.shortcuts import get_object_or_404`
   - Agregar `TutorConvenioSerializer` al bloque de imports de `apps.internados.serializers`.

Criterio de aceptación:
- `GET /api/v1/tutors/{id}/convenios/` devuelve la lista de `TutorConvenio` del tutor.
- `POST /api/v1/tutors/{id}/convenios/` crea un vínculo; rechaza si el convenio es Marco.
- `GET /api/v1/tutors/{id}/convenios/{convenio_pk}/` devuelve el vínculo individual.
- `DELETE /api/v1/tutors/{id}/convenios/{convenio_pk}/` elimina el vínculo.
- Escritura bloqueada para roles sin permiso.

---

### Capa 5 — Filters

**Tarea 8 — Limpiar `TutorFilter` (implícito en `filterset_fields`)**

Archivo: `apps/internados/views.py` (el filtro de `TutorViewSet` usa `filterset_fields`
inline, no un `FilterSet` independiente en `filters.py`).

El cambio ya queda cubierto en la Tarea 7 (quitar `"ipress"` de `filterset_fields`).

No hay archivo `filters.py` que referencie `ipress` en el modelo `Tutor`; confirmado en
`apps/internados/filters.py` (que solo define `StudentFilter`, `InternshipFilter` y
`RotationFilter`, sin filtro de tutores).

Criterio de aceptación: ningún filtro del módulo internados referencia `Tutor.ipress`.

---

### Capa 6 — Selectors

**Tarea 9 — (Opcional) Agregar selector `convenios_del_tutor`**

Archivo: `apps/internados/selectors.py`

Si la vista necesita reutilizar la consulta en otro contexto, exponer:

```python
def convenios_del_tutor(tutor) -> QuerySet[TutorConvenio]:
    return TutorConvenio.objects.filter(tutor=tutor).select_related(
        "convenio", "convenio__tipo_convenio", "ipress"
    )
```

La acción de la vista puede llamar a este selector en lugar de construir el queryset
inline. Decisión de implementación delegada al agente Implement; si la consulta es simple
y no se reutiliza, puede quedarse inline.

Criterio de aceptación: si existe el selector, la vista lo consume; el queryset incluye
`select_related` para evitar N+1 en el serializer al leer `convenio_detalle` e
`ipress_detalle`.

---

### Capa 7 — Documentación del schema

**Tarea 10 — Actualizar `docs/db_schema_modulo_02_internados.md`**

Archivo: `docs/db_schema_modulo_02_internados.md`

Sección **§4. Tutor / docente**:

1. Eliminar la fila `ipress_id` de la tabla `tutor`:

   ```
   | `ipress_id` | FK → `ipress` (SET_NULL) — varchar(8) | Sí | Establecimiento al que pertenece ... |
   ```

2. Agregar una nueva subsección `### tutor_convenio` después de `### tutor_universidad`:

   ```
   ### `tutor_convenio` (vínculo tutor ↔ convenio específico ↔ ipress)

   | Columna | Tipo | Null | Descripción |
   |---------|------|------|-------------|
   | `id` | PK | No | |
   | `tutor_id` | FK → `tutor` (CASCADE) | No | Tutor |
   | `convenio_id` | FK → `convenio` (PROTECT) | No | Convenio Específico |
   | `ipress_id` | FK → `ipress` (PROTECT) — varchar(8) | No | Establecimiento (código RENIPRESS de 8 chars, PK textual de `ipress`) |

   Único por `(tutor_id, convenio_id)`. Solo se admiten Convenios de tipo `ESPECIFICO`
   (validado en `services.crear_tutor_convenio`).
   ```

3. Actualizar la nota RN-24 al final de la sección para mencionar la nueva tabla.

4. En §1 Tablas reutilizadas, en la tabla "Del módulo 1", agregar una nota que
   `convenio` también es referenciado desde `tutor_convenio`.

Criterio de aceptación: el schema refleja exactamente las columnas del modelo, sin
`ipress_id` en `tutor` y con la nueva tabla `tutor_convenio` documentada.

---

## 3. Orden de ejecución

```
Tarea 1  →  Tarea 2  →  Tarea 3  →  Tarea 4  →  Tarea 5
(modelo)    (modelo)    (migración)  (serializer  (serializer
 quitar      crear                    limpiar)     nuevo)
 ipress      TutorConvenio

   →  Tarea 6  →  Tarea 7  →  Tarea 8  →  Tarea 9  →  Tarea 10
     (service)    (views)     (filters)    (selector)   (docs)
```

Las Tareas 1 y 2 pueden hacerse en el mismo commit de modelos; la Tarea 3 depende de
ellas. Las Tareas 4-9 son independientes entre sí una vez creada la migración.

---

## 4. Reglas de negocio y dónde se aplican

| Regla | Capa | Descripción |
|---|---|---|
| RN-TC-01 | Service (`crear_tutor_convenio`) | Solo Convenios Específicos admitidos; lanza `ValidationError` |
| RN-TC-02 | Service (`crear_tutor_convenio`) | Unicidad `(tutor, convenio)` anticipada con mensaje legible |
| RN-24 | Serializer (`TutorSerializer`) | Sin cambio; sigue en `validate_universidades` |

No hay validaciones de negocio en el serializer `TutorConvenioSerializer`: la regla de
tipo de convenio es de negocio (nivel service), no de forma (nivel serializer).

---

## 5. Notas sobre la migración

- **Un solo paso** es seguro porque `tutor.ipress_id` es nullable; no hay datos que
  deban migrarse a la nueva tabla.
- En SQLite (desarrollo), `RemoveField` emite un `ALTER TABLE ... DROP COLUMN` desde
  Django 4.0+; en versiones anteriores reconstruye la tabla. Dado que el proyecto usa
  Django 6.0.6, la operación es directa en ambos motores.
- La nueva tabla `tutor_convenio` no tiene datos semilla; no se necesita migración de
  datos.
- Dependencia de `convenios`: verificar el número de la última migración de la app
  `convenios` consultando `apps/convenios/migrations/` antes de escribir el campo
  `dependencies`.
- Nombre de migración: `0027_tutor_convenio`.

---

## 6. Referencias al schema

| Elemento | Tabla / Columna | Schema |
|---|---|---|
| Campo eliminado | `tutor.ipress_id` | `docs/db_schema_modulo_02_internados.md` §4 |
| Nueva tabla | `tutor_convenio` | `docs/db_schema_modulo_02_internados.md` §4 (a agregar) |
| FK a convenio | `tutor_convenio.convenio_id` → `convenio` | `docs/db_schema_modulo_01_convenios.md` |
| FK a ipress | `tutor_convenio.ipress_id` → `ipress.codigo_renipress` (varchar 8, PK textual) | `CLAUDE.md` §RNF — PK textual de `ipress` |
| RN-24 | `tutor_universidad.tutor_id` / `tutor_universidad.universidad_id` | Sin cambio |

---

## 7. Cambios que NO forman parte de este spec

- No se modifica la FK `interno.tutor_id` (el interno sigue referenciando `Tutor`
  directamente).
- No se modifica `InternshipFilter` ni ningún filtro de internados (el filtro `ipress`
  de `InternshipFilter` filtra por `interno.ipress_id`, no por `tutor.ipress_id`).
- No se modifican `services.crear_internado` ni `services.cambiar_tutor`: el cambio de
  tutor en un internado sigue siendo por FK directa a `Tutor`.
- No se agrega alcance institucional a la acción `convenios` más allá del control de
  rol ya existente en `IsUniversityOrReadOnly`.
- No se incluyen pruebas automatizadas (fuera del alcance del MVP).
