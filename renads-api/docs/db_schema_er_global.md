# Diagrama ER Global — RENADS

Diagrama entidad-relación consolidado de los 3 módulos. Las tablas conservan nombres en español; entre paréntesis se indica la clase Django (inglés) y el módulo de origen.

- **M1** = Gestionar Convenios (`convenios`)
- **M2** = Registrar Internados (`internados`)
- **M3** = Registrar Actividades (`actividades`)
- **DJ** = nativo de Django

> Notación: `─<` indica "uno a muchos" (la cresta apunta al lado *muchos*). `┄┄` indica relación **polimórfica** vía `django_content_type`.

---

## 1. Diagrama (Mermaid)

```mermaid
erDiagram
    %% ===== Catálogos clave =====
    region ||--o{ gobierno_regional : ""
    ambito_geografico_sanitario ||--o{ ipress : ""

    %% ===== M1: Jerarquía GORE =====
    gobierno_regional ||--o{ organo_regional : ""
    organo_regional ||--o{ unidad_ejecutora : ""
    unidad_ejecutora ||--o{ ipress : ""

    %% ===== M1: Universidad =====
    universidad ||--o{ autoridad_universidad : ""
    universidad ||--o{ facultad : ""
    universidad ||--o{ local_universidad : ""
    facultad ||--o{ carrera_profesional : ""
    especialidad ||--o{ carrera_profesional : ""
    nivel_academico ||--o{ carrera_profesional : ""

    %% ===== M1: Convenio =====
    tipo_convenio ||--o{ convenio : ""
    convenio ||--o{ convenio : "marco→especifico"
    plantilla_convenio ||--o{ convenio : ""
    estado_convenio ||--o{ convenio : ""
    convenio ||--o{ participante_convenio : ""
    convenio ||--o{ historial_estado_convenio : ""
    convenio ||--o{ evaluacion_tecnica : ""
    convenio ||--o{ opinion_conapres : ""
    convenio ||--o{ campo_clinico : ""
    convenio ||--o{ opinion_juridica : ""
    convenio ||--o{ firma : ""
    convenio ||--o{ publicacion : ""
    ipress ||--o{ campo_clinico : ""
    carrera_profesional ||--o{ campo_clinico : ""

    %% ===== M2: Internado =====
    interno ||--o{ internado : ""
    convenio ||--o{ internado : ""
    campo_clinico ||--o{ internado : ""
    ipress ||--o{ internado : "sede principal"
    tutor ||--o{ internado : ""
    universidad ||--o{ interno : ""
    carrera_profesional ||--o{ interno : ""
    internado ||--o{ historial_estado_internado : ""
    internado ||--o{ historial_tutor : ""
    internado ||--o{ rotacion : ""
    ipress ||--o{ rotacion : "origen/destino"
    servicio_area ||--o{ rotacion : ""
    rotacion ||--o{ autorizacion_rotacion : ""
    participante_convenio ||--o{ autorizacion_rotacion : ""
    rotacion ||--o{ historial_estado_rotacion : ""

    %% ===== M3: Actividad =====
    interno ||--o{ actividad_docente_asistencial : ""
    internado ||--o{ actividad_docente_asistencial : ""
    ipress ||--o{ actividad_docente_asistencial : ""
    rotacion ||--o{ actividad_docente_asistencial : "opcional"
    tutor ||--o{ actividad_docente_asistencial : ""
    servicio_area ||--o{ actividad_docente_asistencial : ""
    tipo_actividad ||--o{ actividad_docente_asistencial : ""
    actividad_docente_asistencial ||--o{ validacion_actividad : ""
    actividad_docente_asistencial ||--o{ historial_estado_actividad : ""

    %% ===== Transversales (polimórficas) =====
    documento }o--|| django_content_type : "genérico"
    bitacora_auditoria }o--|| django_content_type : "genérico"
    representante }o--|| django_content_type : "genérico"
    perfil_usuario_entidad }o--|| django_content_type : "genérico"
```

---

## 2. Relaciones polimórficas (vía `django_content_type`)

| Tabla | Apunta a | Propósito |
|-------|----------|-----------|
| `representante` (M1) | `organo_minsa`, `organo_regional`, `unidad_ejecutora`, `ipress`, `conapres` | Representantes/autoridades por jerarquía |
| `perfil_usuario_entidad` (M1) | cualquier entidad organizacional | Vínculo usuario↔entidad↔rol |
| `convenio.solicitante` (M1) | `universidad`, `organo_regional`, … | Entidad solicitante |
| `participante_convenio` (M1) | cualquier entidad | Entidades participantes/firmantes |
| `firma.firmante` (M1) | `organo_minsa`, `universidad`, … | Entidad firmante |
| `documento` (M1) | toda tabla del flujo | Adjuntos PDF (repositorio externo) |
| `bitacora_auditoria` (M1) | cualquier entidad | Auditoría de operaciones críticas |

---

## 3. Puentes entre módulos

```
M1 (conventions)                M2 (internships)              M3 (activities)
────────────────                ────────────────              ───────────────
convenio ───────────────────────> internado
campo_clinico ──────────────────> internado
ipress ─────────────────────────> internado / rotacion ─────> actividad_docente_asistencial
universidad ────────────────────> interno
carrera_profesional ────────────> interno
participante_convenio ──────────> autorizacion_rotacion
                                  interno ────────────────────> actividad_docente_asistencial
                                  internado ──────────────────> actividad_docente_asistencial
                                  tutor / rotacion / servicio_area ──> actividad_docente_asistencial
documento (M1) ─ genérico ──────> [cualquier tabla de M1/M2/M3]
bitacora_auditoria (M1) ─ genérico ─> [cualquier tabla]
```

---

## 4. Mapa apps Django ↔ tablas

| App | Tablas (db_table) |
|-----|-------------------|
| **Gestionar Convenios** (`convenios`, M1) | `ubigeo`, `region`, `ambito_geografico_sanitario`, `tipo_convenio`, `estado_convenio`, `tipo_documento`, `tipo_gestion_universidad`, `tipo_entidad_universidad`, `tipo_autorizacion`, `nivel_academico`, `especialidad`, `tipo_autoridad_firmante`, `tipo_organo_regional`, `tipo_unidad_ejecutora`, `tipo_organo_minsa`, `cargo_ejecutivo`, `motivo_observacion`, `motivo_rechazo`, `motivo_cierre`, `gobierno_regional`, `organo_regional`, `unidad_ejecutora`, `ipress`, `organo_minsa`, `conapres`, `representante`, `universidad`, `autoridad_universidad`, `facultad`, `carrera_profesional`, `local_universidad`, `perfil_usuario_entidad`, `plantilla_convenio`, `convenio`, `participante_convenio`, `historial_estado_convenio`, `evaluacion_tecnica`, `opinion_conapres`, `campo_clinico`, `opinion_juridica`, `firma`, `publicacion`, `documento`, `bitacora_auditoria` |
| **Registrar Internados** (`internados`, M2) | `estado_internado`, `estado_rotacion`, `servicio_area`, `tipo_documento_identidad`, `interno`, `tutor`, `internado`, `historial_estado_internado`, `historial_tutor`, `rotacion`, `autorizacion_rotacion`, `historial_estado_rotacion` |
| **Registrar Actividades** (`actividades`, M3) | `tipo_actividad`, `estado_actividad`, `actividad_docente_asistencial`, `validacion_actividad`, `historial_estado_actividad` |
