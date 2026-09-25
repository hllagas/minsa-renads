# Spec — common: Endurecimiento del perfil de usuario obligatorio (`perfil_usuario`)

**Módulo:** `apps/common`
**Ciclo SDD:** endurecimiento de `UserProfile` (continuación de `spec/common_perfil_usuario.md`)
**Fecha:** 2026-09-24
**Enfoque aprobado:** ENDURECER `perfil_usuario` (NO swap de `AUTH_USER_MODEL`, NO custom user). Django usa el `User` por defecto (`auth.User`, tabla `auth_user`); `UserProfile` es una extensión 1:1.

> **Nota de actualización (refactor posterior — `spec/common_username_dni_apellidos.md`, migración `common 0011`):**
> este spec habla de **7 campos obligatorios** del perfil. El refactor `username_dni_apellidos`
> **elimina** `apellido_paterno` y `apellido_materno` de `perfil_usuario` (pasan a
> `auth_user.last_name`, combinado `"Paterno Materno"`; el nombre a `auth_user.first_name`),
> por lo que el conteo de campos obligatorios del **perfil baja de 7 a 5**
> (`tipo_documento`, `numero_documento`, `telefono`, `unidad_organica`, `cargo`). Además fija
> `username = numero_documento` para todos los usuarios **no-superusuario** (username
> autogenerado/read-only), con **exención total del superusuario**. Leer ese spec para el estado vigente.

---

## 1. Resumen del módulo

Django NO tiene custom user: usa `django.contrib.auth.models.User` (tabla `auth_user`). Los datos personales/institucionales viven en `UserProfile` (tabla `perfil_usuario`, `apps/common/models.py:107`), relación OneToOne con `User`. Hoy todos esos campos son OPCIONALES (nullable o `default=""`).

Este spec vuelve OBLIGATORIOS los campos de identidad e institucionales del perfil, agrega el flag `tiene_ficha_usuario`, y hace un backfill aleatorio coherente sobre los usuarios existentes (respetando unicidad), sin swap de modelo de usuario y sin borrar usuarios.

### Estado de datos medido (postgres docker, `localhost:5433`)

| Dato | Valor |
|---|---|
| `auth_user` | 2 usuarios |
| `perfil_usuario` | 1 fila → **un usuario NO tiene perfil** (crear en la migración) |
| Perfil existente (`usuario_id=2`) | `numero_documento`, `telefono`, `unidad_organica`, `cargo` en NULL → rellenar |
| `convenios.OrganicUnit` (`unidad_organica`) | 14 filas disponibles para backfill FK |
| `convenios.ExecutivePosition` (`cargo`) | 12 filas disponibles para backfill FK |

### Entidades que cubre

| Modelo Python | Tabla BD | Cambio |
|---|---|---|
| `UserProfile` | `perfil_usuario` | Campos → obligatorios + campo nuevo `tiene_ficha_usuario` + migración de datos |

### FKs externas (solo lectura, no se modifican sus modelos)

| Campo | FK a | App | Filas backfill |
|---|---|---|---|
| `UserProfile.unidad_organica` | `convenios.OrganicUnit` (`unidad_organica`) | `apps.convenios` | 14 |
| `UserProfile.cargo` | `convenios.ExecutivePosition` (`cargo_ejecutivo`) | `apps.convenios` | 12 |

---

## 2. Tareas por capa

> **NO se escribe código de aplicación en este spec.** El agente `implement` ejecuta estas tareas exactas.

---

### CAPA 1 — Modelo (`apps/common/models.py`)

#### T-01 — Volver obligatorios los campos existentes de `UserProfile`

En `apps/common/models.py` (clase `UserProfile`, líneas ~124-188) modificar:

| Campo | Estado actual | Estado objetivo |
|---|---|---|
| `tipo_documento` (`:124`) | `blank=True, default=""` | `blank=False` — quitar `default=""` (conserva `choices=DOCUMENT_TYPE_CHOICES`, `max_length=20`) |
| `numero_documento` (`:133`) | `null=True, blank=True, unique=True, default=None` | `null=False, blank=False, unique=True` — quitar `default=None` |
| `apellido_paterno` (`:143`) | `blank=True, default=""` | `blank=False` — quitar `default=""` |
| `apellido_materno` (`:151`) | `blank=True, default=""` | `blank=False` — quitar `default=""` |
| `telefono` (`:159`) | `null=True, blank=True, unique=True, default=None` | `null=False, blank=False, unique=True` — quitar `default=None` |
| `unidad_organica` (`:169`) | `null=True, blank=True, PROTECT` | `null=False, blank=False, PROTECT` (mantener `related_name='perfiles_usuarios'`, `db_column='unidad_organica_id'`) |
| `cargo` (`:179`) | `null=True, blank=True, PROTECT` | `null=False, blank=False, PROTECT` (mantener `related_name='perfiles_usuarios'`, `db_column='cargo_id'`) |

