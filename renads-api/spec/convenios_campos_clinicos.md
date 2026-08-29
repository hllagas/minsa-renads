# Spec — Campos clínicos: Registro (CONAPRES) y Asignación (Órgano Regional)

> Fuente del diseño: `C:\Users\Henry\.claude\plans\silly-drifting-squirrel.md` (plan aprobado — no reabrir decisiones).
> Fuentes de verdad: `docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_modulo_02_internados.md`, `docs/db_schema_er_global.md`, `docs/arquitectura_desarrollo.md`, `CLAUDE.md`.

## 1. Resumen del módulo

Se separa la responsabilidad hoy mezclada en la tabla `campo_clinico` (`ClinicalField`, `apps/convenios/models.py:786`) en **dos sub-módulos STANDALONE** (patrón `students`/`tutors` de Internados, no anidados):

- **(a) `ClinicalFieldRegistration`** — tabla `campo_clinico_ipress` (REFACTOR de `campo_clinico`). Registra el **total** de campos clínicos por **sede docente (IPRESS) + carrera profesional** (+ especialidad opcional). Escritura del rol **CONAPRES**.
- **(b) `ClinicalFieldAllocation`** — tabla `campo_clinico_ipress_universidad` (NUEVA). **Asigna** cupos por **universidad** contra un registro (a). Escritura del rol **Órgano Regional** (grupo `Gobierno Regional`).

**Entidades cubiertas:** `ClinicalFieldRegistration` (a), `ClinicalFieldAllocation` (b). Impacto en `Internship` (`apps/internados`), que pasa a referenciar la asignación (b).

**Reglas de negocio involucradas:**
- Registro (a): la IPRESS debe ser sede docente (`es_sede_docente=True`).
- Asignación (b): disponibilidad = `registro.campos_clinicos_registrados − Σ autorizados de otras asignaciones del mismo registro`; convenio Específico + estado vigente; `convenio.universidad == asignacion.universidad`; coherencia de `ipress`/`carrera_profesional` con el registro padre.
- Acumulador: `registro.campos_clinicos_asignados` = Σ de las asignaciones, recalculado tras cada create/update/delete de (b).
- Internados RN-13 se recalibra sobre `campos_clinicos_autorizados` de la asignación (nueva RN-25 del repunte).

**Convenciones de idioma:** código/identificadores en inglés; nombres de tablas, columnas, `help_text`, docstrings, mensajes de error al usuario y `.md` en español (ver `CLAUDE.md`).

> Nota de estado del repositorio (verificado): la última migración de convenios es `0014`, por lo que la nueva es **`0015`**. La última de internados es `0016_remove_student_anio_academico`, por lo que la nueva es **`0017`** (el plan la nombra "0007", desactualizado: usar `0017`).

---

## 2. Tareas — Models (`apps/convenios/models.py`)

### T-M1 — Refactor `ClinicalField` → `ClinicalFieldRegistration` (tabla `campo_clinico_ipress`)
Renombrar la clase `ClinicalField` (línea ~786) a `ClinicalFieldRegistration` y dejar los campos exactamente así:
- `convenio` — FK→`Convention`, `on_delete=CASCADE`, `db_column="convenio_id"`, `related_name="campos_clinicos"` (se conserva).
- `ipress` — FK→`Ipress`, `on_delete=PROTECT`, `db_column="ipress_id"`.
- `carrera_profesional` — FK→`ProfessionalCareer`, `on_delete=PROTECT`, `db_column="carrera_profesional_id"`.
- `especialidad` — FK→`Specialty`, `on_delete=SET_NULL`, `db_column="especialidad_id"`, `null=True`, `blank=True`, `related_name="+"`.
- `campos_clinicos_registrados` — `PositiveIntegerField` (RENOMBRA `cantidad_maxima`). `verbose_name`/`help_text` en español.
- `campos_clinicos_asignados` — `PositiveIntegerField`, `default=0`, help_text que indique que es acumulador Σ de las asignaciones (recalculado por service; read-only en API).
- Auditoría: `creado_en` (`auto_now_add=True`), `creado_por` (FK→`settings.AUTH_USER_MODEL`, `null=True`, `blank=True`, `related_name="+"`, `on_delete=SET_NULL` o `PROTECT` según patrón; usar `SET_NULL` con `null=True`), `actualizado_en` (`auto_now=True`), `actualizado_por` (FK user, `null=True`, `blank=True`, `related_name="+"`).
- `Meta.db_table = "campo_clinico_ipress"`, `verbose_name = "registro de campos clínicos por sede"`, y `unique_together = (("convenio", "ipress", "carrera_profesional", "especialidad"),)`.
- ELIMINAR los campos: `vigencia_inicio`, `vigencia_fin`, `ambito_geografico_sanitario`, `observaciones`.

