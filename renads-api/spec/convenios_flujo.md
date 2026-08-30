# Spec — Mejora del flujo de convenios (Marco/Específico + Adendas)

> Fuente de verdad: `C:\Users\Henry\.claude\plans\silly-drifting-squirrel.md`
> ("Mejora del flujo de convenios (Marco/Específico + Adendas)").
> Este spec traduce ese plan a tareas exactas para el agente **implement**.
> **Solo se escribe este archivo**; no se escribe código de aplicación aquí.

## Resumen del módulo

El Módulo 1 (`apps/convenios`) gestiona el ciclo de vida de Convenios Marco y
Específicos en una **tabla única** `convenio` (`Convention`), con una máquina de 26
estados (`ConventionStatus`), partes/firmas polimórficas, opiniones DIGEP/CONAPRES/OGAJ,
y campos clínicos (`ClinicalFieldRegistration` / `ClinicalFieldAllocation`). Esta mejora
añade cinco piezas del negocio real, manteniendo el flujo unificado para no perder
trazabilidad:

1. **Adendas de ampliación sin límite** — fila `convenio` encadenada por self-FK
   `convenio_origen` (apunta a Marco o Específico), con nuevo periodo de vigencia.
2. **Partes tipadas del Convenio Específico** — FKs explícitas `unidad_ejecutora`
   (`ExecutingUnit`) y `facultad` (`Faculty`, de la universidad del Marco).
3. **Resolución CONAPRES** de campos clínicos — `numero_resolucion_conapres` +
   `fecha_resolucion_conapres` en `campo_clinico_ipress`.
4. **Resoluciones PDF** enganchadas al sistema de anexos existente (`documento_anexo`
   catálogo + `documento_adjunto` versionado, `AnnexAttachmentMixin`).
5. **Endpoints/serializers** que exponen los nuevos campos, la cadena de adendas, la
   vigencia efectiva y la acción `conventions/{id}/adenda`.

### Entidades que cubre

`Convention` (tabla `convenio`), `ClinicalFieldRegistration` (tabla
`campo_clinico_ipress`), `AnnexDocument` (tabla `documento_anexo`, app `internados`),
`Document` (tabla `documento_adjunto`). Referencias a `ExecutingUnit` (`unidad_ejecutora`),
`Faculty` (`facultad`), `Ipress` (`ipress`, sede docente), `University`.

### Estado real del código (verificado)

- Última migración `apps/convenios`: **`0024_executing_unit_gobierno_regional`** → la nueva
  migración de modelos será **`0025`**.
- Última migración `apps/internados`: **`0018_annexdocument_documento_anexo`** → las nuevas
  serán **`0019`** (AlterField ANNEX_ACTOR) y **`0020`** (seed resoluciones); pueden ir en
  una sola migración `0019` con `AlterField` + `RunPython` (ver Tarea 8, punto de decisión D3).
- `Convention` (`apps/convenios/models.py:738`) ya tiene `convenio_marco` self-FK,
  `universidad`, `organo_directorio`, `estado_actual`, `max_campos_clinicos`, solicitante
  polimórfico. **No** tiene `convenio_origen`, `es_adenda`, `unidad_ejecutora`, `facultad`.
- `ClinicalFieldRegistration` (`apps/convenios/models.py:893`). **No** tiene los campos de
  resolución CONAPRES.
- `ANNEX_ACTOR` (`apps/internados/models.py:69`) tiene: `INTERNO`, `AUTORIDAD_UNIVERSIDAD`,
  `REPRESENTANTE`. **No** tiene `CONVENIO` ni `CAMPO_CLINICO`.
- `AnnexAttachmentMixin` (`apps/convenios/mixins.py:133`) valida `anexo.tipo_actor ==
  self.annex_actor`; ya reusa `adjuntar_documento` (versionado por `(objeto,
  documento_anexo)`). **Nota importante:** su docstring y el de `AnnexUploadSerializer`
  todavía nombran `AUTORIDAD_UNIVERSIDAD`/`documentos_anexos` — no romper; solo ampliar.
- `ConventionViewSet` (`apps/convenios/views.py:59`) es un `ModelViewSet` propio (NO se crea
  con `_entity_viewset`), con `permission_classes = [IsAuthenticated, IsInstitutionalMember,
  ConventionScope, IsModuleEnabled]`. Para las acciones annex habrá que **añadir
  `AnnexAttachmentMixin` a sus bases directamente** y fijar `annex_actor = "CONVENIO"`.
- Estados relevantes ya sembrados (`0002_seed_catalogos.py`):
  `SOLICITUD_REGISTRADA`(1), `VALIDADO_TECNICAMENTE`(6), `CONAPRES_FAVORABLE`(8),
  `CAMPOS_CLINICOS_DEFINIDOS`(10), `ENVIADO_SG`(14), `FIRMADO_MINSA`(16), `SUSCRITO`(19),
  `PUBLICADO`(20), `VIGENTE`(21), `AMPLIADO`(24). **No se crean estados nuevos.**
- `ESTADOS_VIGENTES = {"VIGENTE", "PUBLICADO", "SUSCRITO"}` (`services.py:33`).

---

## Puntos de decisión que el validator debe confirmar