**Criterio de aceptación:** los 7 campos quedan `null=False`/`blank=False`; `numero_documento` y `telefono` conservan `unique=True`; las FK conservan `on_delete=PROTECT` y sus `db_column`.

#### T-02 — Agregar campo `tiene_ficha_usuario` a `UserProfile`

Agregar tras `cargo`:

```python
tiene_ficha_usuario = models.BooleanField(
    "tiene ficha de usuario",
    db_column="tiene_ficha_usuario",
    default=False,
    help_text="Indica si la ficha del usuario está completa/validada",
)
```

**Criterio de aceptación:** campo booleano obligatorio con `default=False`, `db_column="tiene_ficha_usuario"`, descripción en español.

#### T-03 — Actualizar docstring del modelo `UserProfile`

Reflejar en el docstring (`:108-114`) que todos los campos son obligatorios y que `tiene_ficha_usuario` marca la completitud de la ficha. Mantener la mención de que se crea/actualiza vía `services.crear_usuario_con_perfil` / `services.actualizar_perfil_usuario`.

---

### CAPA 2 — Migración (`apps/common/migrations/`)

#### T-04 — Migración `0009_userprofile_campos_obligatorios`

Última migración existente: `0008_userprofile_organic_unit`. La nueva es `0009` con `dependencies = [("common", "0008_userprofile_organic_unit")]`.

**Patrón seguro NOT NULL con datos (orden estricto de operaciones):**

1. **AddField** `tiene_ficha_usuario` (`BooleanField(default=False)`) — seguro directo; `default=False` cubre las filas existentes. Queda `False` en backfill (no se marca `True` salvo indicación del usuario).

2. **RunPython** `backfill_perfiles` (forwards) + reverse `noop` (`migrations.RunPython.noop`). Ver pseudocódigo en §3. En este punto las columnas `numero_documento`/`telefono`/`unidad_organica_id`/`cargo_id` todavía son nullable (estado del modelo previo a T-01 aún vigente en BD), por lo que el RunPython puede escribir sin violar NOT NULL. NO se hace `AlterField` a nullable temporal porque los campos YA son nullable en el estado actual — se pasa directo de "nullable con datos rellenados" a "NOT NULL".

3. **AlterField** de los 7 campos a su estado final (T-01) — `numero_documento`/`telefono` a `null=False`; `tipo_documento`/`apellido_paterno`/`apellido_materno` a `blank=False` sin default vacío; `unidad_organica`/`cargo` a `null=False`. Se ejecutan DESPUÉS del RunPython para que ninguna fila viole el NOT NULL.

> Nota de orden crítica: el `RunPython` debe ir **antes** de los `AlterField` a `null=False`. Si van al revés, la migración falla con `IntegrityError` en las filas con NULL.

**Criterio de aceptación:**
- `python manage.py makemigrations --check --dry-run` limpio tras aplicar (no genera migraciones pendientes).
- `migrate` corre OK en postgres docker.
- Reverse (`migrate common 0008`) no rompe (RunPython reverse es noop; los AlterField revierten a nullable).

#### T-05 — RunPython de backfill (dentro de la migración 0009)

Ver §3 para el pseudocódigo completo. Debe usar modelos históricos (`apps.get_model`), nunca imports directos de los modelos vivos. Nunca borra usuarios.

---

### CAPA 3 — Serializers (`apps/common/serializers.py`)

#### T-06 — `UserProfileReadSerializer` (`:244-269`): exponer `tiene_ficha_usuario`

Agregar `tiene_ficha_usuario` a `Meta.fields` y a `read_only_fields`. El campo se expone en lectura tanto por este serializer directo como anidado en `UserReadSerializer.perfil` (`:347`) y en `MeSerializer.get_perfil` (`:96-102`).

