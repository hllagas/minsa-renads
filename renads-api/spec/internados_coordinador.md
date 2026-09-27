# Spec — Coordinador de tutores (`internados`)

## 1. Resumen

Nuevo perfil **Coordinador**: persona a cargo de los tutores de una universidad en una
sede docente. El coordinador puede ser también tutor (enlace opcional). Puede representar
a una universidad en múltiples sedes sin límite. La asignación de tutores a un coordinador
es por (universidad, sede), garantizando que en cada par (universidad, sede) un tutor
pertenece a un solo coordinador.

### Entidades afectadas


| Entidad / Tabla                                  | Cambio                                                                  |
| ------------------------------------------------ | ----------------------------------------------------------------------- |
| `coordinador` (nueva)                            | Perfil del coordinador; mismos campos que `tutor` + FK opcional a tutor |
| `coordinador_sede` (nueva)                       | Asignación coordinador ↔ universidad ↔ sede docente                     |
| `coordinador_tutor` (nueva)                      | Asignación de tutores a un coordinador por sede                         |
| `apps/internados/models.py`                      | Tres nuevas clases                                                      |
| `apps/internados/migrations/0032_coordinador.py` | Migración única                                                         |
| `apps/internados/serializers.py`                 | Tres nuevos serializers                                                 |
| `apps/internados/services.py`                    | Cuatro nuevas funciones                                                 |
| `apps/internados/views.py`                       | `CoordinatorViewSet` con acciones anidadas                              |
| `config/urls.py`                                 | Registrar router de coordinadores                                       |
| `docs/db_schema_modulo_02_internados.md`         | Nueva sección §5 Coordinador                                            |
| `docs/db_schema_er_global.md`                    | Nodos y relaciones del coordinador                                      |
| `CLAUDE.md`                                      | Reglas RN-CRD-01..06                                                    |


---



## 2. Reglas de negocio


| Regla         | Descripción                                                                                                                                                                                     | Capa de aplicación                            |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| **RN-CRD-01** | Un coordinador está a cargo de los tutores de **una universidad** en **una sede docente** (`ipress.es_sede_docente=True`). La relación se modela en `coordinador_sede`.                         | Service                                       |
| **RN-CRD-02** | Un coordinador **puede** ser también tutor. `coordinador.tutor_id` es nullable; si se informa, debe ser único entre coordinadores (una persona–tutor no puede ser dos coordinadores distintos). | Service + DB `unique=True, null=True`         |
| **RN-CRD-03** | Un coordinador puede representar múltiples pares (universidad, sede) sin límite. No hay tope de cardinalidad en `coordinador_sede`.                                                             | Sin validación adicional                      |
| **RN-CRD-04** | La sede asignada debe tener `ipress.es_sede_docente=True`.                                                                                                                                      | Service `validar_asignacion_coordinador_sede` |
| **RN-CRD-05** | La `unidad_ejecutora` de la sede asignada debe tener ≥1 `convenio` con `tipo=ESPECIFICO`, `estado=VIGENTE` y `universidad` igual a la del registro.                                             | Service `validar_asignacion_coordinador_sede` |
| **RN-CRD-06** | En el par (universidad, sede), un tutor pertenece a **un solo coordinador** (unicidad de tutor por sede y universidad). Validado antes del insert.                                              | Service `asignar_tutor_coordinador_sede`      |


---



## 3. Tareas por capa



### Capa 0 — Modelos

**Tarea 1 — Crear modelo** `Coordinator`

Archivo: `apps/internados/models.py`

Agregar después del bloque de modelos `TutorUniversity` / `TutorConvenio`:

```
class Coordinator(models.Model):
    tutor              FK → Tutor         (SET_NULL, null=True, blank=True, unique=True)
    tipo_documento_identidad   FK → IdentityDocumentType  (PROTECT)
    numero_documento   varchar(20)   NOT NULL   único
    nombres            varchar(150)  NOT NULL
    apellido_paterno   varchar(100)  NOT NULL
    apellido_materno   varchar(100)  NULL
    correo             varchar(255)  NULL
    telefono           varchar(30)   NULL
    numero_colegiatura varchar(50)   NULL
    direccion          varchar(500)  NULL
    ubigeo             FK → Ubigeo   (PROTECT, null=True, blank=True)
    especialidad       FK → Specialty (SET_NULL, null=True, blank=True)
    profesion          FK → ProfessionalCareer (PROTECT, null=True, blank=True)
    activo             BooleanField  default=True
```

