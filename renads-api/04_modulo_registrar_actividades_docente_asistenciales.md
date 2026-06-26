# Módulo 3: Registrar Actividades Docente-Asistenciales

## 1. Definición

El módulo **Registrar Actividades Docente-Asistenciales** permite registrar el desarrollo de las actividades realizadas por los internos en una sede docente o establecimiento de salud, como evidencia del cumplimiento de sus servicios, prácticas, rotaciones o actividades formativas supervisadas.

Las actividades deben estar vinculadas a un interno, un internado activo, una sede docente, un periodo, un tutor o docente responsable y, cuando corresponda, una rotación autorizada.

## 2. Objetivos del módulo

1. Registrar actividades realizadas por internos.
2. Asociar cada actividad a una sede docente y rotación.
3. Registrar fecha, servicio, área, unidad y tipo de actividad.
4. Registrar carga horaria o duración.
5. Permitir validación por tutor o docente.
6. Permitir observación o rechazo de actividades.
7. Generar historial de actividades por interno.
8. Generar reportes para universidades, sedes docentes, DIGEP y supervisores.

## 3. Procesos del módulo

### 3.1 Registro de actividad

El interno, tutor, universidad o sede docente registra las actividades desarrolladas en el marco del internado.

El sistema debe permitir:

1. Seleccionar interno.
2. Seleccionar internado activo.
3. Asociar sede docente.
4. Asociar rotación autorizada, si corresponde.
5. Registrar fecha de actividad.
6. Registrar servicio, área o unidad.
7. Registrar tipo de actividad.
8. Registrar descripción o detalle.
9. Registrar horas o carga horaria.
10. Adjuntar evidencia PDF, si corresponde.

### 3.2 Validación de actividad

El tutor o docente revisa la actividad registrada.

El sistema debe permitir:

1. Aprobar la actividad.
2. Observar la actividad.
3. Rechazar la actividad.
4. Registrar comentario de validación.
5. Registrar fecha y usuario validador.

### 3.3 Consulta y reporte

El sistema permite consultar el historial de actividades por interno, sede, universidad, tutor, convenio, rotación y periodo.

El sistema debe permitir:

1. Consultar actividades por filtros.
2. Exportar reportes.
3. Generar consolidado de actividades.
4. Ver actividades pendientes de validación.
5. Ver actividades observadas o rechazadas.

## 4. Estados sugeridos

1. Registrada.
2. Pendiente de validación.
3. Observada.
4. Subsanada.
5. Validada.
6. Rechazada.
7. Cerrada.

## 5. Reglas de negocio

1. Solo se pueden registrar actividades para internados activos.
2. La actividad debe pertenecer al periodo vigente del internado.
3. Si la actividad se realiza durante una rotación, debe asociarse a una rotación autorizada.
4. No se deben registrar actividades en rotaciones rechazadas, canceladas o no autorizadas.
5. Toda actividad debe asociarse a una sede docente.
6. Toda actividad debe tener un tutor o docente responsable.
7. Las actividades observadas pueden ser subsanadas.
8. Las actividades validadas no deben modificarse sin registrar trazabilidad.
9. El sistema debe impedir duplicidades evidentes según interno, fecha, sede, servicio y horario, si se define control horario.
10. Las evidencias documentales, si se usan, deben adjuntarse en PDF.

## 6. Actores del módulo

1. Interno.
2. Tutor o docente.
3. Universidad.
4. Sede docente o establecimiento de salud.
5. DIGEP.
6. GORE, GERESA, DIRESA o DIRIS.
7. Auditor o supervisor.
8. Administrador RENADS.

## 7. Casos de uso

### CU-DA-01: Registrar actividad docente-asistencial

**Actor principal:** Interno, tutor, universidad o sede docente.  
**Resultado:** Actividad registrada y pendiente de validación.

### CU-DA-02: Adjuntar evidencia de actividad

**Actor principal:** Interno, tutor o universidad.  
**Resultado:** Evidencia PDF asociada a la actividad.

### CU-DA-03: Validar actividad

**Actor principal:** Tutor o docente.  
**Resultado:** Actividad validada.

### CU-DA-04: Observar actividad

**Actor principal:** Tutor o docente.  
**Resultado:** Actividad observada y devuelta para subsanación.

### CU-DA-05: Rechazar actividad

**Actor principal:** Tutor o docente.  
**Resultado:** Actividad rechazada con sustento.

### CU-DA-06: Consultar historial de actividades

**Actor principal:** Universidad, sede docente, DIGEP, auditor o supervisor.  
**Resultado:** Historial consultable por filtros.

### CU-DA-07: Generar reporte consolidado

**Actor principal:** Universidad, DIGEP o sede docente.  
**Resultado:** Reporte consolidado de actividades.

## 8. Requerimientos funcionales

- RF-DA-01: Registrar actividad docente-asistencial.
- RF-DA-02: Asociar actividad a interno.
- RF-DA-03: Asociar actividad a internado activo.
- RF-DA-04: Asociar actividad a sede docente.
- RF-DA-05: Asociar actividad a rotación autorizada, si corresponde.
- RF-DA-06: Registrar fecha de actividad.
- RF-DA-07: Registrar servicio, área o unidad.
- RF-DA-08: Registrar tipo de actividad.
- RF-DA-09: Registrar descripción de actividad.
- RF-DA-10: Registrar horas o carga horaria.
- RF-DA-11: Adjuntar evidencia PDF.
- RF-DA-12: Registrar tutor o docente supervisor.
- RF-DA-13: Validar actividad.
- RF-DA-14: Observar actividad.
- RF-DA-15: Rechazar actividad.
- RF-DA-16: Subsanar actividad observada.
- RF-DA-17: Consultar actividades por interno, sede, tutor, universidad, convenio, rotación y periodo.
- RF-DA-18: Generar reporte consolidado de actividades.
- RF-DA-19: Exportar reporte a PDF o Excel.
- RF-DA-20: Registrar trazabilidad de cambios.

## 9. Requerimientos no funcionales específicos

1. El registro de actividades debe ser simple y rápido para uso frecuente.
2. El sistema debe responder eficientemente a consultas por periodo y sede.
3. La información de actividades debe mantenerse íntegra y auditable.
4. Los cambios sobre actividades validadas deben requerir permisos especiales.
5. El sistema debe proteger datos personales del interno.