**Criterio:** `GET /api/v1/users/{id}/` y `GET /api/v1/auth/me/` incluyen `perfil.tiene_ficha_usuario`.

#### T-07 — `UserProfileWriteSerializer` (`:304-340`): exigir campos obligatorios + exponer `tiene_ficha_usuario`

- Quitar `required=False, allow_blank=True, allow_null=True` de `numero_documento` (`:307-318`) → dejarlo `required=True`, conservando el `UniqueValidator` (message en español).
- `unidad_organica` (`:319`) y `cargo` (`:324`) `_LazyPrimaryKeyRelatedField`: quitar `required=False, allow_null=True` → `required=True`.
- Los campos heredados del modelo (`tipo_documento`, `apellido_paterno`, `apellido_materno`, `telefono`) serán `required=True` automáticamente al ser `blank=False` en el modelo (`ModelSerializer`). Verificar que `telefono` quede required + único (añadir `UniqueValidator` explícito si el `ModelSerializer` no lo deriva; el modelo tiene `unique=True` así que DRF lo agrega).
- Agregar `tiene_ficha_usuario` a `Meta.fields` (escribible, opcional con default `False`).

**Criterio:** un PATCH/POST de perfil sin `numero_documento`/`telefono`/`unidad_organica`/`cargo`/apellidos/`tipo_documento` responde `400` con errores `required` en español.

#### T-08 — `UserCreateSerializer` (`:379-501`): exigir campos de perfil en el alta

- `tipo_documento` (`:402`): quitar `required=False, allow_blank=True, default=""` → `required=True`.
- `numero_documento` (`:408`): quitar `required=False, allow_blank=True, default=""` → `required=True` + `UniqueValidator` contra `UserProfile.objects.all()` (message español).
- `apellido_paterno` (`:414`) y `apellido_materno` (`:420`): quitar `required=False, allow_blank=True, default=""` → `required=True`.
- `telefono` (`:426`): quitar `required=False, allow_blank=True, default=""` → `required=True` + `UniqueValidator` (message español).
- `unidad_organica` (`:432`) y `cargo` (`:438`): quitar `required=False, allow_null=True, default=None` → `required=True`.
- Agregar `tiene_ficha_usuario` a `Meta.fields` (`:445-466`) y a la lista `campos_perfil` de `_extraer_profile_data` (`:471-490`) — opcional, default `False`.
- `_extraer_profile_data`: la normalización `"" → None` para `numero_documento`/`telefono` (`:487-489`) deja de ser necesaria (ya no admiten blanco) pero puede conservarse inofensiva; documentar que el vacío ahora se rechaza en validación.

**Criterio:** `POST /api/v1/users/` sin los campos de perfil obligatorios → `400`. Con todos → crea `User` + `UserProfile` completo.

#### T-09 — `UserUpdateSerializer` (`:504-619`): exigir campos de perfil en la edición

- `tipo_documento` (`:525`): quitar `required=False, allow_blank=True` → `required=True`. **Ojo PATCH parcial:** para que un `PATCH` que NO toque el perfil no falle, los campos de perfil deben permanecer opcionales en PATCH pero obligatorios en PUT. Decisión: mantenerlos `required=False` a nivel serializer PERO validar en `update`/service que, si el perfil resultante queda incompleto, se rechace. Alternativa más simple y recomendada: dejar `required=False` en `UserUpdateSerializer` (edición parcial) y delegar la exigencia a la constraint de BD + al service. Documentar la decisión elegida en el código.
- `numero_documento` (`:530`): quitar `allow_null=True`; conservar `required=False` para PATCH parcial pero **rechazar blank** (`allow_blank=False`).
- `telefono` (`:546`): igual criterio que `numero_documento`.
- `unidad_organica` (`:552`) / `cargo` (`:557`): quitar `allow_null=True` (no se permite dejar en NULL); conservar `required=False` para PATCH parcial.
- Agregar `tiene_ficha_usuario` a `Meta.fields` (`:563-583`) y a `campos_perfil` de `_extraer_profile_data` (`:585-604`).

**Criterio:** un PATCH parcial que no envía perfil sigue funcionando; un intento de setear `unidad_organica=null` o `numero_documento=""` responde `400`.

> **Regla marcada:** la unicidad de `numero_documento`/`telefono` (RN de serializer, vía `UniqueValidator`) y la obligatoriedad final (constraint BD `NOT NULL`) — la exigencia dura vive en modelo/migración; el serializer añade mensajes en español y unicidad amistosa.