Especificaciones:

- `tutor`: `ForeignKey("Tutor", on_delete=SET_NULL, null=True, blank=True, unique=True, db_column="tutor_id", related_name="coordinador", help_text="Tutor vinculado (si el coordinador también es tutor)")`
- `numero_documento`: `unique=True` — un coordinador es una persona identificable de forma única.
- `Meta.db_table = "coordinador"`
- `Meta.verbose_name = "coordinador"`
- `Meta.verbose_name_plural = "coordinadores"`
- `__str__` retorna `f"{self.nombres} {self.apellido_paterno}"`

Importaciones: los modelos `Tutor`, `IdentityDocumentType`, `Ubigeo`, `Specialty`,
`ProfessionalCareer` ya están importados en `models.py`; verificar que `SET_NULL` esté
en el import de `django.db.models`.

Criterio de aceptación: clase `Coordinator` con exactamente los campos listados;
`tutor_id` nullable y único; `numero_documento` único.

---

**Tarea 2 — Crear modelo** `CoordinatorSede`

Archivo: `apps/internados/models.py`

Agregar después de `Coordinator`:

```
class CoordinatorSede(models.Model):
    coordinador   FK → Coordinator  (CASCADE)
    universidad   FK → University   (PROTECT)
    ipress        FK → Ipress       (PROTECT)  — varchar(8) PK textual
```

Especificaciones:

- `coordinador`: `ForeignKey(Coordinator, on_delete=CASCADE, db_column="coordinador_id", related_name="sedes", help_text="Coordinador")`
- `universidad`: `ForeignKey("apps.convenios.University", on_delete=PROTECT, db_column="universidad_id", related_name="coordinadores_sede", help_text="Universidad")`
- `ipress`: `ForeignKey(Ipress, on_delete=PROTECT, db_column="ipress_id", related_name="coordinadores_sede", help_text="Sede docente (código RENIPRESS de 8 chars)")`
- `Meta.db_table = "coordinador_sede"`
- `Meta.verbose_name = "sede del coordinador"`
- `Meta.verbose_name_plural = "sedes del coordinador"`
- `Meta.unique_together = [("coordinador", "universidad", "ipress")]`
- `__str__` retorna `f"Coordinador {self.coordinador_id} — {self.ipress_id} ({self.universidad_id})"`

Importar `University` desde `apps.convenios.models` si no está ya en el bloque de imports.

Criterio de aceptación: `unique_together` en los tres campos; la IPRESS referencia el
`codigo_renipress` (varchar 8, PK textual de `ipress`).

---

**Tarea 3 — Crear modelo** `CoordinatorTutor`

Archivo: `apps/internados/models.py`

Agregar después de `CoordinatorSede`:

```
class CoordinatorTutor(models.Model):
    coordinador_sede  FK → CoordinatorSede  (CASCADE)
    tutor             FK → Tutor            (PROTECT)
```

Especificaciones:

- `coordinador_sede`: `ForeignKey(CoordinatorSede, on_delete=CASCADE, db_column="coordinador_sede_id", related_name="tutores_asignados", help_text="Asignación coordinador-sede")`
- `tutor`: `ForeignKey(Tutor, on_delete=PROTECT, db_column="tutor_id", related_name="coordinaciones", help_text="Tutor asignado")`
- `Meta.db_table = "coordinador_tutor"`
- `Meta.verbose_name = "tutor del coordinador"`
- `Meta.verbose_name_plural = "tutores del coordinador"`
- `Meta.unique_together = [("coordinador_sede", "tutor")]`
- `__str__` retorna `f"Tutor {self.tutor_id} → CoordinadorSede {self.coordinador_sede_id}"`

**Nota importante sobre RN-CRD-06:** el `unique_together` evita duplicados dentro del
mismo `coordinador_sede`. La unicidad global `(tutor, universidad, ipress)` — es decir,
un tutor bajo un solo coordinador por (universidad, sede) — se valida en el service
(`asignar_tutor_coordinador_sede`) antes del insert, ya que el constraint de DB no puede
abarcar columnas de una FK relacionada.

Criterio de aceptación: `unique_together` en `(coordinador_sede, tutor)`.

---



### Capa 1 — Migración

**Tarea 4 — Crear migración** `0032_coordinador`