**Criterios de aceptación:**
- La clase se llama `ClinicalFieldRegistration`; `Meta.db_table == "campo_clinico_ipress"`.
- Existe `campos_clinicos_registrados` y NO existe `cantidad_maxima`, `vigencia_inicio`, `vigencia_fin`, `ambito_geografico_sanitario`, `observaciones`.
- `campos_clinicos_asignados` tiene `default=0`.
- `unique_together` es exactamente `(convenio, ipress, carrera_profesional, especialidad)`.
- `python manage.py check` sin errores.

### T-M2 — Nuevo modelo `ClinicalFieldAllocation` (tabla `campo_clinico_ipress_universidad`)
Crear la clase con estos campos:
- `campo_clinico_ipress` — FK→`ClinicalFieldRegistration`, `on_delete=PROTECT`, `db_column="campo_clinico_ipress_id"`, `related_name="asignaciones"`.
- `convenio` — FK→`Convention`, `on_delete=PROTECT`, `db_column="convenio_id"`, `related_name="+"` (o nombre no colisionante).
- `ipress` — FK→`Ipress`, `on_delete=PROTECT`, `db_column="ipress_id"`.
- `carrera_profesional` — FK→`ProfessionalCareer`, `on_delete=PROTECT`, `db_column="carrera_profesional_id"`.
- `especialidad` — FK→`Specialty`, `on_delete=SET_NULL`, `db_column="especialidad_id"`, `null=True`, `blank=True`, `related_name="+"`.
- `universidad` — FK→`University`, `on_delete=PROTECT`, `db_column="universidad_id"`, `related_name="campos_clinicos_asignados"`.
- `fecha_inicio` — `DateField`.
- `fecha_fin` — `DateField`.
- `campos_clinicos_autorizados` — `PositiveIntegerField`.
- Auditoría: `creado_en`/`creado_por`/`actualizado_en`/`actualizado_por` (mismo patrón que T-M1).
- `Meta.db_table = "campo_clinico_ipress_universidad"`, `verbose_name = "asignación de campos clínicos por universidad"`, `unique_together = (("campo_clinico_ipress", "universidad", "convenio"),)`.

**Criterios de aceptación:**
- La clase se llama `ClinicalFieldAllocation`; `Meta.db_table == "campo_clinico_ipress_universidad"`.
- FK `campo_clinico_ipress` con `related_name="asignaciones"`; FK `universidad` con `related_name="campos_clinicos_asignados"`.
- `unique_together` es exactamente `(campo_clinico_ipress, universidad, convenio)`.
- `python manage.py check` sin errores.

---

## 3. Tareas — Services (`apps/convenios/services.py`)

> Todas las funciones corren en `transaction.atomic()`, registran auditoría con `registrar_auditoria(...)` y lanzan `rest_framework.exceptions.ValidationError` con mensajes en español para reglas violadas. Reusar `ESTADOS_VIGENTES` y `_exigir_especifico` existentes.

### T-S1 — `crear_registro_campo_clinico` (CONAPRES) [RN — sede docente]
Firma sugerida: `crear_registro_campo_clinico(*, datos: dict, usuario) -> ClinicalFieldRegistration`.
- Validar `datos["ipress"].es_sede_docente` (reusar patrón de `definir_campo_clinico:200`); si no, `ValidationError({"ipress": "La IPRESS debe estar autorizada como sede docente por CONAPRES."})`.
- (Opcional, conservar) si `convenio.max_campos_clinicos is not None` validar que `campos_clinicos_registrados` no lo exceda (equivalente al chequeo actual sobre `cantidad_maxima`).
- Crear el registro con `creado_por=usuario`, `campos_clinicos_asignados=0`.
- `registrar_auditoria(usuario, "CREAR", registro)`.

**Nota RN (dónde vive cada validación):**
- `es_sede_docente` y tope `max_campos_clinicos` → **service** (regla de negocio).
- Presencia/tipo de campos requeridos → **serializer**.

**Criterios de aceptación:**
- IPRESS sin `es_sede_docente=True` produce `ValidationError` con clave `ipress`.
- Se crea la fila con `campos_clinicos_asignados == 0` y `creado_por` = usuario.
- Se registra auditoría `CREAR`.