---

### CAPA 4 — Services (`apps/common/services.py`)

#### T-10 — `crear_usuario_con_perfil` (`:365-396`): exigir perfil completo y setear `tiene_ficha_usuario`

- El docstring dice "todos opcionales" (`:380`) — corregir a "todos obligatorios salvo `tiene_ficha_usuario` (default False)".
- `UserProfile.objects.create(usuario=user, **profile_data)` (`:394`): ahora `profile_data` debe traer los 7 campos obligatorios (garantizado por T-08). Si falta alguno, la constraint `NOT NULL` disparará `IntegrityError` dentro del `transaction.atomic` (`:365`) → rollback completo. Documentar este comportamiento.
- Setear `tiene_ficha_usuario` según venga en `profile_data` (default `False`).

**Criterio:** crear un usuario por el service sin los campos obligatorios lanza error controlado (400 desde serializer, o rollback atómico); con todos crea `User` + `UserSecurity` + `UserProfile` completo.

#### T-11 — `actualizar_perfil_usuario` (`:399-416`): manejar el perfil obligatorio

- `get_or_create(usuario=user)` (`:409`, `:412`): con los campos ahora `NOT NULL`, un `get_or_create` que cree un perfil vacío violaría la constraint. **Riesgo:** hoy se crea un perfil vacío si no existe. Cambiar a: si el perfil no existe, exigir que `profile_data` traiga los 7 campos obligatorios (o crear el perfil solo dentro de `crear_usuario_con_perfil`). Documentar que `actualizar_perfil_usuario` asume un perfil ya existente y completo; si no existe, `profile_data` debe estar completo.
- Permitir actualizar `tiene_ficha_usuario` vía `profile_data`.

**Criterio:** actualizar el perfil de un usuario existente con perfil completo funciona; no se crean perfiles vacíos que violen NOT NULL.

---

### CAPA 5 — RN-22 (onboarding del interno) — `apps/internados/services.py`

#### T-12 — `aprovisionar_interno` (`:291-336`): crear `UserProfile` del interno

**Impacto crítico detectado:** `aprovisionar_interno` crea `User` + `UserSecurity` + `UserEntityProfile` pero **NO crea `UserProfile`** (`apps/internados/services.py:291-336`). Al volver `perfil_usuario` obligatorio, cualquier código que lea `user.perfil` del interno fallará y, más importante, el interno quedará sin ficha.

Tarea: al crear el `User` del interno (bloque `if creado:` `:308-319`), crear también su `UserProfile` con los datos derivados del `Student`:
- `tipo_documento`: mapear `estudiante.tipo_documento` → uno de `DOCUMENT_TYPE_CHOICES` (revisar el catálogo `tipo_documento_identidad` del estudiante; si el código no mapea directo, documentar el mapeo o usar `"DNI"` cuando `len==8`).
- `numero_documento`: `estudiante.numero_documento` (único; coincide con `username`).
- `apellido_paterno` / `apellido_materno`: del `Student`.
- `telefono`: `estudiante.telefono` — **PROBLEMA:** `telefono` es `unique` y `NOT NULL` en `perfil_usuario`; si el estudiante no tiene teléfono o colisiona, hay que generar un valor placeholder único o resolver el conflicto. Documentar la estrategia (p. ej. usar el móvil del estudiante; si nulo/duplicado, generar uno sintético único o dejar `tiene_ficha_usuario=False` y bloquear hasta completar). **Decisión recomendada:** crear el perfil con `tiene_ficha_usuario=False` y los datos disponibles; si `telefono`/`unidad_organica`/`cargo` no aplican al interno, esta tarea DEBE resolver cómo satisfacer el NOT NULL (ver T-13).
- `unidad_organica` / `cargo`: un interno normalmente NO tiene unidad orgánica ni cargo ejecutivo. Con la constraint `NOT NULL`, esto obliga a una decisión de negocio (ver T-13).

**Criterio:** tras registrar un internado, el `User` del interno tiene un `UserProfile` que satisface todas las constraints `NOT NULL` + `UNIQUE`, o la tarea documenta y aplica la excepción acordada (T-13).

#### T-13 — Resolver la tensión "perfil obligatorio" vs. "usuarios sin unidad/cargo" (DECISIÓN DE NEGOCIO)