Archivo: `apps/internados/migrations/0032_coordinador.py`

Dependencias:

- `("internados", "0031_fix_identity_document_types")`
- `("convenios", "0054_rename_organic_unit")` — verificar que siga siendo la última al momento de implementar.

Operaciones en orden:

1. `CreateModel` para `Coordinator` (todos los campos incluyendo `tutor` nullable único).
2. `CreateModel` para `CoordinatorSede` con FK a `Coordinator`, `University` e `Ipress`; `unique_together`.
3. `CreateModel` para `CoordinatorTutor` con FK a `CoordinatorSede` y `Tutor`; `unique_together`.

Una sola migración de tres `CreateModel` secuenciales (sin datos semilla; sin migraciones de datos previas).

Criterio de aceptación: `python manage.py migrate` aplica sin errores; `python manage.py makemigrations --check` no detecta diferencias.

---



### Capa 2 — Serializers

**Tarea 5 — Crear** `CoordinatorSerializer`

Archivo: `apps/internados/serializers.py`

Campos:

- `id` — solo lectura.
- `tutor` — `PrimaryKeyRelatedField(queryset=im.Tutor.objects.all(), allow_null=True, required=False)` — write.
- `tipo_documento_identidad` — PK write.
- `numero_documento` — CharField write.
- `nombres`, `apellido_paterno`, `apellido_materno`, `correo`, `telefono`, `numero_colegiatura`, `direccion` — write.
- `ubigeo` — PK write, allow_null.
- `especialidad` — PK write, allow_null.
- `profesion` — PK write, allow_null.
- `activo` — BooleanField.
- `tutor_detalle` — `SerializerMethodField(read_only=True)`: retorna `{"id": obj.tutor_id, "nombres": ..., "apellido_paterno": ...}` si `tutor_id` no es nulo, o `None`.

`Meta.model = Coordinator`, `fields = ["id", "tutor", "tutor_detalle", "tipo_documento_identidad", "numero_documento", "nombres", "apellido_paterno", "apellido_materno", "correo", "telefono", "numero_colegiatura", "direccion", "ubigeo", "especialidad", "profesion", "activo"]`.

Validaciones en el serializer:

- Ninguna de negocio (unicidad de `numero_documento` y de `tutor_id` la cubre el modelo;
el DRF `UniqueValidator` se genera automáticamente desde `unique=True` en el campo del modelo).

Criterio de aceptación: serializer crear/actualizar un `Coordinator`; `tutor_detalle` solo lectura.

---

**Tarea 6 — Crear** `CoordinatorSedeSerializer`

Archivo: `apps/internados/serializers.py`

Agregar después de `CoordinatorSerializer`.

Campos:

- `id` — solo lectura.
- `coordinador` — `PrimaryKeyRelatedField(read_only=True)` (se inyecta desde la vista).
- `universidad` — PK write.
- `ipress` — PK write.
- `universidad_detalle` — `SerializerMethodField`: `{"id": obj.universidad_id, "nombre": obj.universidad.nombre}`.
- `ipress_detalle` — `SerializerMethodField`: `{"id": obj.ipress_id, "nombre": obj.ipress.nombre}`.

`Meta.model = CoordinatorSede`, `fields = ["id", "coordinador", "universidad", "ipress", "universidad_detalle", "ipress_detalle"]`.

Criterio de aceptación: serializer deserializa un par `(universidad, ipress)`; ambos `_detalle` son solo lectura.

---

**Tarea 7 — Crear** `CoordinatorTutorSerializer`

Archivo: `apps/internados/serializers.py`

Agregar después de `CoordinatorSedeSerializer`.

Campos:

- `id` — solo lectura.
- `coordinador_sede` — `PrimaryKeyRelatedField(read_only=True)` (se inyecta desde la vista).
- `tutor` — `PrimaryKeyRelatedField(queryset=im.Tutor.objects.all())` — write.
- `tutor_detalle` — `SerializerMethodField`: `{"id": obj.tutor_id, "nombres": obj.tutor.nombres, "apellido_paterno": obj.tutor.apellido_paterno, "numero_documento": obj.tutor.numero_documento}`.

`Meta.model = CoordinatorTutor`, `fields = ["id", "coordinador_sede", "tutor", "tutor_detalle"]`.

Criterio de aceptación: serializer acepta un `tutor` PK por escritura; `tutor_detalle` solo lectura.

