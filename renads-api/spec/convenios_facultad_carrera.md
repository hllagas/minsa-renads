# Spec — Facultad en `universidad_carrera` y asignación de carreras por facultad (`convenios_facultad_carrera`)

Producido por el agente **spec** (SDD). El agente **implement** ejecuta estas tareas en orden; el **validator** revisa contra este documento. **No se escribe código de aplicación en este archivo**, solo la lista exacta de tareas.

Fuentes de verdad: `docs/db_schema_modulo_01_convenios.md`, `docs/arquitectura_desarrollo.md`, `apps/convenios/models.py`, `CLAUDE.md`.

---

## Resumen del módulo

Refactor de la relación **carreras por universidad** para incorporar la **facultad** como parte del registro. Hoy `universidad_carrera` (`UniversityCareer`) es una tabla puente `universidad ↔ carrera_profesional`; se le añade la FK `facultad` (a `Faculty`, tabla `facultad`) para que cada carrera profesional quede asociada además a la facultad de la universidad que la dicta.

El caso de uso de negocio es una **inclusión del registro de facultades por universidad**: en la interfaz "carreras por universidad" primero se selecciona una facultad y sobre ella se marcan (checkbox) las carreras profesionales que correspondan. Por eso se agrega una **acción en lote** que cuelga del recurso `faculties`: `POST /api/v1/faculties/{id}/careers`.

**Entidades cubiertas:**

| Entidad (modelo) | Tabla | Rol en este refactor |
|---|---|---|
| `Faculty` | `facultad` | Recurso padre de la asignación en lote (acción `careers`) |
| `ProfessionalCareer` | `carrera_profesional` | Carreras marcables (sin cambios de modelo) |
| `UniversityCareer` | `universidad_carrera` | Puente `universidad ↔ carrera_profesional`; **gana la FK `facultad`** |
| `University` | `universidad` | Se conserva en el puente (explícito y filtrable) |

**Reglas de negocio de este refactor:**

- **RN-FC-01 (unicidad):** una carrera profesional se registra **una sola vez por universidad**, sin importar la facultad. Se conserva `unique_together = (universidad, carrera_profesional)`.
- **RN-FC-02 (coherencia facultad↔universidad):** la `facultad` de un `universidad_carrera` debe pertenecer a la misma universidad del registro (`facultad.universidad_id == universidad_id`). Validación en el serializer de escritura y en el service de sincronización.
- **RN-FC-03 (facultad requerida en API):** `facultad` es opcional a nivel DB (`null=True, blank=True`) por compatibilidad con las 3 filas existentes (precedente `Convention.facultad`), pero **requerida en el serializer de escritura** de `university-careers` y derivada automáticamente en la acción en lote.

**Endpoints afectados:**

- `/api/v1/university-careers/` (CRUD unitario existente): expone y valida `facultad`; nuevo filtro `facultad`.
- `POST /api/v1/faculties/{id}/careers` (**nuevo**): sincroniza en lote las carreras de una facultad.

**Archivos a modificar:** `apps/convenios/models.py`, nueva migración `apps/convenios/migrations/0026_*.py`, `apps/convenios/serializers.py`, `apps/convenios/views.py`, `apps/convenios/services.py`, `docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_er_global.md`, `CLAUDE.md`.

---

## Dependencias entre tareas

```
T1 (modelo) → T2 (migración) → T3 (serializer write) → T4 (viewset faculties + acción) 
                              → T5 (service sincronización)  ── consumido por T4
T3, T6 (filtro university-careers) dependen de T1/T2
T7 (docs) al final; T8 (verificación) tras todo lo anterior
```

- T1 y T2 son prerrequisito de todo lo demás.
- T4 depende de T5 (la acción consume el service) y de T3 (reutiliza el serializer de escritura para exponer resultados).
- T7 y T8 al final.

---

## T1 — Modelo `UniversityCareer`: añadir campo `facultad`

**Archivo:** `apps/convenios/models.py` (clase `UniversityCareer`, actualmente ~líneas 640–660).

Añadir la FK `facultad` a `Faculty`, conservando el resto del modelo intacto.

Especificación exacta del campo nuevo:

- Nombre de atributo: `facultad`.
- `models.ForeignKey(Faculty, ...)` — `on_delete=models.PROTECT`.
- `db_column="facultad_id"`.
- `related_name="carreras_facultad"` (evita colisión; `Faculty` no tiene aún un reverse a `UniversityCareer`). Verificar que no colisione con otros `related_name` sobre `Faculty`.
- `null=True, blank=True`.
- `help_text="Facultad de la universidad a la que pertenece la carrera"` (español).

Requisitos adicionales:

- **Ubicación de la clase:** `Faculty` está definida **antes** de `UniversityCareer` en el archivo, por lo que la referencia directa a la clase `Faculty` es válida (no usar string lazy salvo que resulte necesario por orden de definición).
- Conservar `universidad` (FK PROTECT, `related_name="carreras"`), `carrera_profesional` (FK PROTECT, `related_name="universidades"`) y `activo` sin cambios.
- Conservar `unique_together = (("universidad", "carrera_profesional"),)` **sin modificar** (la unicidad NO incluye `facultad`).
- Conservar `db_table = "universidad_carrera"`, `verbose_name`/`verbose_name_plural` en español.
- Docstring de la clase en español, actualizada para mencionar la facultad, p. ej.: `"""Tabla puente universidad ↔ carrera profesional (carreras que dicta cada universidad), asociada a la facultad que la imparte."""`.

**Criterios de aceptación:**

- La clase `UniversityCareer` tiene los cuatro campos `facultad`, `universidad`, `carrera_profesional`, `activo`.
- `unique_together` permanece `(("universidad", "carrera_profesional"),)`.
- `help_text` y docstring/verbose en español; nombres de atributo/columna/`related_name` en inglés/español según convención (`db_column="facultad_id"`).
- `python manage.py check` no reporta errores de `related_name` duplicado.

**Referencias:** `docs/db_schema_modulo_01_convenios.md` §`universidad_carrera` (líneas ~264–275) y §`facultad` (~246–253).

---

## T2 — Migración de esquema

**Archivo nuevo:** `apps/convenios/migrations/0026_universitycareer_facultad.py` (nombre real lo genera `makemigrations`; debe depender de `0025_convention_adenda_partes_resol_conapres`).

- Generar con `python manage.py makemigrations convenios` tras T1.
- Debe contener un único `AddField` de `facultad` sobre `UniversityCareer` con `null=True` (por eso NO requiere `default` ni pregunta interactiva; las 3 filas existentes quedan con `facultad = NULL`).
- No debe alterar `unique_together` (permanece igual) ni tocar otros modelos.

**Criterios de aceptación:**

- `python manage.py migrate` aplica sin errores sobre la BD dev (3 filas `universidad_carrera`, 1 fila `facultad`).
- `python manage.py makemigrations --check --dry-run` queda **limpio** (sin migraciones pendientes) tras aplicar.
- Las 3 filas preexistentes conservan sus datos con `facultad_id = NULL`.

**Referencias:** precedente de FK `facultad` opcional a nivel DB en `Convention.facultad` (migración `0025`).

---

## T3 — Serializer de escritura/lectura de `university-careers`

**Archivo:** `apps/convenios/views.py` (entrada `"university-careers"` del dict `ENTITY_VIEWSETS`, ~líneas 602–609) y, si se requiere validación custom, `apps/convenios/serializers.py`.

Situación actual: `university-careers` usa `_entity_viewset(m.UniversityCareer, ...)` con `serializer_class = _auto_serializer(model, detalles=...)` generado por el factory (`fields="__all__"`, más `*_detalle` por cada entrada de `detalles`).

Como `facultad` es `null=True` a nivel modelo, el `ModelSerializer` autogenerado la haría **opcional**. Para cumplir **RN-FC-03** (requerida en escritura) y **RN-FC-02** (coherencia facultad↔universidad) se necesita un serializer explícito. Tareas:

### T3.1 — Serializer explícito `UniversityCareerSerializer` (en `apps/convenios/serializers.py`)