El endurecimiento a `NOT NULL` de `unidad_organica`, `cargo`, `telefono` asume que TODO usuario es un funcionario institucional. Los **internos** (RN-22) y potencialmente otros usuarios de servicio no encajan. Antes de implementar T-01/T-12, el `implement` DEBE confirmar con el usuario una de estas opciones (dejar registrado en el spec de validación):

- **Opción A (recomendada):** exceptuar del NOT NULL a `unidad_organica`/`cargo`/`telefono` para el rol `Interno`, o crear filas "placeholder" en `OrganicUnit`/`ExecutivePosition` ("No aplica / Interno") y asignarlas. `telefono` sintético único por interno.
- **Opción B:** mantener NOT NULL estricto y que el onboarding del interno rellene todos los campos con datos reales/placeholder únicos.

Este spec asume **Opción B con placeholders** salvo indicación contraria del usuario. El backfill (§3) usa la misma lógica de placeholders para los usuarios existentes.

**Criterio:** la decisión queda documentada y el onboarding del interno no rompe la constraint.

---

### CAPA 6 — Documentación

#### T-14 — Documentar `perfil_usuario` en el schema

- `docs/db_schema_modulo_01_convenios.md`: la tabla `perfil_usuario` NO está documentada allí (solo aparece `perfil_usuario_entidad`). Agregar/actualizar la ficha de la tabla `perfil_usuario` con las columnas y sus constraints finales (obligatorias + `tiene_ficha_usuario`). Si el proyecto prefiere ubicarla en un doc transversal, usar `docs/arquitectura_seguridad.md`.
- `docs/arquitectura_seguridad.md:114`: actualizar la fila de `UserProfile` — "Apellidos, DNI único **obligatorio**, teléfono único **obligatorio**, cargo **obligatorio**, unidad orgánica **obligatoria**, ficha completa (`tiene_ficha_usuario`)".
- `docs/arquitectura_seguridad.md:471-476` (tabla de constraints): actualizar `numero_documento`/`telefono` de `perfil_usuario` — ya no admiten NULL (`UNIQUE` + `NOT NULL`).
- `docs/arquitectura_seguridad.md:460-468` (onboarding del interno): agregar el paso "se crea su `UserProfile` (RN-22)".

#### T-15 — Actualizar `CLAUDE.md`

En la sección de RN-22 / seguridad, agregar que `perfil_usuario` tiene todos sus campos obligatorios + `tiene_ficha_usuario`, y que el onboarding del interno crea también el `UserProfile`.

#### T-16 — Actualizar `spec/common_perfil_usuario.md`

Anotar (nota al pie o sección "Cambios posteriores") que los campos del perfil pasaron a obligatorios y se agregó `tiene_ficha_usuario` en este spec.

---

## 3. Estrategia de migración — detalle y pseudocódigo del RunPython

### Orden de operaciones en `0009_userprofile_campos_obligatorios`

```
operations = [
    1. AddField('tiene_ficha_usuario', BooleanField(default=False))       # seguro
    2. RunPython(backfill_perfiles, migrations.RunPython.noop)            # rellena datos
    3. AlterField('tipo_documento',   blank=False, sin default)
    4. AlterField('numero_documento', null=False, unique=True)
    5. AlterField('apellido_paterno', blank=False, sin default)
    6. AlterField('apellido_materno', blank=False, sin default)
    7. AlterField('telefono',         null=False, unique=True)
    8. AlterField('unidad_organica',  null=False)
    9. AlterField('cargo',            null=False)
]
```

Los `AlterField` van DESPUÉS del `RunPython` para no violar `NOT NULL`.

### Pseudocódigo del backfill (forwards)