---



### Capa 3 — Services

**Tarea 8 — Agregar** `validar_asignacion_coordinador_sede`

Archivo: `apps/internados/services.py`

Agregar después de `validar_universidades_tutor`:

```python
def validar_asignacion_coordinador_sede(*, ipress, universidad):
```

Reglas (lanza `ValidationError` con mensaje en español):

- **RN-CRD-04:** `ipress.es_sede_docente` debe ser `True`.
Mensaje: `"La IPRESS indicada no es una sede docente autorizada."`
- **RN-CRD-05:** debe existir al menos un `Convention` con
`tipo_convenio__codigo="ESPECIFICO"`, `estado="VIGENTE"`,
`universidad=universidad`, `unidad_ejecutora=ipress.unidad_ejecutora`.
Mensaje: `"La sede docente no pertenece a una unidad ejecutora con Convenio Específico vigente para la universidad indicada."`

No retorna nada; solo lanza si hay error.

Importaciones necesarias: `from apps.convenios.models import Convention` (verificar que esté en el bloque de imports de services).

Criterio de aceptación: rechaza sedes no docentes; rechaza sedes sin convenio específico vigente para la universidad dada.

---

**Tarea 9 — Agregar** `crear_coordinador_sede` **y** `eliminar_coordinador_sede`

Archivo: `apps/internados/services.py`

`crear_coordinador_sede(*, coordinador, universidad, ipress, usuario) -> CoordinatorSede`

- Llama a `validar_asignacion_coordinador_sede(ipress=ipress, universidad=universidad)`.
- Verifica unicidad anticipada: si existe `CoordinatorSede(coordinador, universidad, ipress)` → `ValidationError("El coordinador ya está asignado a esta sede para esta universidad.")`.
- Crea y retorna el `CoordinatorSede`.
- Llama a `registrar_auditoria(usuario, "CREAR", coordinador_sede)` post-creación.

`eliminar_coordinador_sede(*, coordinador_sede, usuario) -> None`

- Llama a `registrar_auditoria(usuario, "ELIMINAR", coordinador_sede)`.
- Ejecuta `coordinador_sede.delete()` (CASCADE elimina los `CoordinatorTutor` asociados).

Criterio de aceptación: `crear_coordinador_sede` rechaza sedes inválidas y duplicados; ambas funciones auditan.

---

**Tarea 10 — Agregar** `asignar_tutor_coordinador_sede` **y** `desasignar_tutor_coordinador_sede`

Archivo: `apps/internados/services.py`

`asignar_tutor_coordinador_sede(*, coordinador_sede, tutor, usuario) -> CoordinatorTutor`

- **RN-CRD-06:** verifica que no exista ningún `CoordinatorTutor` donde
`coordinador_sede__universidad=coordinador_sede.universidad` AND
`coordinador_sede__ipress=coordinador_sede.ipress` AND
`tutor=tutor`.
Si existe → `ValidationError("El tutor ya está asignado a un coordinador en esta sede para esta universidad.")`.
- Verifica unicidad anticipada del `unique_together`: si existe `CoordinatorTutor(coordinador_sede, tutor)` → `ValidationError("El tutor ya está asignado a este coordinador en esta sede.")`.
- Crea y retorna `CoordinatorTutor`.
- Llama a `registrar_auditoria(usuario, "CREAR", coordinador_tutor)`.

`desasignar_tutor_coordinador_sede(*, coordinador_tutor, usuario) -> None`

- Llama a `registrar_auditoria(usuario, "ELIMINAR", coordinador_tutor)`.
- Ejecuta `coordinador_tutor.delete()`.

Criterio de aceptación: `asignar_tutor_coordinador_sede` rechaza duplicados globales (RN-CRD-06) y locales; ambas funciones auditan.

---



### Capa 4 — Views

**Tarea 11 — Crear** `CoordinatorViewSet` **con acciones anidadas**

Archivo: `apps/internados/views.py`

Clase base:

```python
class CoordinatorViewSet(viewsets.ModelViewSet):
    queryset = im.Coordinator.objects.select_related(
        "tutor", "tipo_documento_identidad", "ubigeo", "especialidad", "profesion"
    ).order_by("apellido_paterno", "nombres")
    serializer_class = CoordinatorSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["activo", "universidades_coordinadas__universidad", "universidades_coordinadas__ipress"]
    search_fields = ["nombres", "apellido_paterno", "numero_documento"]
```