### T-S2 — `actualizar_registro_campo_clinico` (CONAPRES)
Firma: `actualizar_registro_campo_clinico(*, registro, datos: dict, usuario) -> ClinicalFieldRegistration`.
- Aplicar campos editables (`campos_clinicos_registrados`, `carrera_profesional`, `especialidad`, `ipress`, ...); NO permitir editar `campos_clinicos_asignados` (lo maneja el acumulador).
- Revalidar `es_sede_docente` si cambia la IPRESS.
- Regla de integridad: `campos_clinicos_registrados` no puede quedar por debajo de `campos_clinicos_asignados` actual → `ValidationError({"campos_clinicos_registrados": "No puede ser menor que los campos ya asignados a universidades."})`.
- Setear `actualizado_por=usuario`; `registrar_auditoria(usuario, "ACTUALIZAR", registro)`.

**Criterios de aceptación:**
- Bajar `campos_clinicos_registrados` por debajo de `campos_clinicos_asignados` da `ValidationError`.
- `campos_clinicos_asignados` no es editable desde este service.
- Se registra auditoría `ACTUALIZAR`.

### T-S3 — Helper privado `_recalcular_asignados(registro)` [Acumulador — fuente única]
- Recalcula `registro.campos_clinicos_asignados = Σ registro.asignaciones.campos_clinicos_autorizados` (agregación `Sum`, `or 0`).
- Guarda con `update_fields=["campos_clinicos_asignados", "actualizado_en"]`.
- Debe invocarse dentro de la misma transacción de create/update/delete de asignaciones.

**Criterios de aceptación:**
- Tras aplicarse, `registro.campos_clinicos_asignados` == suma exacta de `campos_clinicos_autorizados` de sus asignaciones.
- Es la ÚNICA función que escribe `campos_clinicos_asignados`.

### T-S4 — `crear_asignacion_campo_clinico` (Órgano Regional) [RN — disponibilidad + convenio vigente]
Firma: `crear_asignacion_campo_clinico(*, datos: dict, usuario) -> ClinicalFieldAllocation`.
- Tomar `registro = datos["campo_clinico_ipress"]` y bloquear con `ClinicalFieldRegistration.objects.select_for_update().get(pk=registro.pk)`.
- Validar convenio Específico + vigente: `_exigir_especifico(convenio, "La asignación de campos clínicos")` y `convenio.estado_actual.codigo in ESTADOS_VIGENTES` (si no, `ValidationError({"convenio": "El Convenio Específico debe estar vigente."})`).
- Validar `convenio.universidad_id == datos["universidad"].id` → si no, `ValidationError({"universidad": "La universidad debe coincidir con la del convenio."})`.
- Validar coherencia con el registro padre: `datos["ipress"].id == registro.ipress_id` y `datos["carrera_profesional"].id == registro.carrera_profesional_id` (y especialidad si aplica) → si no, `ValidationError` con la clave correspondiente y mensaje en español.
- **Disponibilidad:** `disponible = registro.campos_clinicos_registrados − (Σ campos_clinicos_autorizados de OTRAS asignaciones del registro)`. Si `datos["campos_clinicos_autorizados"] > disponible` → `ValidationError({"campos_clinicos_autorizados": "Excede los campos clínicos disponibles del registro."})`.
- Crear la asignación con `creado_por=usuario`.
- `_recalcular_asignados(registro)`.
- `registrar_auditoria(usuario, "CREAR", asignacion)`.

**Criterios de aceptación:**
- Con `registrados=10` y una asignación previa de 6, crear una de 4 pasa; una de 5 da `ValidationError` con clave `campos_clinicos_autorizados`.
- Convenio no Específico o no vigente → `ValidationError`.
- `convenio.universidad != universidad` → `ValidationError` con clave `universidad`.
- `ipress`/`carrera_profesional` distintos del registro padre → `ValidationError`.
- Tras crear, `registro.campos_clinicos_asignados` refleja el nuevo total.
- Usa `select_for_update` sobre el registro.

### T-S5 — `actualizar_asignacion_campo_clinico` (Órgano Regional)
Firma: `actualizar_asignacion_campo_clinico(*, asignacion, datos: dict, usuario) -> ClinicalFieldAllocation`.
- `select_for_update` sobre el registro padre.
- Recalcular disponibilidad EXCLUYENDO la propia asignación (`Σ de otras`), con las mismas validaciones que T-S4 aplicables a los campos editables (`campos_clinicos_autorizados`, `fecha_inicio`, `fecha_fin`).
- Setear `actualizado_por=usuario`; `_recalcular_asignados(registro)`; `registrar_auditoria(usuario, "ACTUALIZAR", asignacion)`.

