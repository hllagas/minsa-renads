# Guía de pruebas manuales — Módulo `convenios`

Prueba end-to-end de CRUD, maestros, búsqueda server-side y flujo del convenio contra el backend real.

## Prerrequisitos
1. **Backend arriba** (lo corre el usuario): `python manage.py runserver` en `renaes-api` →
   `http://localhost:8000`. Datos seedeados (catálogos/entidades existen).
2. **Frontend:** `npm run dev` (lo corre el usuario) → `http://localhost:3000`. `.env.local` con
   `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`.
3. **Sesión:** iniciar sesión (módulo Auth). Para ver **todo** usar un usuario `Administrador RENADS`
   o superusuario; para probar **gating**, usuarios con roles acotados (DIGEP, CONAPRES, OGAJ, SG).

## 1. Lista de convenios (`/convenios`)
1. Abrir `/convenios` → tabla con código, título, tipo, estado, inicio.
2. **Búsqueda:** escribir en "Buscar por título o código" → la lista se filtra server-side.
3. **Filtros (combobox server-side):** abrir "Todos los tipos" / "Todos los estados", escribir para
   buscar (p. ej. estado "vigente") → al elegir, la tabla filtra. Verifica que estados más allá de
   los primeros 20 también aparezcan al buscar (deuda saldada).
4. **Paginación:** "Siguiente"/"Anterior" cambian de página (server-side).

## 2. Alta de convenio (`/convenios/nuevo`)
1. "Nuevo convenio" → formulario.
2. Seleccionar **Tipo de convenio** (combobox), escribir **Título**, **Fecha de solicitud**.
3. **Solicitante (limitación):** ingresar `solicitante_tipo_contenido` (id de ContentType) y
   `solicitante_id_objeto` como números válidos del backend.
4. Guardar → redirige al detalle. Si el backend rechaza (p. ej. RN-3: Específico sin Marco vigente),
   se muestra el error en un toast.

## 3. Detalle y edición (`/convenios/[id]`)
1. Abrir un convenio → pestaña **Datos** muestra tipo, estado (`estado_actual` + `estado_codigo`),
   solicitante, fechas.
2. **Editar** → cambia título/código/fechas/máx. campos clínicos → Guardar (PATCH) → vuelve al detalle.
   (El tipo de convenio no es editable por diseño.)
3. Pestañas **Campos clínicos / Participantes / Historial** listan los sub-recursos (pueden estar vacíos).

## 4. Flujo del convenio (acciones por rol)
> Cada acción aparece **solo** si el usuario tiene el rol. CONAPRES y campos clínicos aparecen solo
> en convenios **Específicos**.

| Acción | Rol | Resultado esperado |
|--------|-----|--------------------|
| Cambiar estado | Administrador RENADS | `{estado_codigo, observacion}`; estado inválido → error toast (`400`) |
| Evaluación técnica | DIGEP | resultado `Validado`/`Observado`; mueve el estado |
| Opinión CONAPRES | CONAPRES (Específico) | registra opinión |
| Agregar campo clínico | CONAPRES (Específico) | aparece en pestaña Campos clínicos |
| Opinión jurídica | OGAJ | registra opinión |
| Registrar firma | Secretaría General | bloquea si hay observaciones pendientes (error del backend) |
| Publicar | Secretaría General | `PUBLICADO` → `VIGENTE` |
| Agregar participante | Administrador RENADS | aparece en pestaña Participantes |

Pasos por acción: pulsar el botón → completar el diálogo → Guardar → toast de éxito y la pestaña /
estado se refresca. Verificar que un usuario **sin** el rol **no ve** el botón.

## 5. Maestros (`/convenios/maestros`)
1. Índice con tarjetas: Universidades, IPRESS, Gobiernos regionales, Unidades ejecutoras, Órganos
   regionales, Órganos MINSA, CONAPRES.
2. Entrar a **Universidades** → tabla + buscador + paginación. Con rol `Administrador RENADS`:
   "Nuevo" / "Editar" / "Eliminar" visibles; sin rol → "Solo lectura".
3. **Crear:** "Nuevo" → completar (combobox de FK con búsqueda server-side, p. ej. Tipo de gestión)
   → Guardar → aparece en la tabla.
4. **Editar / Eliminar:** modifican/borran (confirmación). Repetir en otra entidad (p. ej. IPRESS,
   con FK Unidad ejecutora y Ámbito sanitario).

## Notas / limitaciones conocidas
- **Solicitante/firmante/participante polimórficos** se capturan como ids numéricos de ContentType
  (no hay endpoint de ContentTypes en el contrato). Un selector entidad/tipo queda pendiente.
- El gating del front es UX; la **autoridad final es el backend** (valida rol, RN y estados).