```python
def backfill_perfiles(apps, schema_editor):
    import random
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("common", "UserProfile")
    OrganicUnit = apps.get_model("convenios", "OrganicUnit")
    ExecutivePosition = apps.get_model("convenios", "ExecutivePosition")

    rng = random.Random(20260924)  # semilla determinista para reproducibilidad

    unidades = list(OrganicUnit.objects.values_list("pk", flat=True))
    cargos = list(ExecutivePosition.objects.values_list("pk", flat=True))
    if not unidades or not cargos:
        raise RuntimeError(
            "No hay OrganicUnit/ExecutivePosition para el backfill del perfil de usuario."
        )

    # Documentos/teléfonos ya usados para no violar UNIQUE.
    docs_usados = set(
        UserProfile.objects.exclude(numero_documento__isnull=True)
        .values_list("numero_documento", flat=True)
    )
    tels_usados = set(
        UserProfile.objects.exclude(telefono__isnull=True)
        .values_list("telefono", flat=True)
    )

    def nuevo_documento():
        while True:
            d = str(rng.randint(10_000_000, 99_999_999))  # 8 dígitos (DNI)
            if d not in docs_usados:
                docs_usados.add(d)
                return d

    def nuevo_telefono():
        while True:
            t = "9" + str(rng.randint(0, 99_999_999)).zfill(8)  # 9 dígitos, empieza en 9
            if t not in tels_usados:
                tels_usados.add(t)
                return t

    APELLIDOS = ["Quispe", "Mamani", "Flores", "Huaman", "Rojas",
                 "Vargas", "Torres", "Ramos", "Castro", "Diaz"]

    for user in User.objects.all():
        perfil = UserProfile.objects.filter(usuario=user).first()
        if perfil is None:
            # (a) crea el perfil faltante
            perfil = UserProfile(usuario=user)

        # (b) rellena SOLO los campos vacíos/nulos, preservando datos reales
        if not perfil.tipo_documento:
            perfil.tipo_documento = "DNI"
        if not perfil.numero_documento:
            perfil.numero_documento = nuevo_documento()
        if not perfil.apellido_paterno:
            perfil.apellido_paterno = user.last_name.split(" ")[0] or rng.choice(APELLIDOS)
        if not perfil.apellido_materno:
            perfil.apellido_materno = rng.choice(APELLIDOS)
        if not perfil.telefono:
            perfil.telefono = nuevo_telefono()
        if perfil.unidad_organica_id is None:
            perfil.unidad_organica_id = rng.choice(unidades)  # fila real existente
        if perfil.cargo_id is None:
            perfil.cargo_id = rng.choice(cargos)               # fila real existente
        # tiene_ficha_usuario queda en False (default) para el backfill.
        perfil.save()
```

**Notas:**
- Reverse: `migrations.RunPython.noop` (no se revierten los datos aleatorios; el reverse solo revierte los `AlterField` a nullable).
- `apps.get_model` obligatorio (modelos históricos), nunca imports de modelos vivos.
- Rellena solo campos vacíos → idempotente y preserva datos reales del perfil `usuario_id=2`.
- `numero_documento` = 8 dígitos (DNI); `telefono` = 9 dígitos empezando en 9; ambos verificados contra los sets de usados para respetar `UNIQUE`.
- `unidad_organica`/`cargo` = PK real elegido al azar de las 14/12 filas existentes (nunca inventa FKs).
- Con Users=2 y UserProfile=1: crea 1 perfil nuevo (usuario sin perfil) y completa el perfil `usuario_id=2` con documento/teléfono/unidad/cargo.

---

## 4. Comandos de entorno (los ejecuta `implement`, NUNCA `runserver`)

```powershell
# Activar entorno virtual
.venv\Scripts\Activate.ps1

# Verificar que no queden migraciones pendientes tras los cambios de modelo
python manage.py makemigrations --check --dry-run

# Generar la migración (revisar y ajustar el orden manualmente según §3)
python manage.py makemigrations common

# Aplicar contra postgres docker (datos reales)
$env:DATABASE_URL = "postgresql://renads:renads@localhost:5433/renads"
python manage.py migrate --settings=config.settings.docker
```

---

## 5. Serializers / endpoints afectados (archivo:línea)

| Ubicación | Qué cambia |
|---|---|
| `apps/common/serializers.py:244` `UserProfileReadSerializer` | Exponer `tiene_ficha_usuario` (T-06) |
| `apps/common/serializers.py:304` `UserProfileWriteSerializer` | `numero_documento`/`unidad_organica`/`cargo` → required; añadir `tiene_ficha_usuario` (T-07) |
| `apps/common/serializers.py:379` `UserCreateSerializer` | 7 campos de perfil → required; añadir `tiene_ficha_usuario` (T-08) |
| `apps/common/serializers.py:504` `UserUpdateSerializer` | quitar `allow_null`/`allow_blank`; añadir `tiene_ficha_usuario`; cuidar PATCH parcial (T-09) |
| `apps/common/serializers.py:76` `MeSerializer` (`get_perfil` `:96`) | Expone el perfil anidado → hereda `tiene_ficha_usuario` (sin cambio de código, se hereda de T-06) |
| `apps/common/serializers.py:343` `UserReadSerializer` (`perfil` `:347`) | Expone el perfil anidado → hereda `tiene_ficha_usuario` |
| `apps/common/services.py:365` `crear_usuario_con_perfil` | Docstring + `tiene_ficha_usuario` (T-10) |
| `apps/common/services.py:399` `actualizar_perfil_usuario` | `get_or_create` vacío rompe NOT NULL → ajustar (T-11) |
| `apps/internados/services.py:291` `aprovisionar_interno` | Crear `UserProfile` del interno (T-12) — **impacto crítico** |
| `apps/common/views.py:190` `UserViewSet` | Sin cambios de código; usa los serializers endurecidos |