**Criterios de aceptación:**
- Subir `campos_clinicos_autorizados` respetando disponibilidad (excluyendo la propia) pasa; excederla da `ValidationError`.
- `registro.campos_clinicos_asignados` queda recalculado.

### T-S6 — `eliminar_asignacion_campo_clinico` (Órgano Regional)
Firma: `eliminar_asignacion_campo_clinico(*, asignacion, usuario) -> None`.
- Si tiene internados referenciándola (`asignacion.internos.exists()` según `related_name`), no borrar: dejar que el `PROTECT` de Internship lo impida y que la vista lo traduzca a 409, o validar explícitamente con mensaje en español.
- Guardar referencia al registro padre; borrar; `_recalcular_asignados(registro)`; `registrar_auditoria(usuario, "ELIMINAR", asignacion)`.

**Criterios de aceptación:**
- Tras eliminar, `registro.campos_clinicos_asignados` se recalcula.
- Eliminar una asignación con internados asociados no corrompe datos (queda protegida vía FK PROTECT / 409).
- Se registra auditoría `ELIMINAR`.

### T-S7 — Retirar `definir_campo_clinico`
- Eliminar la función `definir_campo_clinico` (`services.py:198`) y su import/uso.
- No debe quedar referencia a `ClinicalField` (nombre viejo) en `services.py`; actualizar el import a `ClinicalFieldRegistration` y `ClinicalFieldAllocation`.

**Criterios de aceptación:**
- `grep "definir_campo_clinico"` no arroja resultados en `apps/convenios`.
- `grep "ClinicalField\b"` (nombre exacto viejo) no arroja resultados fuera de migraciones.

---

## 4. Tareas — Selectors (`apps/convenios/selectors.py`)

### T-SEL1 — Retirar `campos_clinicos_de`
Eliminar la función `campos_clinicos_de` (`selectors.py:54`), que referencia `ambito_geografico_sanitario` (columna eliminada) y el modelo viejo.

**Criterios de aceptación:** la función ya no existe; no hay referencias a ella.

### T-SEL2 — Selectors de lectura para (a) y (b)
Añadir:
- `registros_campo_clinico()` → `ClinicalFieldRegistration.objects.select_related("convenio", "ipress", "carrera_profesional", "especialidad")`.
- `asignaciones_campo_clinico()` → `ClinicalFieldAllocation.objects.select_related("campo_clinico_ipress", "convenio", "ipress", "carrera_profesional", "especialidad", "universidad")`.
- Actualizar el import del módulo a `ClinicalFieldRegistration`/`ClinicalFieldAllocation`.

**Criterios de aceptación:**
- Ambos selectors devuelven QuerySets con `select_related` que evita N+1 al serializar detalles.
- No hay import de `ClinicalField` (nombre viejo).

---

## 5. Tareas — Serializers (`apps/convenios/serializers.py`)

### T-SER1 — Reemplazar `ClinicalFieldSerializer`
Eliminar el serializer viejo (línea ~131, con campos `cantidad_maxima`, `vigencia_*`, `ambito_geografico_sanitario`, `observaciones`) y su import.

**Criterios de aceptación:** no queda `ClinicalFieldSerializer` ni referencias a los campos eliminados.

### T-SER2 — `ClinicalFieldRegistrationSerializer`
- Campos de escritura: `convenio`, `ipress`, `carrera_profesional`, `especialidad`, `campos_clinicos_registrados`.
- Campos read-only: `id`, `campos_clinicos_asignados`, `creado_en`, `actualizado_en`, `creado_por`, `actualizado_por`.
- Campo computado read-only `disponibilidad` (`SerializerMethodField`) = `campos_clinicos_registrados − campos_clinicos_asignados`.
- Validaciones de serializer: presencia/tipo de campos obligatorios; `campos_clinicos_registrados` positivo. Las reglas de negocio (sede docente, tope de convenio) van en el service.

**Criterios de aceptación:**
- La respuesta incluye `campos_clinicos_registrados`, `campos_clinicos_asignados` (read-only), `disponibilidad`.
- Enviar `campos_clinicos_asignados` en el body no lo altera.

### T-SER3 — `ClinicalFieldAllocationSerializer`
- Campos de escritura: `campo_clinico_ipress`, `convenio`, `ipress`, `carrera_profesional`, `especialidad`, `universidad`, `fecha_inicio`, `fecha_fin`, `campos_clinicos_autorizados`.
- Read-only: `id`, `creado_en`, `actualizado_en`, `creado_por`, `actualizado_por`.
- Validación de serializer: `fecha_fin >= fecha_inicio` (mensaje en español). El resto (disponibilidad, coherencia con registro, convenio vigente) en el service.

