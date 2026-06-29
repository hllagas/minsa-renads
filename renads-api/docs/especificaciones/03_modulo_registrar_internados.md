# Módulo 2: Registrar Internados

## 1. Definición

El módulo **Registrar Internados** permite registrar a los alumnos de último año de pregrado o profesionales que cursan segunda especialidad, denominados internos, vinculándolos a una universidad, un Convenio Específico vigente, una sede docente, un tutor o docente responsable y un ámbito geográfico sanitario.

El módulo también controla las rotaciones de los internos entre establecimientos de salud que pertenecen al mismo ámbito geográfico sanitario.

## 2. Objetivos del módulo

1. Registrar internos autorizados para realizar actividades docente-asistenciales.
2. Asociar cada interno a una universidad y Convenio Específico vigente.
3. Registrar tutor o docente responsable.
4. Registrar sede docente principal.
5. Registrar y controlar rotaciones entre establecimientos de salud.
6. Validar que las rotaciones se realicen dentro del mismo ámbito geográfico sanitario.
7. Limitar la cantidad máxima de rotaciones a 4 durante el periodo de internado.
8. Registrar autorización de rotaciones por las autoridades suscritas en el Convenio Específico.
9. Controlar fechas de inicio, fin, suspensión, retiro o culminación del internado.
10. Generar reportes de internos, tutores, sedes, rotaciones y estados.

## 3. Procesos del módulo

### 3.1 Registro del interno

La universidad registra al interno que realizará actividades de internado en una sede docente autorizada.

El sistema debe permitir:

1. Registrar datos personales del interno.
2. Registrar datos académicos.
3. Asociar universidad.
4. Asociar programa, carrera o especialidad.
5. Asociar Convenio Específico vigente.
6. Asociar sede docente principal.
7. Asociar tutor o docente responsable.
8. Registrar fecha de inicio y fecha de fin.

### 3.2 Validación de convenio y campo clínico

El sistema valida que el internado se encuentre respaldado por un Convenio Específico vigente y que exista disponibilidad de campo clínico.

El sistema debe validar:

1. Convenio Específico vigente.
2. Convenio no cerrado, vencido ni anulado.
3. Campo clínico disponible.
4. Sede docente autorizada.
5. Ámbito geográfico sanitario permitido.

### 3.3 Registro de rotaciones

El interno puede rotar entre establecimientos de salud durante el periodo del internado.

El sistema debe permitir:

1. Registrar sede de origen.
2. Registrar sede de destino.
3. Registrar servicio, área o unidad de rotación.
4. Registrar fecha de inicio y fin de la rotación.
5. Validar que ambas sedes pertenezcan al mismo ámbito geográfico sanitario.
6. Validar que el interno no exceda 4 rotaciones durante su internado.
7. Adjuntar sustento documental PDF, si corresponde.

### 3.4 Autorización de rotaciones

Las rotaciones de internos solo pueden ser autorizadas por las autoridades suscritas en el Convenio Específico.

El sistema debe permitir:

1. Identificar las autoridades suscritas en el Convenio Específico.
2. Registrar solicitud de rotación.
3. Registrar aprobación, observación o rechazo.
4. Registrar fecha de autorización.
5. Registrar autoridad responsable.
6. Adjuntar documento PDF de autorización, si corresponde.
7. Impedir que una rotación inicie sin autorización.

### 3.5 Cierre del internado

Al finalizar el periodo, el internado debe cerrarse con historial completo de sedes, rotaciones y actividades.

El sistema debe permitir:

1. Registrar culminación.
2. Registrar retiro o suspensión.
3. Registrar observaciones.
4. Consultar historial de rotaciones.
5. Consultar actividades docente-asistenciales asociadas.

## 4. Estados sugeridos del internado

1. Registrado.
2. Pendiente de validación.
3. Observado.
4. Validado.
5. Activo.
6. En rotación solicitada.
7. En rotación autorizada.
8. En rotación observada.
9. Suspendido.
10. Retirado.
11. Culminado.
12. Anulado.

## 5. Estados sugeridos de la rotación

1. Solicitada.
2. Pendiente de autorización.
3. Observada.
4. Autorizada.
5. Rechazada.
6. En curso.
7. Culminada.
8. Cancelada.

## 6. Reglas de negocio

1. Todo interno debe estar asociado a una universidad.
2. Todo interno debe estar asociado a un Convenio Específico vigente.
3. El Convenio Específico debe estar suscrito, publicado o vigente, según la regla operativa que se defina.
4. No se permite registrar internos sobre Convenios Marco sin Convenio Específico.
5. Todo interno debe tener un tutor o docente responsable.
6. El tiempo máximo del internado es de un año.
7. Un interno puede rotar por varias sedes docentes durante el internado.
8. Las rotaciones solo pueden realizarse entre establecimientos del mismo ámbito geográfico sanitario.
9. La cantidad máxima de rotaciones por interno es de 4 durante todo el periodo de internado.
10. Las rotaciones solo pueden ser autorizadas por las autoridades suscritas en el Convenio Específico.
11. No se debe permitir iniciar una rotación sin autorización registrada.
12. No se debe permitir registrar rotaciones fuera de las fechas del internado.
13. No se debe permitir exceder la cantidad de campos clínicos autorizados.
14. Un cambio de tutor debe quedar registrado con fecha, motivo y responsable.
15. Todo cambio de estado del internado o rotación debe quedar en bitácora.

