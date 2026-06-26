# Guía de pruebas manuales — Módulo `internados`

Prueba CRUD de personas, internados y el flujo de rotaciones contra el backend real.

## Prerrequisitos
1. **Backend arriba** (`python manage.py runserver`) y **frontend** (`npm run dev`) — los corre el usuario.
2. Sesión iniciada. Para CRUD de personas/internados usar `Universidad` o `Administrador RENADS`;
   para autorizar rotaciones, `Autoridad de convenio`.
3. **Datos base necesarios** (si el backend no los tiene seedeados, crearlos primero):
   - `service-areas` (servicios/áreas) — **requerido para crear rotaciones** (hoy puede estar vacío).
   - Un **Convenio Específico vigente** con al menos un **campo clínico** (módulo Convenios).
   - Universidades, IPRESS, carreras profesionales, tipos de documento (módulo Convenios/maestros).

## 1. Personas (`/internados/personas`)
1. Índice con **Internos** y **Tutores**.
2. **Internos** → "Nuevo" (rol Universidad/Admin): completar documento, tipo de documento (combobox),
   nombres, apellidos, universidad, carrera (combobox con búsqueda) → Guardar → aparece en la tabla.
3. **Tutores** → "Nuevo": documento, tipo, nombres, apellidos, especialidad/IPRESS (opcional) → Guardar.
4. Editar / Eliminar (confirmación). Sin rol de escritura → "Solo lectura".

## 2. Alta de internado (`/internados/nuevo`)
1. "Nuevo internado" (rol Universidad).
2. Seleccionar **Interno**, **Convenio Específico** (combobox), **IPRESS**, **Tutor**, **Ámbito
   geográfico sanitario**; **Campo clínico (id)** como número; fechas (fin ≤ 1 año).
3. Guardar → redirige al detalle. Si el backend rechaza (convenio no específico/vigente, fechas, etc.)
   → toast con el error.

## 3. Detalle del internado (`/internados/[id]`)
1. Pestaña **Datos**: interno, convenio, sede, tutor, estado (`estado_actual` + código), fechas.
2. **Editar** → cambia IPRESS/observaciones/fechas (PATCH). (Tutor no se edita aquí.)
3. Acciones (según rol): **Cambiar estado** (Admin), **Cambiar tutor** (Universidad: nuevo tutor +
   fecha + motivo), **Agregar rotación** (Universidad).

## 4. Flujo de rotaciones (pestaña Rotaciones)
1. **Agregar rotación** (acción del internado, rol Universidad): sede origen/destino (mismo ámbito
   sanitario — RN-8), servicio/área, fechas → se crea con estado inicial.
2. En la lista de rotaciones, por cada una (según rol):
   - **Autorizar** (Autoridad de convenio): `participante_convenio` (id de un participante **firmante**
     del convenio), resultado (Aprobado/Observado/Rechazado), fecha.
   - **Iniciar** (Universidad): requiere autorización aprobada (RN-11) → pasa a en curso.
   - **Cambiar estado** (Admin).
3. Verificar: máximo **4 rotaciones** por interno (RN-9); la 5ª debe fallar con error del backend.

## Notas / limitaciones
- `campo_clinico` y `participante_convenio` se ingresan como ids numéricos (sin selector dependiente).
- El gating del front es UX; el backend valida rol, RN (mismo ámbito, máx. 4, autorización previa) y estados.
- Si `service-areas` está vacío en el backend, crear al menos uno antes de probar rotaciones.