**Criterios de aceptación:**
- `fecha_fin < fecha_inicio` da error de validación con mensaje en español.
- Todos los campos del schema (b) presentes.

---

## 6. Tareas — Permissions (`apps/convenios/permissions.py`)

### T-P1 — `IsConapresOrReadOnly`
Espejo de `IsAdminRoleOrReadOnly`: lectura para autenticados; escritura solo superusuario o grupo `CONAPRES`.
- `message = "La escritura requiere el rol CONAPRES."`

**Criterios de aceptación:** GET permitido a autenticados; POST/PUT/PATCH/DELETE solo superuser o grupo `CONAPRES`.

### T-P2 — `IsRegionalOrganOrReadOnly`
Espejo: lectura para autenticados; escritura solo superusuario o grupo `Gobierno Regional`.
- `message = "La escritura requiere el rol Gobierno Regional."`
- Constante de nombre de grupo (`ROL_GOBIERNO_REGIONAL = "Gobierno Regional"`), coherente con `exigir_roles`.

**Criterios de aceptación:** escritura restringida al grupo `Gobierno Regional` (o superuser); lectura libre para autenticados.

---

## 7. Tareas — Filters (`apps/convenios/filters.py`)

### T-F1 — Reemplazar `ClinicalFieldFilter`
- Eliminar `ClinicalFieldFilter` (referencia `ambito_geografico_sanitario`, ya inexistente) y su import.
- Añadir `ClinicalFieldRegistrationFilter` con `fields = {convenio, ipress, carrera_profesional, especialidad}` (todos `["exact"]`).
- Añadir `ClinicalFieldAllocationFilter` con `fields = {campo_clinico_ipress, convenio, ipress, carrera_profesional, universidad}` (todos `["exact"]`).

**Criterios de aceptación:**
- No queda `ClinicalFieldFilter` ni referencia a `ambito_geografico_sanitario`.
- Los dos nuevos filtersets importan los modelos nuevos y compilan (`manage.py check`).

---

## 8. Tareas — ViewSets y router (`apps/convenios/views.py`, `apps/convenios/urls.py`)

### T-V1 — Retirar la action anidada `campos_clinicos`
Eliminar `ConventionViewSet.campos_clinicos` (`views.py:130-141`) y quitar el import de `ClinicalFieldSerializer`.

**Criterios de aceptación:** el endpoint `conventions/{id}/campos-clinicos/` deja de existir; `grep "campos-clinicos"` no arroja rutas en views.

### T-V2 — `ClinicalFieldRegistrationViewSet` (standalone, CRUD)
Heredar `AuditedModelViewSet`. Configuración:
- `queryset` = selector `registros_campo_clinico()`.
- `serializer_class = ClinicalFieldRegistrationSerializer`.
- `permission_classes = [IsAuthenticated, IsConapresOrReadOnly]`.
- `filterset_class = ClinicalFieldRegistrationFilter`.
- `ordering = ["id"]`.
- Delegar escritura en services: sobrescribir `perform_create`/`perform_update` para llamar a `crear_registro_campo_clinico`/`actualizar_registro_campo_clinico` (o `create`/`update` con validación + service), asegurando que la auditoría y `creado_por`/`actualizado_por` la fija el service (evitar doble auditoría de `AuditedModelViewSet`).

> Nota de implementación: `AuditedModelViewSet.perform_*` ya audita; si la escritura delega en services (que también auditan), sobrescribir `perform_create`/`perform_update` para NO duplicar auditoría — llamar solo al service. Documentar la decisión en el docstring del viewset.

**Criterios de aceptación:**
- Ruta `clinical-field-registrations` expone list/retrieve/create/update/partial_update/destroy.
- Un usuario CONAPRES puede crear; un usuario sin rol recibe 403 en escritura y 200 en lectura.
- La respuesta incluye `disponibilidad`.
- No se registra auditoría duplicada (una entrada por operación).

### T-V3 — `ClinicalFieldAllocationViewSet` (standalone, CRUD)
Heredar `AuditedModelViewSet`. Configuración:
- `queryset` = selector `asignaciones_campo_clinico()`.
- `serializer_class = ClinicalFieldAllocationSerializer`.
- `permission_classes = [IsAuthenticated, IsRegionalOrganOrReadOnly]`.
- `filterset_class = ClinicalFieldAllocationFilter`.
- `ordering = ["id"]`.
- Delegar create/update/destroy en `crear_/actualizar_/eliminar_asignacion_campo_clinico` (misma nota de no duplicar auditoría; `perform_destroy` debe llamar al service que recalcula el acumulador, y traducir `ProtectedError` a 409 como hace `AuditedModelViewSet`).