Nota: `filterset_fields` usa el `related_name="sedes"` de `CoordinatorSede`; ajustar el
nombre según el `related_name` definido en el modelo.

Escritura restringida: inyectar `IsUniversityOrAdminOrReadOnly` (o equivalente) para
limitar POST/PATCH/DELETE al rol `Universidad` o `Administrador RENADS`.

---

**Acción** `sedes` **— list + create de** `CoordinatorSede`

```python
@action(detail=True, methods=["get", "post"], url_path="sedes")
def sedes(self, request, pk=None):
```

- `GET`: retorna `CoordinatorSedeSerializer(qs, many=True).data`.
Queryset: `im.CoordinatorSede.objects.filter(coordinador=coordinador).select_related("universidad", "ipress")`.
- `POST`: exige rol `Universidad` o `Administrador RENADS`.
Valida con `CoordinatorSedeSerializer(data=request.data)`.
Llama a `services.crear_coordinador_sede(coordinador=coordinador, universidad=ser.validated_data["universidad"], ipress=ser.validated_data["ipress"], usuario=request.user)`.
Retorna `CoordinatorSedeSerializer(cs).data` con status 201.

---

**Acción** `sede_detail` **— retrieve + delete de** `CoordinatorSede`

```python
@action(detail=True, methods=["get", "delete"], url_path="sedes/(?P<sede_pk>[^/.]+)")
def sede_detail(self, request, pk=None, sede_pk=None):
```

- Resuelve: `cs = get_object_or_404(im.CoordinatorSede, coordinador=coordinador, pk=sede_pk)`.
- `GET`: retorna `CoordinatorSedeSerializer(cs).data`.
- `DELETE`: exige rol. Llama a `services.eliminar_coordinador_sede(coordinador_sede=cs, usuario=request.user)`. Retorna 204.

---

**Acción** `sede_tutores` **— list + assign tutores a un** `CoordinatorSede`

```python
@action(detail=True, methods=["get", "post"], url_path="sedes/(?P<sede_pk>[^/.]+)/tutores")
def sede_tutores(self, request, pk=None, sede_pk=None):
```

- Resuelve sede: `cs = get_object_or_404(im.CoordinatorSede, coordinador=coordinador, pk=sede_pk)`.
- `GET`: retorna `CoordinatorTutorSerializer(qs, many=True).data`.
Queryset: `im.CoordinatorTutor.objects.filter(coordinador_sede=cs).select_related("tutor")`.
- `POST`: exige rol.
Valida con `CoordinatorTutorSerializer(data=request.data)`.
Llama a `services.asignar_tutor_coordinador_sede(coordinador_sede=cs, tutor=ser.validated_data["tutor"], usuario=request.user)`.
Retorna `CoordinatorTutorSerializer(ct).data` con status 201.

---

**Acción** `sede_tutor_detail` **— delete de** `CoordinatorTutor`

```python
@action(detail=True, methods=["delete"], url_path="sedes/(?P<sede_pk>[^/.]+)/tutores/(?P<tutor_pk>[^/.]+)")
def sede_tutor_detail(self, request, pk=None, sede_pk=None, tutor_pk=None):
```

- Resuelve: `cs = get_object_or_404(im.CoordinatorSede, coordinador=coordinador, pk=sede_pk)`.
- Resuelve: `ct = get_object_or_404(im.CoordinatorTutor, coordinador_sede=cs, tutor_id=tutor_pk)`.
- `DELETE`: exige rol. Llama a `services.desasignar_tutor_coordinador_sede(coordinador_tutor=ct, usuario=request.user)`. Retorna 204.

Criterio de aceptación global:

- `GET /api/v1/coordinators/` → lista con filtros.
- CRUD básico en `/api/v1/coordinators/{id}/`.
- Acciones de sedes y tutores funcionan según lo descrito.
- Escritura bloqueada sin rol.

---



### Capa 5 — URL Router

**Tarea 12 — Registrar** `CoordinatorViewSet` **en el router**

Archivo: `config/urls.py` (o el archivo donde se registran los routers de la app internados).

```python
router.register(r"coordinators", CoordinatorViewSet, basename="coordinator")
```

Verificar que el import de `CoordinatorViewSet` esté incluido en el bloque de imports
del archivo de URLs.