## 7. Actores del módulo

1. Universidad pública o privada.
2. Interno.
3. Tutor o docente.
4. Sede docente o establecimiento de salud.
5. Autoridades suscritas en el Convenio Específico.
6. GORE, GERESA, DIRESA o DIRIS.
7. DIGEP.
8. Administrador RENADS.
9. Auditor o supervisor.

## 8. Casos de uso

### CU-IN-01: Registrar interno

**Actor principal:** Universidad.  
**Resultado:** Interno registrado y asociado a Convenio Específico vigente.

### CU-IN-02: Validar internado

**Actor principal:** Sistema RENADS, Universidad o DIGEP.  
**Resultado:** Internado validado u observado según convenio, sede y campo clínico.

### CU-IN-03: Asignar tutor o docente

**Actor principal:** Universidad.  
**Resultado:** Interno queda asociado a un tutor responsable.

### CU-IN-04: Registrar sede docente principal

**Actor principal:** Universidad.  
**Resultado:** Interno queda vinculado a una sede docente autorizada.

### CU-IN-05: Solicitar rotación

**Actor principal:** Universidad, tutor o sede docente.  
**Resultado:** Rotación registrada en estado solicitada o pendiente de autorización.

### CU-IN-06: Autorizar rotación

**Actor principal:** Autoridad suscrita en el Convenio Específico.  
**Resultado:** Rotación autorizada, observada o rechazada.

### CU-IN-07: Validar límite de rotaciones

**Actor principal:** Sistema RENADS.  
**Resultado:** Rotación permitida si el interno no excede 4 rotaciones.

### CU-IN-08: Validar ámbito geográfico sanitario

**Actor principal:** Sistema RENADS.  
**Resultado:** Rotación permitida si sede origen y destino pertenecen al mismo ámbito geográfico sanitario.

### CU-IN-09: Registrar culminación del internado

**Actor principal:** Universidad o tutor.  
**Resultado:** Internado culminado con historial completo.

### CU-IN-10: Consultar historial del internado

**Actor principal:** Universidad, DIGEP, sede docente, auditor o supervisor.  
**Resultado:** Historial consultable de tutor, sedes, rotaciones, actividades y estados.

## 9. Requerimientos funcionales

- RF-IN-01: Registrar interno.
- RF-IN-02: Registrar datos personales del interno.
- RF-IN-03: Registrar datos académicos del interno.
- RF-IN-04: Asociar interno a universidad.
- RF-IN-05: Asociar interno a carrera, programa o especialidad.
- RF-IN-06: Asociar interno a Convenio Específico vigente.
- RF-IN-07: Validar disponibilidad de campo clínico.
- RF-IN-08: Asignar tutor o docente responsable.
- RF-IN-09: Registrar sede docente principal.
- RF-IN-10: Registrar fecha de inicio y fin del internado.
- RF-IN-11: Validar duración máxima de un año.
- RF-IN-12: Registrar solicitud de rotación.
- RF-IN-13: Registrar sede origen y sede destino de la rotación.
- RF-IN-14: Validar que las sedes pertenezcan al mismo ámbito geográfico sanitario.
- RF-IN-15: Validar máximo de 4 rotaciones por interno.
- RF-IN-16: Registrar autorización de rotación.
- RF-IN-17: Restringir autorización a autoridades suscritas en el Convenio Específico.
- RF-IN-18: Registrar observación o rechazo de rotación.
- RF-IN-19: Impedir inicio de rotación sin autorización.
- RF-IN-20: Registrar suspensión, retiro, culminación o anulación del internado.
- RF-IN-21: Registrar cambio de tutor o sede principal, si corresponde.
- RF-IN-22: Consultar historial de rotaciones.
- RF-IN-23: Consultar internos por convenio, universidad, sede, tutor, región y periodo.
- RF-IN-24: Generar reportes de internos, campos clínicos usados y rotaciones.

## 10. Requerimientos no funcionales específicos

1. El sistema debe validar automáticamente reglas de convenio, campo clínico, ámbito geográfico y rotaciones.
2. Las autorizaciones deben quedar registradas con trazabilidad legal y administrativa.
3. Los datos personales del interno deben protegerse según normativa aplicable.
4. Las búsquedas deben permitir localizar internos por documento, universidad, convenio, sede y periodo.
5. La bitácora debe conservar cambios de tutor, sede, estado y rotación.