**Criterios de aceptación:**
- Ruta `clinical-field-allocations` expone CRUD completo.
- Escritura solo grupo `Gobierno Regional` (o superuser); lectura para autenticados.
- Crear excediendo disponibilidad → 400 con mensaje en `campos_clinicos_autorizados`.
- Tras create/update/delete, el registro (a) padre queda con `campos_clinicos_asignados` recalculado.

### T-V4 — Registrar en el router
Añadir ambos ViewSets a `ENTITY_VIEWSETS` (para reutilizar el bucle de registro) o registrarlos explícitamente en `urls.py`:
- `clinical-field-registrations` → `ClinicalFieldRegistrationViewSet`.
- `clinical-field-allocations` → `ClinicalFieldAllocationViewSet`.

**Criterios de aceptación:**
- En shell, `router` expone 6 rutas (CRUD) por cada basename bajo `/api/v1/`.
- `GET /api/v1/clinical-field-registrations/` y `GET /api/v1/clinical-field-allocations/` responden 200 autenticado.

---

## 9. Tareas — Internados (`apps/internados`)

### T-I1 — `Internship.campo_clinico` → FK a `ClinicalFieldAllocation` (`models.py:236`)
- Cambiar el `to` de la FK a `apps.convenios.ClinicalFieldAllocation`, `on_delete=PROTECT`, `related_name="internos"`.
- Conservar `db_column="campo_clinico_id"`.
- Actualizar el import en `models.py` (`from apps.convenios.models import ... ClinicalFieldAllocation`) y retirar el de `ClinicalField`.

**Criterios de aceptación:**
- `Internship.campo_clinico` apunta a `ClinicalFieldAllocation`; `db_column` sigue `campo_clinico_id`.
- `related_name="internos"` disponible desde la asignación (para T-S6).

### T-I2 — RN-13 sobre `campos_clinicos_autorizados` (`services.py:190-192`)
- `usados = Internship.objects.filter(campo_clinico=campo_clinico).count()`.
- `if usados >= campo_clinico.campos_clinicos_autorizados:` → `ValidationError({"campo_clinico": "Se alcanzó el máximo de campos clínicos autorizados."})`.
- Ajustar la validación `campo_clinico.convenio_id != convenio.id` (línea 187): la asignación tiene `convenio_id`, sigue siendo válida.

**Criterios de aceptación:**
- Registrar un internado cuando `usados >= campos_clinicos_autorizados` → `ValidationError`.
- La comprobación de pertenencia al convenio sigue funcionando contra `asignacion.convenio_id`.

### T-I3 — Chequeo de ámbito (`services.py:199`) — DECISIÓN
El campo ya no tiene `ambito_geografico_sanitario`. **Decisión documentada:** derivar el ámbito de la IPRESS del registro/asignación en lugar del campo eliminado.
- Reemplazar la comparación por: `if datos["ambito_geografico_sanitario"].id != campo_clinico.ipress.ambito_geografico_sanitario_id:` (la `Ipress` tiene `ambito_geografico_sanitario`, confirmado por `IpressViewSet.filterset_fields`).
- Mensaje en español: `"Debe coincidir con el ámbito de la sede docente."`

**Criterios de aceptación:**
- El chequeo compara contra `campo_clinico.ipress.ambito_geografico_sanitario_id`.
- No hay referencia a `campo_clinico.ambito_geografico_sanitario` (columna eliminada).

### T-I4 — Serializers y selectors de internados
- `serializers.py:107,121`: `campo_clinico` sigue siendo el nombre del campo; verificar que `InternshipReadSerializer`/`InternshipWriteSerializer` no expongan atributos del modelo viejo. Sin cambios de nombre, solo confirmar coherencia.
- `selectors.py:53`: `select_related("...", "campo_clinico", ...)` sigue válido (FK renombrada de destino, no de atributo); opcionalmente añadir `campo_clinico__campo_clinico_ipress` si se serializa.

**Criterios de aceptación:**
- `internados_visibles` compila y el `select_related` sobre `campo_clinico` no rompe.
- Serialización de internados no referencia campos inexistentes de la asignación.

---

## 10. Tareas — Migraciones