Criterio de aceptación: `GET /api/v1/coordinators/` responde 200.

---



### Capa 6 — Documentación del schema

**Tarea 13 — Actualizar** `docs/db_schema_modulo_02_internados.md`

Agregar sección **§5. Coordinador** (antes de §6 — Rotaciones, o como nueva sección numerada):

```markdown
## 5. Coordinador

### `coordinador`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tutor_id` | FK → `tutor` (SET_NULL), único | Sí | Tutor vinculado (si el coordinador también es tutor — RN-CRD-02) |
| `tipo_documento_identidad_id` | FK → `tipo_documento_identidad` | No | |
| `numero_documento` | varchar(20), único | No | |
| `nombres` | varchar(150) | No | |
| `apellido_paterno` | varchar(100) | No | |
| `apellido_materno` | varchar(100) | Sí | |
| `correo` | varchar(255) | Sí | |
| `telefono` | varchar(30) | Sí | |
| `numero_colegiatura` | varchar(50) | Sí | |
| `direccion` | varchar(500) | Sí | |
| `ubigeo_id` | FK → `ubigeo` (PROTECT) — varchar(6) | Sí | |
| `especialidad_id` | FK → `especialidad` | Sí | |
| `profesion_id` | FK → `carrera_profesional` (PROTECT) | Sí | |
| `activo` | bool | No | |

> **RN-CRD-01..03:** un coordinador gestiona los tutores de una universidad en una sede
> docente. Puede ser también tutor (RN-CRD-02, `tutor_id` único nullable). Puede
> representar múltiples (universidad, sede) sin límite (RN-CRD-03).

### `coordinador_sede` (asignación coordinador ↔ universidad ↔ sede — RN-CRD-01)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `coordinador_id` | FK → `coordinador` (CASCADE) | No | |
| `universidad_id` | FK → `universidad` (PROTECT) | No | |
| `ipress_id` | FK → `ipress` (PROTECT) — varchar(8) | No | Sede docente (código RENIPRESS) |

Único por `(coordinador_id, universidad_id, ipress_id)`.
La sede debe cumplir RN-CRD-04 (`es_sede_docente=True`) y RN-CRD-05 (unidad ejecutora
con Convenio Específico vigente para la universidad).

Endpoints: `GET/POST /api/v1/coordinators/{id}/sedes/`,
`GET/DELETE /api/v1/coordinators/{id}/sedes/{sede_pk}/`.

### `coordinador_tutor` (tutores asignados a un coordinador por sede — RN-CRD-06)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `coordinador_sede_id` | FK → `coordinador_sede` (CASCADE) | No | |
| `tutor_id` | FK → `tutor` (PROTECT) | No | |

Único por `(coordinador_sede_id, tutor_id)`. RN-CRD-06: un tutor es único a un
coordinador por (universidad, sede) — validado en service antes del insert.

Endpoints: `GET/POST /api/v1/coordinators/{id}/sedes/{sede_pk}/tutores/`,
`DELETE /api/v1/coordinators/{id}/sedes/{sede_pk}/tutores/{tutor_pk}/`.
```

También agregar en §1 (Tablas reutilizadas del módulo 1): `convenio` referenciado desde
`validar_asignacion_coordinador_sede` (RN-CRD-05).

Criterio de aceptación: schema sincronizado con los modelos; todas las columnas y reglas
documentadas.

---

**Tarea 14 — Actualizar** `docs/db_schema_er_global.md`

Agregar en el diagrama Mermaid (sección internados):

```
coordinador ||--o{ coordinador_sede : "sedes (RN-CRD-01)"
coordinador_sede }o--|| universidad : ""
coordinador_sede }o--|| ipress : "sede docente (RN-CRD-04/05)"
coordinador_sede ||--o{ coordinador_tutor : "tutores asignados"
coordinador_tutor }o--|| tutor : "(RN-CRD-06)"
coordinador }o--o| tutor : "también tutor (RN-CRD-02)"
```

Criterio de aceptación: nodos y relaciones del coordinador reflejados en el ER global.

---

**Tarea 15 — Actualizar** `CLAUDE.md`

En la sección **Reglas del módulo Registrar Internados**, agregar bloque para coordinador
después de RN-24:

```
- **RN-CRD-01 (coordinador por sede):** un coordinador está a cargo de los tutores de una
  universidad en una sede docente (`ipress.es_sede_docente=True`). Relación en
  `coordinador_sede`.