> El agente **implement** debe implementar la opción recomendada y **dejar comentario TODO**
> señalando la decisión; el **validator** confirma o corrige.

- **D1 — ¿En qué transición se aplica `_exigir_campos_clinicos_conapres`?**
  El plan (línea 43) dice "antes de avanzar a suscripción". El único punto de escritura de
  firma es `services.registrar_firma` (`services.py:399`), que setea `FIRMADO_MINSA` /
  `FIRMADO_EXTERNOS`. No existe hoy un service que setee `ENVIADO_SG` (esa transición solo
  se puede alcanzar vía la acción genérica `conventions/{id}/cambiar-estado` →
  `services.cambiar_estado` → `_set_estado`).
  **Recomendación (implement):** aplicar el gate dentro de `registrar_firma`, **solo para
  Específicos** (`convenio.tipo_convenio.codigo == "ESPECIFICO"`), antes de crear la firma —
  es el primer punto de escritura de suscripción con service dedicado. Adicionalmente,
  invocarlo en `cambiar_estado` cuando `nuevo_estado_codigo == "ENVIADO_SG"` y el convenio
  sea Específico. Ver Tarea 6 para el detalle. El validator confirma el/los punto(s) exacto(s).

- **D2 — ¿RESOL_CONAPRES se adjunta al `convenio` o al `campo_clinico_ipress`?**
  El plan (líneas 57, 59) lo deja abierto ("a `campo_clinico_ipress` o al `convenio`, según
  actor elegido"). Instrumentar `ClinicalFieldRegistrationViewSet` con `AnnexAttachmentMixin`
  exige `annex_actor` distinto (`CAMPO_CLINICO`) y un actor propio en el catálogo.
  **Recomendación (implement):** el número/fecha de la resolución CONAPRES viven como
  **columnas** en `campo_clinico_ipress` (Tarea 3, obligatorio por el plan); el **PDF**
  `RESOL_CONAPRES` se adjunta al **registro de campo clínico** con `tipo_actor="CAMPO_CLINICO"`
  instrumentando `ClinicalFieldRegistrationViewSet` con `AnnexAttachmentMixin`
  (`annex_actor="CAMPO_CLINICO"`). Las resoluciones `RESOL_MARCO`/`RESOL_ESPECIFICO`/
  `RESOL_ADENDA` (`tipo_actor="CONVENIO"`) se adjuntan al **convenio**. Si el validator
  prefiere colgar todo del convenio, entonces `RESOL_CONAPRES` pasa a `tipo_actor="CONVENIO"`
  y no se instrumenta el ViewSet de registro (más simple; menos preciso). **Marcar TODO.**

- **D3 — Migraciones internados: ¿una o dos?** `AlterField` de `ANNEX_ACTOR` + `RunPython`
  seed pueden convivir en `0019` (patrón: la app ya combina AlterField y seed en migraciones
  separadas — ver `0010`+`0011`). **Recomendación:** una sola `0019_annex_actor_convenio_seed`
  con `AlterField` seguido de `RunPython`. El validator confirma.

- **D4 — Herencia de `unidad_ejecutora`/`facultad` en la adenda de un Marco.** Un Marco no
  tiene `unidad_ejecutora`/`facultad` (deben ser nulos, Tarea 5). Una adenda de un Marco
  hereda ambos como `None` (correcto). Una adenda de un Específico los hereda del origen.
  Confirmar que `crear_adenda` no valida partes "de Específico" cuando el origen es Marco.

- **D5 — Validación de partes en `actualizar_convenio` con PATCH parcial.** Hoy
  `actualizar_convenio` (`services.py:172`) solo aplica los campos presentes en `datos`.
  Al añadir la validación de partes por tipo hay que decidir si se revalida siempre contra
  el estado resultante del objeto (recomendado) o solo si los campos vienen en el payload.
  **Recomendación:** validar contra el estado final del objeto (leer del objeto, no del
  payload) para no permitir estados incoherentes vía PATCH. El validator confirma.

---

## Tareas (ordenadas por dependencia)

### FASE A — Modelos

#### Tarea 1 — `Convention`: campos de adenda + partes del Específico
- **Archivo:** `apps/convenios/models.py` — clase `Convention` (a partir de la línea 738;
  añadir tras `convenio_marco`, líneas 743–747, y tras `universidad`, líneas 767–771).
- **Acción:** añadir cuatro campos, **todos nullable/con default** (migración segura):
  - `convenio_origen = models.ForeignKey("self", on_delete=models.PROTECT,
    db_column="convenio_origen_id", null=True, blank=True, related_name="adendas",
    help_text="Convenio (Marco o Específico) que esta adenda amplía")`
  - `es_adenda = models.BooleanField("es adenda", default=False, help_text="Marca la fila
    como adenda de ampliación (derivable de convenio_origen; explícito para filtros)")`
  - `unidad_ejecutora = models.ForeignKey(ExecutingUnit, on_delete=models.PROTECT,
    db_column="unidad_ejecutora_id", null=True, blank=True, related_name="convenios",
    help_text="Unidad ejecutora parte del Convenio Específico")`
  - `facultad = models.ForeignKey(Faculty, on_delete=models.PROTECT,
    db_column="facultad_id", null=True, blank=True, related_name="convenios",
    help_text="Facultad (de la universidad del Marco) parte del Convenio Específico")`
- **Ubicación de las clases referenciadas:** `ExecutingUnit` (`models.py:350`), `Faculty`
  (`models.py:608`) — ya definidas antes de `Convention`, no hay problema de orden.
- **Criterio de aceptación:** el modelo importa sin errores; `related_name="adendas"`,
  `related_name="convenios"` no colisionan (verificar: `ExecutingUnit`/`Faculty` no tienen
  ya un `related_name="convenios"` — `OrganDirectory.convenios` y `University.convenios`
  existen pero son de otros modelos, no colisionan por ser reverse de FKs distintas).
  `python manage.py check` limpio.
- **Riesgo:** `related_name="convenios"` en `ExecutingUnit` y `Faculty` — confirmar que no
  choca con ninguna reverse existente en esos modelos (no la hay). El `db_column` con sufijo
  `_id` sigue la convención del resto del archivo.

#### Tarea 2 — `ClinicalFieldRegistration`: resolución CONAPRES
- **Archivo:** `apps/convenios/models.py` — clase `ClinicalFieldRegistration`
  (línea 893; añadir tras `campos_clinicos_asignados`, líneas 920–927).
- **Acción:** añadir dos campos:
  - `numero_resolucion_conapres = models.CharField("número de resolución CONAPRES",
    max_length=100, blank=True, help_text="Número de la resolución CONAPRES que autoriza los
    campos clínicos de la sede")`
  - `fecha_resolucion_conapres = models.DateField("fecha de resolución CONAPRES", null=True,
    blank=True, help_text="Fecha de la resolución CONAPRES")`
- **Criterio de aceptación:** `python manage.py check` limpio; ambos campos opcionales.
- **Riesgo:** ninguno (campos opcionales, sin unicidad).

### FASE B — Migraciones (modelos)

#### Tarea 3 — Migración `0025` de `apps/convenios`
- **Archivo (crear):** `apps/convenios/migrations/0025_convention_adenda_partes_resol_conapres.py`
- **Dependencia:** `("convenios", "0024_executing_unit_gobierno_regional")`.
- **Acción:** `migrations.AddField` ×6:
  - `Convention.convenio_origen`, `Convention.es_adenda`, `Convention.unidad_ejecutora`,
    `Convention.facultad` (Tarea 1).
  - `ClinicalFieldRegistration.numero_resolucion_conapres`,
    `ClinicalFieldRegistration.fecha_resolucion_conapres` (Tarea 2).
- **Criterio de aceptación:** `python manage.py makemigrations --check --dry-run` limpio tras
  crearla; `python manage.py migrate` sin error sobre datos existentes (todos los campos
  nullable/default → sin transferencia de datos).
- **Riesgo:** generar la migración con `makemigrations` (no a mano) para capturar los
  `db_column`/`on_delete` exactos; renombrar el archivo al nombre indicado y verificar la
  dependencia.

### FASE C — Services

#### Tarea 4 — `crear_adenda` (nuevo caso de uso)
- **Archivo:** `apps/convenios/services.py` (añadir tras `crear_convenio`, línea 169; y tras
  la validación de partes de Tarea 5 si comparte helper).
- **Acción:** implementar
  `crear_adenda(*, convenio_origen: Convention, datos: dict, usuario) -> Convention`:
  1. Exigir nuevo periodo: `fecha_inicio` obligatorio; si falta `fecha_fin` y el tipo tiene
     `anios_vigencia`, derivarla con `_sumar_anios` (mismo patrón que `crear_convenio`,
     líneas 142–145). Validar `fecha_fin > fecha_inicio`.
  2. Crear fila `Convention` con: `es_adenda=True`, `convenio_origen=convenio_origen`,
     **heredando del origen** `tipo_convenio`, `convenio_marco`, `universidad`,
     `organo_directorio`, `unidad_ejecutora`, `facultad`, `solicitante_tipo_contenido`,
     `solicitante_id_objeto`; `titulo`/`codigo` desde `datos` (permitir override; default =
     título del origen + sufijo "(Adenda)"); `estado_actual = _obtener_estado(
     "SOLICITUD_REGISTRADA")`; `fecha_solicitud` desde `datos` (default hoy); `creado_por=usuario`.
  3. Crear `ConventionStatusHistory` inicial (patrón líneas 165–167).
  4. `registrar_auditoria(usuario, "CREAR", convenio)`.
  5. **Sin límite de encadenamiento** — no validar profundidad de la cadena.
  - Punto de decisión **D4**: cuando `convenio_origen.tipo_convenio.codigo == "MARCO"`,
    `unidad_ejecutora`/`facultad` heredados son `None` (correcto, no validar partes de
    Específico).
- **Criterio de aceptación:** crear una adenda de un Específico produce una fila con
  `es_adenda=True`, `convenio_origen` set, `tipo_convenio`/`unidad_ejecutora`/`facultad`
  iguales al origen, estado `SOLICITUD_REGISTRADA`, historial + auditoría presentes.
- **RN mapeada:** Cambio 2 del plan (adendas sin límite). Va en **service** (transacción +
  auditoría + historial).
- **Riesgo:** heredar el solicitante polimórfico (dos columnas); no dejar `NULL` en
  `solicitante_id_objeto`/`solicitante_tipo_contenido` (NOT NULL en el modelo).

#### Tarea 5 — Validación de partes por tipo en `crear_convenio`/`actualizar_convenio`
- **Archivo:** `apps/convenios/services.py` — `crear_convenio` (línea 113),
  `actualizar_convenio` (línea 172). Extraer helper `_validar_partes_por_tipo(convenio_o_datos)`.
- **Acción:** implementar helper reusable que valide, según `tipo_convenio.codigo`:
  - **MARCO:** `universidad` obligatoria (ya lo es por el modelo NOT NULL);
    `unidad_ejecutora` y `facultad` **deben ser nulos** → si vienen no-nulos, `ValidationError`
    `{"unidad_ejecutora": "Un Convenio Marco no lleva unidad ejecutora ni facultad."}`.
  - **ESPECIFICO:** además de la RN-3 existente (Marco vigente, `crear_convenio` líneas
    129–140, **no tocar**):
    - `unidad_ejecutora` **obligatoria** → falta ⇒ `{"unidad_ejecutora": "Requerida para un
      Convenio Específico."}`.
    - `facultad` **obligatoria** → falta ⇒ `{"facultad": "Requerida para un Convenio
      Específico."}`.
    - `facultad` debe pertenecer a la universidad del Marco:
      `facultad.universidad_id == convenio_marco.universidad_id` → si no,
      `{"facultad": "La facultad debe pertenecer a la universidad del Convenio Marco."}`.
      **Nota:** para DIRIS sin Marco (`convenio_marco is None`), validar contra
      `convenio.universidad_id` en su lugar (la universidad propia del Específico).
- **Integración:**
  - `crear_convenio`: invocar el helper tras la validación de tipo (después de la línea 140,
    antes de `Convention.objects.create`), y añadir `unidad_ejecutora`/`facultad` al
    `Convention.objects.create(...)` (leerlos de `datos.get(...)`).
  - `actualizar_convenio`: añadir `"unidad_ejecutora"`, `"facultad"`, `"convenio_origen"`,
    `"es_adenda"` a la lista `editables` (línea 175) **con criterio** — `convenio_origen`/
    `es_adenda` normalmente NO deberían editarse por PATCH (se fijan en `crear_adenda`);
    dejar **solo** `unidad_ejecutora` y `facultad` como editables, y revalidar partes contra
    el estado final del objeto (punto **D5**).
- **Criterio de aceptación:**
  - Crear Específico sin `unidad_ejecutora` o sin `facultad` → 400.
  - Crear Específico con `facultad` de otra universidad (≠ universidad del Marco) → 400.
  - Crear Marco con `unidad_ejecutora`/`facultad` no-nulos → 400.
  - Crear Marco/Específico válidos → 201.
- **RN mapeada:** Cambio 2 (partes por tipo). Va en **service**. La obligatoriedad simple
  (campo requerido según tipo) podría duplicarse como validación de serializer, pero la
  coherencia cruzada (`facultad`↔`universidad del Marco`) **debe** ir en service.
- **Riesgo:** no romper el flujo DIRIS-sin-Marco existente (líneas 131–135). El helper debe
  contemplar `convenio_marco is None`.

#### Tarea 6 — `_exigir_campos_clinicos_conapres` (gate de suscripción)  ⚠️ D1
- **Archivo:** `apps/convenios/services.py` — nuevo helper + integración en `registrar_firma`
  (línea 399) y `cambiar_estado` (línea 187).
- **Acción:** implementar
  `_exigir_campos_clinicos_conapres(convenio: Convention) -> None`:
  - Solo aplica a Específicos (`convenio.tipo_convenio.codigo == "ESPECIFICO"`); si no, return.
  - Exigir que exista **≥1** `ClinicalFieldRegistration` del convenio
    (`convenio.campos_clinicos`) tal que:
    - `ipress.es_sede_docente is True`,
    - `ipress.unidad_ejecutora_id == convenio.unidad_ejecutora_id` (la sede pertenece a la UE
      del convenio),
    - `numero_resolucion_conapres` no vacío (`.exclude(numero_resolucion_conapres="")`).
  - Si no hay ninguno → `ValidationError("No se puede avanzar a suscripción: falta al menos
    un campo clínico registrado por CONAPRES (con resolución) sobre una sede docente de la
    unidad ejecutora.")`.
- **Integración (recomendación D1):**
  - En `registrar_firma` (línea 399), **antes** de `_tiene_observaciones_pendientes`, llamar
    `_exigir_campos_clinicos_conapres(convenio)`.
  - En `cambiar_estado` (línea 187), si `nuevo_estado_codigo == "ENVIADO_SG"`, llamar el gate
    antes de `_set_estado`.
  - **Marcar TODO** referenciando el punto de decisión D1 para que el validator confirme la
    transición exacta.
- **Criterio de aceptación:** intentar firmar/avanzar a `ENVIADO_SG` un Específico sin ningún
  `campo_clinico_ipress` con resolución sobre sede docente de la UE → 400; con ≥1 registro
  válido → procede.
- **RN mapeada:** Cambio 2 del plan (requisito de campos clínicos antes de suscripción). Va
  en **service**.
- **Riesgo:** el JOIN `ipress__unidad_ejecutora` requiere `unidad_ejecutora` seteada en el
  convenio (garantizado por Tarea 5 para Específicos). No romper Marcos (early return).

#### Tarea 7 — `crear_registro_campo_clinico`: sede pertenece a la UE del convenio
- **Archivo:** `apps/convenios/services.py` — `crear_registro_campo_clinico` (línea 220).
- **Acción:** tras la validación `ipress.es_sede_docente` (líneas 227–231) y antes de crear
  el registro, añadir:
  - Si `convenio.unidad_ejecutora_id` está seteado y
    `ipress.unidad_ejecutora_id != convenio.unidad_ejecutora_id` →
    `ValidationError({"ipress": "La sede docente debe pertenecer a la unidad ejecutora del
    Convenio Específico."})`.
  - **Punto de decisión implícito:** hoy un Específico podría no tener `unidad_ejecutora`
    (datos previos a esta mejora). Recomendación: validar solo si el convenio la tiene
    (`is not None`); marcar TODO para que el validator decida si se exige siempre.
- **Criterio de aceptación:** registrar un campo clínico con una `ipress` cuya
  `unidad_ejecutora` difiere de la del convenio → 400; coincidente → 201 (y avanza a
  `CAMPOS_CLINICOS_DEFINIDOS` como hoy, línea 246, sin cambios).
- **RN mapeada:** Cambio 3 del plan. Va en **service** (misma transacción del registro).
- **Riesgo:** no alterar el avance de estado existente ni la validación de
  `max_campos_clinicos`.

#### Tarea 8 — Selector `vigencia_efectiva` + marcar origen `AMPLIADO`
- **Archivo:** `apps/convenios/selectors.py` (selector) y `apps/convenios/services.py`
  (efecto de vigencia).
- **Acción — selector** (`selectors.py`, añadir junto a `historial_convenio`, línea 48):
  - `vigencia_efectiva(convenio: Convention) -> datetime.date | None`: recorre la cadena de
    adendas (`convenio.adendas`) y devuelve la `fecha_fin` de la **última adenda vigente** de
    la cadena (estado en `services.ESTADOS_VIGENTES`, mayor `fecha_fin`); si no hay adenda
    vigente, devuelve `convenio.fecha_fin`. Considerar cadenas de 2+ niveles (adenda de
    adenda) recorriendo recursivamente por `convenio_origen`/`adendas`. Precargar con
    `prefetch_related("adendas")` donde se use.
  - **Nota:** para evitar dependencia circular selectors→services por `ESTADOS_VIGENTES`,
    definir el set en un módulo neutro o duplicar el literal en el selector con comentario;
    recomendación: importar `from apps.convenios.services import ESTADOS_VIGENTES` (services
    no importa selectors, no hay ciclo — verificado).
- **Acción — efecto de vigencia** (`services.py`): al pasar una adenda a `VIGENTE`, marcar el
  `convenio_origen` como `AMPLIADO`. Punto de enganche recomendado: envolver el paso a
  `VIGENTE` en un helper o interceptar en `cambiar_estado`/`publicar_convenio`. Como el paso
  a `VIGENTE` hoy solo se alcanza vía `cambiar_estado` (`_set_estado`), añadir en
  `cambiar_estado`: si `nuevo_estado_codigo == "VIGENTE"` y `convenio.es_adenda` y
  `convenio.convenio_origen_id`, tras `_set_estado`, llamar
  `_avanzar_estado(convenio.convenio_origen, "AMPLIADO", usuario)` — **usar `_set_estado`
  aquí NO** porque `AMPLIADO` (orden 24) es posterior a `VIGENTE` (21); usar `_set_estado`
  directo para forzar la marca, o `_avanzar_estado` si el origen aún no está en un estado
  posterior. Recomendación: `_set_estado(convenio.convenio_origen, "AMPLIADO", usuario,
  observacion="Ampliado por adenda #<id>")`. **Marcar TODO** (punto de decisión menor: si el
  origen ya está `CERRADO`/`ANULADO` no debe reactivarse — añadir guarda).
- **Criterio de aceptación:** suscribir/publicar y pasar a `VIGENTE` una adenda → su
  `convenio_origen` queda en `AMPLIADO`; `vigencia_efectiva(origen)` = `fecha_fin` de la
  adenda; cadena de 2+ adendas devuelve la fecha de la última vigente.
- **RN mapeada:** Cambio 2 (vigencia efectiva). Selector = lectura; efecto `AMPLIADO` = service.
- **Riesgo:** recursión de la cadena; guarda contra estados terminales del origen.

### FASE D — Serializers

#### Tarea 9 — `ConventionWriteSerializer`: nuevos campos de escritura
- **Archivo:** `apps/convenios/serializers.py` — `ConventionWriteSerializer` (línea 60).
- **Acción:** añadir a `Meta.fields`: `"unidad_ejecutora"`, `"facultad"`. **No** añadir
  `convenio_origen`/`es_adenda` al write serializer del CRUD (se fijan en `crear_adenda`).
  La obligatoriedad por tipo se valida en el service (Tarea 5); el serializer deja ambos
  como opcionales (`required=False`) porque para Marco deben ir nulos.
- **Criterio de aceptación:** POST/PUT `conventions/` acepta `unidad_ejecutora`/`facultad`;
  omitirlos en un Marco no falla en el serializer (falla en el service solo si vienen mal).
- **Riesgo:** no exponer campos que rompan la creación de Marcos.

#### Tarea 10 — `ConventionReadSerializer`: cadena + vigencia + detalles
- **Archivo:** `apps/convenios/serializers.py` — `ConventionReadSerializer` (línea 29).
- **Acción:** añadir a `Meta.fields` (línea 47) y como campos:
  - `es_adenda` (bool, del modelo), `convenio_origen` (id, del modelo).
  - `unidad_ejecutora` (id) + `unidad_ejecutora_detalle`
    (`SerializerMethodField` → `_detalle_fk(obj.unidad_ejecutora, "nombre", "codigo")`,
    reusar helper `_detalle_fk` línea 128).
  - `facultad` (id) + `facultad_detalle`
    (`_detalle_fk(obj.facultad, "nombre")`).
  - `adendas` (`SerializerMethodField`): lista `{id, titulo, estado_codigo, fecha_inicio,
    fecha_fin}` de `obj.adendas.all()` (cadena de adendas directas; documentar que es un
    nivel — el frontend recorre recursivamente si necesita niveles profundos, o el método
    aplana la cadena completa — **marcar TODO** para decisión del validator).
  - `vigencia_efectiva` (`SerializerMethodField` → `selectors.vigencia_efectiva(obj)`).
- **Optimización:** actualizar `selectors.convenios_visibles` (línea 23) para
  `select_related("unidad_ejecutora", "facultad", "convenio_origen")` y
  `prefetch_related("adendas")` (evitar N+1 al serializar).
- **Criterio de aceptación:** GET `conventions/{id}` devuelve `es_adenda`, `convenio_origen`,
  `unidad_ejecutora`(+detalle), `facultad`(+detalle), `adendas`, `vigencia_efectiva`.
- **Riesgo:** import de `selectors` dentro del serializer puede crear ciclo
  (serializers ← selectors ← models). Verificar: `selectors.py` importa de `models`, no de
  `serializers`; `serializers.py` no es importado por `selectors` → import seguro. Preferir
  import diferido (dentro del método) si `makemigrations`/`spectacular` se queja.

#### Tarea 11 — `ClinicalFieldRegistrationSerializer`: resolución CONAPRES
- **Archivo:** `apps/convenios/serializers.py` — `ClinicalFieldRegistrationSerializer`
  (línea 141).
- **Acción:** añadir a `Meta.fields` (línea 157): `"numero_resolucion_conapres"`,
  `"fecha_resolucion_conapres"` (ambos de escritura, opcionales). No añadir a
  `read_only_fields`.
- **Integración service:** en `crear_registro_campo_clinico` (service ya hace
  `**datos`, línea 240–242) y `actualizar_registro_campo_clinico` (añadir ambos a la lista
  `editables`, línea 259–262) — verificar que los nuevos campos fluyen.
- **Criterio de aceptación:** POST/PUT `clinical-field-registrations/` acepta y persiste
  `numero_resolucion_conapres`/`fecha_resolucion_conapres`; GET los expone.
- **Riesgo:** `crear_registro_campo_clinico` usa `**datos`; los nuevos campos deben estar en
  `validated_data` (garantizado al añadirlos a `fields`).

### FASE E — Filters

#### Tarea 12 — `ConventionFilter`: filtros de adenda
- **Archivo:** `apps/convenios/filters.py` — `ConventionFilter` (línea 13).
- **Acción:** añadir a `Meta.fields` (línea 21): `"es_adenda": ["exact"]`,
  `"convenio_origen": ["exact"]`. (`"convenio_marco": ["exact"]` ya existe, línea 24.)
- **Criterio de aceptación:** `GET /api/v1/conventions/?es_adenda=true`,
  `?convenio_origen=<id>`, `?convenio_marco=<id>` filtran correctamente.
- **Riesgo:** ninguno.

### FASE F — Mixins / Views

#### Tarea 13 — Ampliar `ANNEX_ACTOR` (modelo internados)
- **Archivo:** `apps/internados/models.py` — `ANNEX_ACTOR` (línea 69).
- **Acción:** añadir choices: `("CONVENIO", "Convenio / adenda")` y, si se aprueba D2,
  `("CAMPO_CLINICO", "Campo clínico (resolución CONAPRES)")`.
- **Criterio de aceptación:** `python manage.py check` limpio; `AnnexDocument.tipo_actor`
  acepta los nuevos valores.
- **Riesgo:** el `max_length=30` de `tipo_actor` (línea 81) cabe `CAMPO_CLINICO` (13) — OK.

#### Tarea 14 — Migración internados `0019` (AlterField + seed)  ⚠️ D3
- **Archivo (crear):** `apps/internados/migrations/0019_annex_actor_convenio_seed.py`
- **Dependencia:** `("internados", "0018_annexdocument_documento_anexo")`.
- **Acción:**
  1. `migrations.AlterField` de `annexdocument.tipo_actor` con la lista de choices ampliada
     (patrón `0010_annexdocument_tipo_actor.py`).
  2. `migrations.RunPython(seed, unseed)` sembrando en `documento_anexo` (patrón
     `0011_seed_documentos_actor.py`) los anexos de resolución:
     - `("RESOL_MARCO", "Resolución de aprobación del Convenio Marco", "...", "CONVENIO",
       obligatorio=False)`
     - `("RESOL_ESPECIFICO", "Resolución de aprobación del Convenio Específico", "...",
       "CONVENIO", obligatorio=False)`
     - `("RESOL_ADENDA", "Resolución de aprobación de la adenda", "...", "CONVENIO",
       obligatorio=False)`
     - `("RESOL_CONAPRES", "Resolución CONAPRES de campos clínicos", "...",
       "CAMPO_CLINICO", obligatorio=False)` — `tipo_actor` según **D2**.
     - Usar `update_or_create(codigo=..., defaults={...})` (idempotente); `unseed` borra por
       `codigo__in`.
- **Criterio de aceptación:** `makemigrations --check` limpio tras crearla; `migrate` crea
  los 4 `documento_anexo`; `annex-checklist` los lista para el actor correspondiente.
- **Riesgo:** `obligatorio` — se recomienda `False` para las resoluciones (no bloquear el
  flujo del MVP con adjuntos obligatorios); el validator confirma la obligatoriedad.

#### Tarea 15 — Instrumentar `ConventionViewSet` con `AnnexAttachmentMixin`
- **Archivo:** `apps/convenios/views.py` — `ConventionViewSet` (línea 59).
- **Acción:**
  - Cambiar la firma de clase a `class ConventionViewSet(AnnexAttachmentMixin,
    viewsets.ModelViewSet):` (`AnnexAttachmentMixin` ya importado, línea 19).
  - Añadir atributo `annex_actor = "CONVENIO"`.
  - Esto habilita `conventions/{id}/annex-upload` y `conventions/{id}/annex-checklist`
    reusando `adjuntar_documento` (versionado por `(convenio, documento_anexo)`).
  - Verificar que las `permission_classes` del ViewSet (línea 62) siguen aplicando a las
    acciones del mixin (el mixin no las relaja — confirmado en su docstring). Las acciones
    annex son de escritura; `IsModuleEnabled` gatea por `module_content_type` — confirmar que
    subir un anexo cuando el módulo está fuera de ventana **debe o no** bloquearse (marcar
    TODO; recomendación: permitir adjuntar anexos aunque el módulo esté fuera de ventana ⇒
    puede requerir excluir estas acciones del gate; el validator decide).
- **Criterio de aceptación:** `POST conventions/{id}/annex-upload` con `RESOL_ESPECIFICO` PDF
  crea un `documento_adjunto` versionado ligado al anexo; `annex-checklist` refleja el
  adjunto. `annex-upload` con un anexo de `tipo_actor != "CONVENIO"` → 400 (enforcement del
  mixin, `mixins.py:173`).
- **Riesgo:** el mixin importa `AnnexUploadSerializer`/`DocumentSerializer` de
  `apps.convenios.serializers` (ya existe). No romper OpenAPI (`@extend_schema` del mixin ya
  define nombres únicos por acción — pero al montar el mixin en `ConventionViewSet` **y** en
  `OrganRepresentativeViewSet` **y** posiblemente `ClinicalFieldRegistrationViewSet`, DRF-spectacular
  puede advertir por nombres de componente duplicados; verificar el schema sin errores tras
  el cambio).

#### Tarea 16 — (Condicional a D2) Instrumentar `ClinicalFieldRegistrationViewSet`
- **Archivo:** `apps/convenios/views.py` — `ClinicalFieldRegistrationViewSet` (línea 231).
- **Acción (solo si D2 = adjuntar al registro):** añadir `AnnexAttachmentMixin` a las bases
  (`class ClinicalFieldRegistrationViewSet(AnnexAttachmentMixin, AuditedModelViewSet):`) y
  `annex_actor = "CAMPO_CLINICO"`. Habilita `clinical-field-registrations/{id}/annex-upload`
  y `.../annex-checklist` para `RESOL_CONAPRES`.
- **Criterio de aceptación:** `POST clinical-field-registrations/{id}/annex-upload` con
  `RESOL_CONAPRES` PDF versiona el documento sobre el registro.
- **Riesgo:** ver Tarea 15 (posibles nombres de componente OpenAPI duplicados). Si D2 se
  resuelve como "todo cuelga del convenio", **omitir esta tarea**.

#### Tarea 17 — Acción `conventions/{id}/adenda`
- **Archivo:** `apps/convenios/views.py` — `ConventionViewSet` (añadir action tras
  `historial`, línea 180).
- **Acción:** `@action(detail=True, methods=["post"], url_path="adenda")` →
  `crear_adenda`. La vista:
  - Toma el `convenio_origen = self.get_object()`.
  - Valida el rol/alcance con el patrón existente (p. ej. `exigir_roles(request,
    "Administrador RENADS")` o el rol de la entidad solicitante — **marcar TODO** para que el
    validator fije el rol que puede crear adendas; recomendación: mismo alcance que crear un
    convenio, vía `ConventionScope`/`exigir_ambito`, no un rol fijo).
  - Deserializa el nuevo periodo/título con un serializer nuevo `AdendaWriteSerializer`
    (campos: `titulo` opcional, `codigo` opcional, `fecha_solicitud` opcional,
    `fecha_inicio` requerido, `fecha_fin` opcional). Añadir el serializer en
    `serializers.py`.
  - Llama `services.crear_adenda(convenio_origen=convenio_origen,
    datos=ser.validated_data, usuario=request.user)`.
  - Responde `201` con `ConventionReadSerializer(adenda).data` (usar `self._read`, línea 77,
    pero con status 201 → devolver `Response(ConventionReadSerializer(...).data, status=201)`).
- **Criterio de aceptación:** `POST conventions/{id}/adenda` con nuevo periodo crea la adenda
  (`es_adenda=True`, `convenio_origen=<id>`) y la devuelve serializada; sin `fecha_inicio` →
  400.
- **Riesgo:** el gate `IsModuleEnabled`/`ConventionScope` aplica a la acción (es escritura);
  confirmar que el alcance del usuario incluye la entidad del convenio origen.

### FASE G — Documentación

#### Tarea 18 — `docs/db_schema_modulo_01_convenios.md`
- **Acción:** documentar en `convenio`: `convenio_origen` (self-FK, adendas), `es_adenda`,
  `unidad_ejecutora`, `facultad` (partes del Específico); en `campo_clinico_ipress`:
  `numero_resolucion_conapres`, `fecha_resolucion_conapres`. Describir la relación UE→sedes
  docentes (`Ipress.unidad_ejecutora`), la cadena de adendas y `vigencia_efectiva`, y las
  reglas: partes por tipo, requisito de campos clínicos con resolución antes de suscripción,
  efecto `AMPLIADO`.
- **Criterio de aceptación:** el `.md` refleja el modelo final (columnas nuevas + reglas).

#### Tarea 19 — `docs/db_schema_modulo_02_internados.md` y `docs/api_almacenamiento_frontend.md`
- **Acción:** documentar los nuevos `ANNEX_ACTOR` (`CONVENIO`, `CAMPO_CLINICO`) y los
  `documento_anexo` sembrados (`RESOL_MARCO`/`RESOL_ESPECIFICO`/`RESOL_ADENDA`/`RESOL_CONAPRES`);
  en `api_almacenamiento_frontend.md`, las acciones `annex-upload`/`annex-checklist` sobre
  `conventions/` (y `clinical-field-registrations/` si D2 lo aprueba).
- **Criterio de aceptación:** los docs listan los endpoints y el catálogo actualizado.

#### Tarea 20 — `CLAUDE.md`
- **Acción:** añadir las reglas del flujo mejorado en la sección "Reglas del módulo Gestionar
  Convenios": adendas (fila `convenio` con `convenio_origen`/`es_adenda`, sin límite,
  `vigencia_efectiva`, origen → `AMPLIADO`), partes por tipo (`unidad_ejecutora`/`facultad`
  del Específico; nulos en Marco; `facultad.universidad == convenio_marco.universidad`),
  requisito de campos clínicos con resolución CONAPRES antes de suscripción, resolución
  CONAPRES en `campo_clinico_ipress`, resoluciones PDF por anexos (`tipo_actor` `CONVENIO`/
  `CAMPO_CLINICO`).