- Definir un `ModelSerializer` sobre `m.UniversityCareer` con `fields = "__all__"` (equivalente al autogenerado) que:
  - Declare `facultad` como **requerido** (`required=True, allow_null=False`), pese al `null=True` del modelo.
  - Añada los campos de solo lectura de detalle: `universidad_detalle`, `carrera_profesional_detalle` y **`facultad_detalle`** (nuevos), replicando el formato `{id, codigo|None, nombre}` que produce `_detalle_nombre`. Se puede reutilizar el helper `_auto_serializer` con `detalles={"universidad": _detalle_nombre, "carrera_profesional": _detalle_nombre, "facultad": _detalle_nombre}` como base y sobreescribir `facultad` a requerido, o declarar los `SerializerMethodField` manualmente. Elegir el enfoque que menos duplique lógica; documentar cuál se usó en el código.
  - Implemente `validate()` que aplique **RN-FC-02**: `facultad.universidad_id == universidad_id`. Mensaje de error en español, p. ej.: `"La facultad seleccionada no pertenece a la universidad indicada."` Considerar `partial` (PATCH): al validar tomar el valor entrante o el de la instancia para `universidad` y `facultad`.

> Nota: `Faculty` no tiene campo `codigo`; `_detalle_nombre` ya maneja la ausencia con `getattr(rel, "codigo", None)`, así que `facultad_detalle` devolverá `{id, codigo: null, nombre}`. Aceptable.

### T3.2 — Enlazar el serializer al viewset

- En `views.py`, reemplazar la generación por factory de la entrada `"university-careers"` para que use `UniversityCareerSerializer` (importado de `serializers.py`). Dos opciones válidas:
  - (a) Pasar el serializer explícito al viewset generado (definir un ViewSet dedicado análogo a `IpressViewSet`, que hereda de `_entity_viewset(...)` y sobreescribe `serializer_class`), o
  - (b) Extender el factory. **Preferir (a)** por consistencia con el patrón `IpressViewSet` ya usado en el archivo.
- Mantener `permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]` (escritura solo `Administrador RENADS`), auditoría heredada de `AuditedModelViewSet`.

**Criterios de aceptación:**

- `POST /api/v1/university-careers/` **sin** `facultad` responde 400 con mensaje en español (RN-FC-03).
- `POST`/`PATCH` con `facultad` cuya universidad no coincide con `universidad` responde 400 con mensaje en español (RN-FC-02).
- La lectura (`GET` list/retrieve) expone `facultad`, `facultad_detalle`, `universidad_detalle`, `carrera_profesional_detalle`.
- La escritura sigue restringida a `Administrador RENADS` y auditada.

**RN en serializer:** RN-FC-02 y RN-FC-03 son **validaciones de serializer** en el CRUD unitario.

---

## T5 — Service de sincronización en lote

**Archivo:** `apps/convenios/services.py`.

Definir la función pública:

```
sincronizar_carreras_facultad(*, facultad, carreras_ids, usuario) -> list[UniversityCareer]
```

Comportamiento (idempotente, todo dentro de `transaction.atomic()`):

1. Derivar `universidad = facultad.universidad` (no se recibe del cliente).
2. Normalizar `carreras_ids` a un conjunto de enteros; validar que cada id exista en `ProfessionalCareer` (400 con mensaje en español si alguno no existe).
3. **RN-FC-01 (unicidad por universidad):** por cada carrera enviada, buscar o crear la fila `universidad_carrera` de `(universidad, carrera_profesional)`:
   - Si existe (con o sin la misma facultad): fijar `facultad = facultad`, `activo = True` y guardar (upsert por reactivación / reasignación de facultad).
   - Si no existe: crear con `universidad`, `carrera_profesional`, `facultad`, `activo=True`.
   - **RN-FC-02:** como la facultad se deriva de la universidad, la coherencia queda garantizada por construcción; aun así, validar defensivamente `facultad.universidad_id == universidad_id`.
4. **Baja de las que ya no están:** las filas `universidad_carrera` **de esa facultad** (`facultad=facultad`) cuya carrera **no** esté en `carreras_ids` se marcan `activo=False` (no se borran, preserva historial y evita `ProtectedError`). El alcance de baja es **por facultad**, no por universidad (no dar de baja carreras que la universidad tiene registradas contra otra facultad).
5. Registrar auditoría con `registrar_auditoria(usuario, accion, objeto)` por cada alta/reactivación/baja (usar acciones `"CREAR"`, `"ACTUALIZAR"` según corresponda), siguiendo el patrón del resto de `services.py`.
6. Devolver la lista de filas `universidad_carrera` **activas** resultantes de la facultad (para que la vista arme la respuesta / checklist).