**Endpoints impactados:**
- `POST /api/v1/users/` — ahora exige los 7 campos de perfil.
- `PUT/PATCH /api/v1/users/{id}/` — exige perfil completo en PUT; PATCH parcial preserva.
- `GET /api/v1/users/{id}/` y `GET /api/v1/auth/me/` — exponen `perfil.tiene_ficha_usuario`.
- Registro de internado (crea usuario del interno) — debe crear su `UserProfile`.

---

## 6. Impacto en RN-22 y `crear_usuario_con_perfil`

- **RN-22 (`aprovisionar_interno`):** hoy NO crea `UserProfile`. Con la constraint obligatoria, el interno queda sin ficha (y `user.perfil` inexistente rompe lecturas). T-12 corrige creando el perfil; T-13 resuelve cómo satisfacer `unidad_organica`/`cargo`/`telefono` para un interno (decisión de negocio, Opción B con placeholders por defecto).
- **`crear_usuario_con_perfil`:** el `UserProfile.objects.create(**profile_data)` requiere ahora los 7 campos; la exigencia se delega al serializer (T-08). El `transaction.atomic` garantiza rollback si falta algún campo obligatorio.
- **`actualizar_perfil_usuario`:** el patrón `get_or_create(usuario=user)` que crea un perfil vacío violaría `NOT NULL`; T-11 lo ajusta.

---

## 7. Criterios de validación (para el validator)

1. **`makemigrations --check --dry-run` limpio** tras aplicar los cambios de modelo (no hay migraciones pendientes sin generar).
2. **`migrate` OK en postgres docker** (`--settings=config.settings.docker`, `DATABASE_URL` al `localhost:5433`), sin `IntegrityError`.
3. **Ambos usuarios con perfil completo:** tras la migración, `UserProfile.objects.count() == User.objects.count()` (2 == 2); ningún perfil con `numero_documento`/`telefono`/`unidad_organica_id`/`cargo_id`/`apellido_paterno`/`apellido_materno`/`tipo_documento` en NULL o vacío.
4. **Constraints NOT NULL efectivas:** las 5 columnas (`numero_documento`, `telefono`, `unidad_organica_id`, `cargo_id`, más los char) son `NOT NULL` en el schema real de postgres; `numero_documento` y `telefono` conservan índice UNIQUE.
5. **Unicidad respetada:** no hay `numero_documento` ni `telefono` duplicados tras el backfill.
6. **`tiene_ficha_usuario`** existe como columna `boolean NOT NULL default false`; backfill lo dejó en `False`.
7. **Endpoints exponen los campos nuevos:** `GET /api/v1/auth/me/` y `GET /api/v1/users/{id}/` incluyen `perfil.tiene_ficha_usuario` y los apellidos.
8. **Endpoints exigen los obligatorios:** `POST /api/v1/users/` sin `numero_documento`/`telefono`/`unidad_organica`/`cargo`/apellidos/`tipo_documento` responde `400` con mensajes en español.
9. **RN-22 no rompe:** registrar un internado crea el `User` del interno CON `UserProfile` que satisface las constraints (según la decisión de T-13).
10. **PATCH parcial preservado:** un `PATCH /api/v1/users/{id}/` que no toca el perfil no falla por campos de perfil faltantes.
11. **Docs sincronizadas:** `docs/arquitectura_seguridad.md` y el schema reflejan la obligatoriedad + `tiene_ficha_usuario`; `CLAUDE.md` actualizado.
12. **`/code-review` ejecutado** antes de dar por cerrada la implementación (regla del proyecto).