- **RN-CRD-02 (coordinador puede ser tutor):** `coordinador.tutor_id` nullable y único;
  una persona registrada como tutor puede ser a la vez coordinador (enlace opcional).
- **RN-CRD-03 (sedes sin límite):** un coordinador puede representar múltiples pares
  (universidad, sede) sin tope de negocio.
- **RN-CRD-04 (sede docente):** la sede asignada debe tener `ipress.es_sede_docente=True`.
  Validado en `services.validar_asignacion_coordinador_sede`.
- **RN-CRD-05 (convenio vigente):** la `unidad_ejecutora` de la sede debe tener ≥1
  `convenio` con `tipo=ESPECIFICO`, `estado=VIGENTE` y `universidad` igual a la del
  registro. Validado en `services.validar_asignacion_coordinador_sede`.
- **RN-CRD-06 (tutor único por coordinador en sede):** en cada par (universidad, sede)
  un tutor pertenece a un solo coordinador. Validado en
  `services.asignar_tutor_coordinador_sede` antes del insert.
```

Criterio de aceptación: CLAUDE.md refleja todas las reglas RN-CRD-*.

---



## 4. Orden de ejecución

```
T1 → T2 → T3 → T4 → T5 → T6 → T7
(modelos: Coordinator, CoordinatorSede, CoordinatorTutor)   (migración)   (serializers)

   → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15
    (services: validar, crear/eliminar sede, asignar/desasignar tutor)
    (views + router)   (docs schema, ER, CLAUDE.md)
```

T1-T3 en un solo commit de modelos. T4 depende de T1-T3. T5-T12 son independientes
entre sí una vez aplicada la migración.

---



## 5. Notas sobre la migración

- Tres `CreateModel` en un solo archivo `0032_coordinador.py`; sin datos semilla.
- `coordinador.tutor_id` nullable único: PostgreSQL permite múltiples NULL con
`UNIQUE` constraint, comportamiento correcto.
- No hay migración de datos: entidad nueva sin registros previos.
- Verificar el número de última migración de convenios antes de escribir `dependencies`.

---



## 6. Endpoints — resumen


| Endpoint                                                        | Método           | Descripción                         | Rol escritura                  |
| --------------------------------------------------------------- | ---------------- | ----------------------------------- | ------------------------------ |
| `/api/v1/coordinators/`                                         | GET              | Lista con filtros                   | —                              |
| `/api/v1/coordinators/`                                         | POST             | Crear coordinador                   | `Universidad` / `Admin RENADS` |
| `/api/v1/coordinators/{id}/`                                    | GET/PATCH/DELETE | Detalle / editar / eliminar         | `Universidad` / `Admin RENADS` |
| `/api/v1/coordinators/{id}/sedes/`                              | GET              | Listar sedes asignadas              | —                              |
| `/api/v1/coordinators/{id}/sedes/`                              | POST             | Asignar sede                        | `Universidad` / `Admin RENADS` |
| `/api/v1/coordinators/{id}/sedes/{sede_pk}/`                    | GET              | Detalle sede                        | —                              |
| `/api/v1/coordinators/{id}/sedes/{sede_pk}/`                    | DELETE           | Desasignar sede (CASCADE → tutores) | `Universidad` / `Admin RENADS` |
| `/api/v1/coordinators/{id}/sedes/{sede_pk}/tutores/`            | GET              | Listar tutores de la sede           | —                              |
| `/api/v1/coordinators/{id}/sedes/{sede_pk}/tutores/`            | POST             | Asignar tutor                       | `Universidad` / `Admin RENADS` |
| `/api/v1/coordinators/{id}/sedes/{sede_pk}/tutores/{tutor_pk}/` | DELETE           | Desasignar tutor                    | `Universidad` / `Admin RENADS` |


---



## 7. Cambios fuera de alcance de este spec

- No se modifica `interno.tutor_id` ni ningún flujo de internado existente.
- No se agrega el coordinador al `UserProfile` ni al onboarding de usuario (RN-22 sin cambio).
- No se expone el coordinador en `/auth/me/` ni en `modulos_habilitados`.
- No se agrega gate `IsModuleEnabled` al `CoordinatorViewSet` (fuera del alcance del MVP).
- No se incluyen pruebas automatizadas.