Consideraciones:

- Idempotencia: llamar dos veces con el mismo `carreras_ids` no debe producir cambios ni auditoría redundante innecesaria (evaluar si registrar auditoría solo cuando hubo cambio real de estado).
- Manejar el caso `carreras_ids = []` (da de baja todas las carreras activas de esa facultad).
- Mensajes de error de validación en español.

**Criterios de aceptación:**

- Enviar `[A, B]` y luego `[B, C]` deja activas `{B, C}` de esa facultad y `A` en `activo=False`.
- Una carrera ya registrada para la universidad contra **otra** facultad no se ve afectada por la sincronización de esta facultad (respeta el alcance por facultad y la unicidad por universidad).
- Todas las operaciones quedan auditadas en `bitacora_auditoria`.
- Ninguna fila se elimina físicamente.

**RN en service:** RN-FC-01 y RN-FC-02 (defensiva) y la lógica de alta/baja (activo) son **reglas de negocio en el service**.

---

## T4 — ViewSet de `faculties` con acción en lote `careers`

**Archivo:** `apps/convenios/views.py` (entrada `"faculties"` de `ENTITY_VIEWSETS`, ~líneas 594–596) y serializer de entrada en `apps/convenios/serializers.py`.

Situación actual: `"faculties"` se genera con `_entity_viewset(m.Faculty, filterset_fields=["universidad", "activo"], search_fields=["nombre"])`, que no admite acciones custom. Hay que definir un **ViewSet dedicado para `Faculty`** siguiendo el patrón de `IpressViewSet` (hereda del viewset generado por el factory y añade la `@action`).

### T4.1 — Serializer de entrada de la acción

En `serializers.py`, definir un serializer de entrada, p. ej. `FacultyCareersSyncSerializer`:

- Campo `carreras`: `PrimaryKeyRelatedField(queryset=ProfessionalCareer.objects.all(), many=True)` (o `ListField(child=IntegerField())` validando existencia en el service). Preferir `PrimaryKeyRelatedField(many=True)` para validación temprana de ids.
- Permitir lista vacía (`allow_empty=True`) para poder dar de baja todas.

### T4.2 — ViewSet `FacultyViewSet` con la acción

- Definir `FacultyViewSet` heredando de `_entity_viewset(m.Faculty, filterset_fields=["universidad", "activo"], search_fields=["nombre"])` (mismo patrón que `IpressViewSet`), conservando CRUD, permisos (`IsAuthenticated, IsAdminRoleOrReadOnly`) y auditoría.
- Añadir:

```
@action(detail=True, methods=["post"], url_path="careers")
def careers(self, request, pk=None):
    ...
```

Lógica de la acción:

1. `facultad = self.get_object()`.
2. `exigir_roles(request, "Administrador RENADS")` (mismo criterio de escritura que las demás entidades CRUD; superusuario exento según la implementación de `exigir_roles`/permisos del proyecto — respetar el comportamiento vigente de `IsAdminRoleOrReadOnly`/`exigir_roles`).
3. Validar el body con `FacultyCareersSyncSerializer` (`is_valid(raise_exception=True)`).
4. Llamar `resultado = services.sincronizar_carreras_facultad(facultad=facultad, carreras_ids=[...], usuario=request.user)`.
5. Responder 200 con la lista de `universidad_carrera` resultantes serializadas con `UniversityCareerSerializer` (reutiliza T3.1: incluye `facultad_detalle`, `carrera_profesional_detalle`), p. ej. `{"carreras": UniversityCareerSerializer(resultado, many=True).data}`.

- **Actualizar la entrada del dict:** reemplazar en `ENTITY_VIEWSETS` el valor de `"faculties"` por `FacultyViewSet` (el router en `urls.py` es dinámico y no requiere cambios).

**Criterios de aceptación:**

- `POST /api/v1/faculties/{id}/careers` con `{"carreras": [1,2]}` sincroniza y devuelve 200 con las filas resultantes.
- Escritura restringida a `Administrador RENADS`; un usuario sin ese rol recibe 403.
- La `universidad` de las filas resultantes es la de la facultad (`facultad.universidad`); no se acepta ni se usa `universidad` del body.
- El CRUD unitario de `faculties` (list/retrieve/create/update/delete) sigue funcionando igual.
- Idempotencia verificable: repetir la misma petición no cambia el resultado.