### T-MIG1 — `apps/convenios/migrations/0015_*`
Una migración con este orden seguro:
1. `RenameModel` `ClinicalField` → `ClinicalFieldRegistration`.
2. `AlterModelTable` a `campo_clinico_ipress`.
3. `RenameField` `cantidad_maxima` → `campos_clinicos_registrados`.
4. `AddField` `campos_clinicos_asignados` (`default=0`) y los 4 campos de auditoría (`creado_por`/`actualizado_en`/`actualizado_por`; `creado_en` ya existe).
5. `AlterUniqueTogether` a `(convenio, ipress, carrera_profesional, especialidad)`.
6. `CreateModel` `ClinicalFieldAllocation` (tabla `campo_clinico_ipress_universidad`) con su `unique_together`.
7. **Data migration (`RunPython`)**: por cada `ClinicalFieldRegistration` existente, crear una `ClinicalFieldAllocation` con:
   - `campo_clinico_ipress` = el registro,
   - `convenio` = registro.convenio, `ipress` = registro.ipress, `carrera_profesional` = registro.carrera_profesional, `especialidad` = registro.especialidad,
   - `universidad` = registro.convenio.universidad,
   - `campos_clinicos_autorizados` = registro.campos_clinicos_registrados,
   - `fecha_inicio`/`fecha_fin` = fechas del convenio (registro.convenio.fecha_inicio/fecha_fin); si nulas, usar `vigencia_inicio`/`vigencia_fin` del registro ANTES de eliminarlas (ver paso 9 — leer estos valores en la data migration antes del `RemoveField`).
   - luego setear `registro.campos_clinicos_asignados = campos_clinicos_registrados` y guardar.
   - `reverse_code` que borre las asignaciones creadas (o `RunPython.noop` documentado).
8. (La data migration del paso 7 debe leer `vigencia_inicio`/`vigencia_fin` ANTES de borrarlos.)
9. `RemoveField` `vigencia_inicio`, `vigencia_fin`, `ambito_geografico_sanitario`, `observaciones`.

> IMPORTANTE: el paso 7 depende de que la asignación creada quede identificable para la data migration de internados (T-MIG2). Guardar el mapeo `registro_id → allocation_id` es implícito: hay 1 asignación por registro tras la migración inicial, y `Internship.campo_clinico_id` hoy apunta al `registro` (mismo id espacial). En la data migration de internados, resolver la asignación por `campo_clinico_ipress_id == internship.campo_clinico_id` (el valor viejo apuntaba al registro).

**Criterios de aceptación:**
- `python manage.py migrate` aplica 0015 sin error sobre `db.sqlite3`.
- Cada registro (a) preexistente tiene exactamente una asignación (b) con `autorizados == registrados` y `universidad == convenio.universidad`.
- `campos_clinicos_asignados` de cada registro == `campos_clinicos_registrados`.
- La migración es reversible (o el `reverse` está documentado como no soportado con motivo).

### T-MIG2 — `apps/internados/migrations/0017_*`
> Nota: la última migración de internados es `0016`, no `0006`; usar `0017`.
- `AlterField` `Internship.campo_clinico` → `convenios.ClinicalFieldAllocation` (`db_column="campo_clinico_id"`, `PROTECT`, `related_name="internos"`).
- `RunPython` que repunta cada `Internship` existente: `internship.campo_clinico_id` (que apunta al viejo registro) → id de la `ClinicalFieldAllocation` creada para ese registro en T-MIG1 (resolver por `ClinicalFieldAllocation.objects.get(campo_clinico_ipress_id=<valor_viejo>)`).
- `dependencies` sobre `('convenios', '0015_...')`.

**Criterios de aceptación:**
- `migrate` aplica 0017 tras 0015 sin error.
- Toda fila de internado preexistente queda con `campo_clinico_id` apuntando a una `ClinicalFieldAllocation` válida (la del repunte); ninguna fila se pierde.
- `python manage.py makemigrations --check --dry-run` queda limpio (sin cambios pendientes) tras aplicar todo.
- `python manage.py check` OK.

---

## 11. Tareas — Documentación

### T-D1 — `docs/db_schema_modulo_01_convenios.md` §9
Reemplazar la tabla `campo_clinico` por las dos tablas `campo_clinico_ipress` y `campo_clinico_ipress_universidad` (columnas, tipos, FKs, `unique_together`), y documentar reglas: CONAPRES registra el total; Órgano Regional asigna por universidad con disponibilidad = registrados − Σ autorizados.

**Criterios de aceptación:** §9 lista ambas tablas con sus columnas exactas y las reglas de disponibilidad/roles; no queda mención a `campo_clinico` con las columnas eliminadas.

