# RENADS - Requerimientos No Funcionales Transversales

## 1. Seguridad

- RNF-SEG-01: El sistema debe implementar autenticación de usuarios.
- RNF-SEG-02: El sistema debe implementar autorización basada en roles y perfiles institucionales.
- RNF-SEG-03: El sistema debe restringir el acceso a información según entidad, rol y ámbito de competencia.
- RNF-SEG-04: El sistema debe proteger datos personales de internos, tutores y representantes institucionales.
- RNF-SEG-05: El sistema debe usar comunicación segura mediante HTTPS.
- RNF-SEG-06: El sistema debe registrar intentos fallidos de autenticación.
- RNF-SEG-07: El sistema debe permitir expiración automática de sesión.

## 2. Auditoría y trazabilidad

- RNF-AUD-01: Toda operación crítica debe quedar registrada en bitácora.
- RNF-AUD-02: La bitácora debe registrar usuario, fecha, hora, acción, entidad afectada, valor anterior y valor nuevo cuando corresponda.
- RNF-AUD-03: Los cambios de estado de convenios, internados, rotaciones y actividades deben ser auditables.
- RNF-AUD-04: Los documentos reemplazados deben conservar referencia histórica o versión previa.
- RNF-AUD-05: Las autorizaciones de rotaciones deben conservar evidencia de autoridad, fecha y decisión.

## 3. Gestión documental

- RNF-DOC-01: El sistema debe permitir adjuntar documentos en formato PDF.
- RNF-DOC-02: Cada documento debe estar asociado a una actividad, proceso o entidad del sistema.
- RNF-DOC-03: Cada documento debe registrar nombre, tipo, versión, usuario de carga, fecha y estado.
- RNF-DOC-04: El sistema debe permitir observar, validar, reemplazar o anular documentos.
- RNF-DOC-05: El sistema debe preservar los documentos del expediente digital durante el tiempo definido por normativa archivística.

## 4. Disponibilidad

- RNF-DIS-01: El sistema debe estar disponible para usuarios nacionales, regionales e institucionales.
- RNF-DIS-02: El sistema debe manejar interrupciones de forma controlada y evitar pérdida de información.
- RNF-DIS-03: El sistema debe permitir copias de seguridad periódicas.
- RNF-DIS-04: El sistema debe contar con mecanismos de recuperación ante fallos.

## 5. Rendimiento

- RNF-REN-01: Las consultas frecuentes deben responder en tiempos adecuados para uso operativo.
- RNF-REN-02: Los filtros por convenio, universidad, región, sede, interno y periodo deben ser eficientes.
- RNF-REN-03: La carga y descarga de documentos PDF debe manejar archivos de tamaño definido por política del sistema.
- RNF-REN-04: El sistema debe soportar concurrencia de múltiples entidades a nivel nacional.

## 6. Usabilidad

- RNF-USA-01: El sistema debe presentar bandejas de trabajo por rol.
- RNF-USA-02: El sistema debe mostrar estados claros de convenios, internados, rotaciones y actividades.
- RNF-USA-03: Los formularios deben validar información obligatoria antes de guardar.
- RNF-USA-04: El sistema debe mostrar alertas de vencimiento y tareas pendientes.
- RNF-USA-05: El sistema debe permitir búsquedas y filtros por campos clave.

## 7. Interoperabilidad

- RNF-INT-01: El sistema debe diseñarse para integrarse posteriormente con una plataforma de firma digital.
- RNF-INT-02: El sistema debe diseñarse para posible integración con servicios de identidad.
- RNF-INT-03: El sistema debe permitir exportar reportes en PDF y Excel.
- RNF-INT-04: El sistema debe considerar integración futura con registros oficiales como RENIEC, SUNEDU u otros, si se aprueba el alcance.

## 8. Mantenibilidad

- RNF-MAN-01: El sistema debe manejar catálogos parametrizables.
- RNF-MAN-02: Los tipos de documento deben poder administrarse sin cambios de código.
- RNF-MAN-03: Los roles y permisos deben ser configurables.
- RNF-MAN-04: Las plantillas de PDF deben poder actualizarse de forma controlada.
- RNF-MAN-05: El sistema debe separar funcionalmente convenios, internados y actividades.

## 9. Cumplimiento

- RNF-CUM-01: El sistema debe alinearse con las resoluciones y procedimientos aplicables.
- RNF-CUM-02: El sistema debe conservar evidencia de cumplimiento normativo.
- RNF-CUM-03: El sistema debe permitir auditorías internas y externas.
- RNF-CUM-04: El sistema debe evitar el registro de internados sin convenio habilitante.
- RNF-CUM-05: El sistema debe impedir rotaciones sin autorización de autoridades suscritas en el Convenio Específico.