**RN en vista:** la vista solo orquesta (permiso + validación de entrada + delegación al service); la lógica de negocio vive en T5.

---

## T6 — Filtro `facultad` en `university-careers`

**Archivo:** `apps/convenios/views.py` (entrada / ViewSet de `university-careers` de T3.2).

- Añadir `"facultad"` a `filterset_fields`, quedando `["universidad", "carrera_profesional", "facultad", "activo"]`.

**Criterios de aceptación:**

- `GET /api/v1/university-careers/?facultad={id}` filtra por facultad.
- Los filtros previos (`universidad`, `carrera_profesional`, `activo`) siguen operativos.

---

## T7 — Documentación

### T7.1 — `docs/db_schema_modulo_01_convenios.md`

- En §`universidad_carrera` (~líneas 264–275):
  - Añadir la fila de columna: `| facultad_id | FK → facultad (PROTECT) | Sí | Facultad de la universidad que imparte la carrera (opcional en BD por filas históricas; requerida vía API) |`.
  - Mantener la nota de `unique_together = (universidad, carrera_profesional)` y agregar la regla de coherencia `facultad.universidad_id == universidad_id`.
  - Actualizar la línea de Endpoint: filtros ahora `universidad`, `carrera_profesional`, `facultad`, `activo`; lectura expone `universidad_detalle`, `carrera_profesional_detalle` y `facultad_detalle`.
  - Añadir nota del endpoint en lote: `POST /api/v1/faculties/{id}/careers` (body `{carreras: [ids]}`), sincronización idempotente (alta/reactivación + baja por `activo`) por facultad, deriva `universidad` de la facultad, escritura solo `Administrador RENADS`.

### T7.2 — `docs/db_schema_er_global.md`

- Ajustar el diagrama textual (~líneas 669–670) para reflejar que `universidad_carrera` referencia también `facultad`, p. ej. añadir `facultad ──< universidad_carrera`.

### T7.3 — `CLAUDE.md`

- En la sección "Carreras por universidad (Módulo 1)" (viñeta de RNF/catálogos), actualizar a: `university-careers` (tabla puente `universidad_carrera`, `UniversityCareer`; FK `universidad` + `carrera_profesional` + **`facultad`** (PROTECT, opcional en BD, requerida en API), `unique_together (universidad, carrera_profesional)`; validación `facultad.universidad == universidad`; CRUD escritura solo `Administrador RENADS`; filtros `universidad`/`carrera_profesional`/`facultad`/`activo`; lectura expone `universidad_detalle`, `carrera_profesional_detalle`, `facultad_detalle`). Añadir la **acción en lote** `POST /api/v1/faculties/{id}/careers` (`{carreras:[ids]}`, sincronización idempotente por facultad vía `services.sincronizar_carreras_facultad`).

**Criterios de aceptación:**

- Los tres documentos reflejan el campo `facultad`, la regla de unicidad/coherencia y el endpoint en lote.
- Nombres de tabla/columna y descripciones en español; endpoints en inglés.

---

## T8 — Verificación final

Ejecutar (con el entorno virtual activado, `.venv\Scripts\Activate.ps1`):

- `python manage.py makemigrations --check --dry-run` → **sin** migraciones pendientes.
- `python manage.py check` → sin errores.
- `python manage.py spectacular --file nul` → **0 errores** de generación de esquema OpenAPI (la acción `careers` y el serializer explícito deben resolver correctamente).

**Criterios de aceptación:**

- Los tres comandos pasan limpios.
- No queda ninguna referencia rota a `_entity_viewset(m.Faculty, ...)` ni al serializer autogenerado de `university-careers` tras el reemplazo por los viewsets/serializers dedicados.

---

## Fuera de alcance

- Tests automatizados (fuera del MVP, según `CLAUDE.md`).
- Backfill de la `facultad` de las 3 filas históricas (quedan `NULL`; se corrigen al re-sincronizar desde la UI).
- Estados de aprobación/observación de la asignación de carreras.