### T-D2 — `docs/db_schema_er_global.md`
Actualizar FKs: `campo_clinico_ipress`→(convenio, ipress, carrera_profesional, especialidad); `campo_clinico_ipress_universidad`→(campo_clinico_ipress, convenio, ipress, carrera_profesional, especialidad, universidad); `interno`→`campo_clinico_ipress_universidad`.

**Criterios de aceptación:** el diagrama/lista ER refleja las dos tablas nuevas y el repunte de `interno`.

### T-D3 — `docs/db_schema_modulo_02_internados.md`
Actualizar la FK de `interno` a la asignación (b) y RN-13/RN-17 (cupo contra `campos_clinicos_autorizados`; chequeo de ámbito derivado de la IPRESS).

**Criterios de aceptación:** el doc describe la FK a `campo_clinico_ipress_universidad` y RN-13 recalibrada.

### T-D4 — `docs/modulo_01_crud_transversales.md` y `docs/api_accesos_frontend.md`
Documentar endpoints `clinical-field-registrations` (escritura CONAPRES, filtros: convenio, ipress, carrera_profesional, especialidad; expone disponibilidad) y `clinical-field-allocations` (escritura Gobierno Regional, filtros: campo_clinico_ipress, convenio, ipress, carrera_profesional, universidad). Retirar el endpoint anidado `conventions/{id}/campos-clinicos/`.

> Nota: verificar el nombre exacto del archivo de accesos (`docs/api_accesos_frontend.md`); si en el repo es `docs/api_almacenamiento_frontend.md` u otro, actualizar el que documente accesos/roles del módulo Convenios.

**Criterios de aceptación:** ambos endpoints documentados con roles y filtros; el endpoint anidado ya no aparece.

### T-D5 — `CLAUDE.md`
Añadir a §"Reglas del módulo Gestionar Convenios" (o donde corresponda) los dos sub-módulos, roles (CONAPRES registra total; `Gobierno Regional` asigna por universidad), la regla de disponibilidad, y una nueva RN (p. ej. **RN-25**) del repunte de `Internship` a la asignación con cupo contra `campos_clinicos_autorizados`.

**Criterios de aceptación:** `CLAUDE.md` describe los dos sub-módulos, sus roles y la RN-25.

---

## 12. Cierre

### T-C1 — `/code-review`
Ejecutar `/code-review` sobre el diff completo (models, services, selectors, serializers, permissions, filters, views, urls, migraciones convenios + internados, docs). Resolver hallazgos antes de cerrar.

### T-C2 — `/fix-types`
Ejecutar mypy; si reporta errores, invocar `/fix-types` (no corregir tipos a mano).

**Criterios de aceptación (verificación end-to-end):**
1. `python manage.py makemigrations && migrate` limpios; `makemigrations --check --dry-run` sin cambios; `manage.py check` OK.
2. Router expone `clinical-field-registrations` y `clinical-field-allocations` con CRUD (verificar en shell).
3. CONAPRES crea registro `registrados=10`; Gobierno Regional crea 2 asignaciones 6+4 → `asignados=10`, `disponibilidad=0`; una 3ª de 1 → 400.
4. Internado consume cupo; superado `campos_clinicos_autorizados` → RN-13 400.
5. Fila de internado preexistente repuntada correctamente (data migration).
6. `/code-review` sin hallazgos bloqueantes; mypy sin errores.

---

## 13. Referencias rápidas (schema y código)

- Modelo actual a refactorizar: `apps/convenios/models.py:786` (`ClinicalField`, tabla `campo_clinico`).
- Patrón sede docente / tope convenio: `apps/convenios/services.py:198-212` (`definir_campo_clinico`).
- `ESTADOS_VIGENTES`, `_exigir_especifico`: `apps/convenios/services.py:29,80`.
- Permiso espejo: `apps/convenios/permissions.py:26` (`IsAdminRoleOrReadOnly`), `exigir_roles` :65.
- Base CRUD auditado: `apps/convenios/views.py:200` (`AuditedModelViewSet`), registro en router: `apps/convenios/views.py:412` (`ENTITY_VIEWSETS`), `apps/convenios/urls.py:22-24`.
- FK a repuntar: `apps/internados/models.py:236`; RN-13/ámbito: `apps/internados/services.py:190-202`; serializers `apps/internados/serializers.py:107,121`; selector `apps/internados/selectors.py:53`.
- `Ipress.ambito_geografico_sanitario` confirmado en `apps/convenios/views.py:355` (filterset de `IpressViewSet`).
- `University`: `apps/convenios/models.py:461`.