- **Criterio de aceptación:** `CLAUDE.md` describe las cuatro reglas nuevas de forma
  consistente con el resto del documento.

---

## Verificación end-to-end (checklist del implement, la corre el validator)

1. `python manage.py makemigrations --check --dry-run` limpio; `migrate`; `check` OK;
   OpenAPI/`spectacular` sin errores (`python manage.py spectacular --file schema.yml`
   o el comando del proyecto).
2. Crear Marco (GERESA) → crear Específico (con Marco vigente) con `unidad_ejecutora` +
   `facultad`; facultad de la universidad del Marco OK; facultad ajena → 400; Marco con
   `unidad_ejecutora`/`facultad` → 400.
3. Registrar `campo_clinico_ipress` con `numero_resolucion_conapres` sobre sede docente
   (`es_sede_docente=True`) de la UE del convenio; sede sin `es_sede_docente` → 400; sede de
   otra UE → 400; avanzar el Específico a suscripción **sin** campo clínico con resolución →
   bloqueado (400).
4. Crear adenda (`POST conventions/{id}/adenda`) de un Específico con nuevo periodo → fila
   `es_adenda=True`, `convenio_origen` set, hereda tipo/UE/facultad; pasar la adenda a
   `VIGENTE` → origen `AMPLIADO`; `vigencia_efectiva(origen)` = fin de la adenda.
5. Cadena de 2+ adendas (adenda de adenda) → sin límite; lectura del convenio expone
   `adendas` y `vigencia_efectiva`.
6. `POST conventions/{id}/annex-upload` (RESOL_ESPECIFICO PDF) → `documento_adjunto`
   versionado por `(convenio, documento_anexo)`; `annex-checklist` lo refleja; anexo de otro
   `tipo_actor` → 400.
7. `GET conventions/?es_adenda=true` y `?convenio_origen=<id>` filtran; el serializer expone
   `unidad_ejecutora_detalle`/`facultad_detalle`.

## Cierre (según CLAUDE.md)

`/code-review` sobre modelos/migraciones/serializers/views/services; `/fix-types` para mypy.
No cerrar el módulo sin `spec/convenios_flujo.validacion.md` sin errores del agente
`validator`.
