# Validación — Coordinador de tutores (`internados`)

**Fecha:** 2026-09-26
**Resultado:** EXITOSA — sin errores altos ni medios.

---

## Resumen de revisión

| Tarea | Descripción | Estado |
|-------|-------------|--------|
| T1 | Modelo `Coordinator` | OK |
| T2 | Modelo `CoordinatorSede` | OK |
| T3 | Modelo `CoordinatorTutor` | OK |
| T4 | Migración `0032_coordinador` | OK |
| T5 | `CoordinatorSerializer` | OK |
| T6 | `CoordinatorSedeSerializer` | OK |
| T7 | `CoordinatorTutorSerializer` | OK |
| T8 | `validar_asignacion_coordinador_sede` | OK |
| T9 | `crear_coordinador_sede` / `eliminar_coordinador_sede` | OK |
| T10 | `asignar_tutor_coordinador_sede` / `desasignar_tutor_coordinador_sede` | OK |
| T11 | `CoordinatorViewSet` con 4 acciones anidadas | OK (ver hallazgo L-1) |
| T12 | Registro en router de `apps/internados/urls.py` | OK |
| T13 | `docs/db_schema_modulo_02_internados.md` §5 Coordinador | OK |
| T14 | `docs/db_schema_er_global.md` — nodos y relaciones | OK |
| T15 | `CLAUDE.md` — reglas RN-CRD-01..06 | OK |

**`python manage.py check`**: sin errores (0 silenciados).
**`makemigrations --check --dry-run`**: sin diferencias detectadas.

---

## Hallazgos

### Nivel BAJO (mejora de consistencia arquitectónica)

**L-1 · `apps/internados/views.py:513` — `CoordinatorViewSet` omite `IsInstitutionalMember` en `permission_classes`**

```python
# Implementado:
permission_classes = [IsAuthenticated, IsUniversityOrReadOnly]

# Patrón del módulo (TutorViewSet, StudentViewSet, InternshipViewSet):
permission_classes = [IsAuthenticated, IsInstitutionalMember, IsUniversityOrReadOnly]
```

`IsInstitutionalMember` garantiza que el usuario tenga al menos un perfil institucional activo. Su ausencia permite a cualquier usuario autenticado sin perfil leer el listado de coordinadores. No está explícitamente exigido por el spec (que dice "inyectar `IsUniversityOrAdminOrReadOnly` o equivalente"), pero rompe el patrón arquitectónico del módulo. **Corrección sugerida:** agregar `IsInstitutionalMember` al `permission_classes` del `CoordinatorViewSet`.

---

## Puntos críticos verificados

| Punto | Verificación |
|-------|-------------|
| **RN-CRD-02** — `tutor_id` nullable y único | Implementado como `OneToOneField(SET_NULL, null=True, blank=True)`. La unicidad en BD la cubre el campo `OneToOne`. Correcto. |
| **RN-CRD-04** — `ipress.es_sede_docente=True` | `services.py:108`: `if not ipress.es_sede_docente: raise ValidationError(...)`. Correcto. |
| **RN-CRD-05** — Convenio Específico vigente | `services.py:113–118`: `Convention.objects.filter(tipo_convenio__codigo="ESPECIFICO", estado_actual__codigo="VIGENTE", ...)`. El ORM correcto sobre FKs → `Catalog.codigo`. Correcto. |
| **RN-CRD-06** — Unicidad global `(tutor, universidad, ipress)` | `services.py:172–176`: chequeo cross-tabla antes del `unique_together` local. Doble verificación implementada. Correcto. |
| **Auditoría** — 4 funciones de escritura | Todas llaman `registrar_auditoria(usuario, "CREAR"/"ELIMINAR", objeto)` con la firma correcta. Correcto. |
| **PK textual de `ipress`** | FK en modelos y migración apunta a `convenios.Ipress` (cuya PK es `codigo_renipress`, `primary_key=True`). No se necesita `to_field` explícito. Correcto. |
| **URLs anidadas** | Regex `(?P<sede_pk>[^/.]+)` y `(?P<tutor_pk>[^/.]+)` en `url_path` de las acciones. Sin colisión con el router DRF. Correcto. |
| **Migración** | Dependencias: `("internados", "0031_fix_identity_document_types")` y `("convenios", "0054_rename_organic_unit")`. Tres `CreateModel` en orden correcto. Correcto. |
| **Router** | `router.register("coordinators", views.CoordinatorViewSet, basename="coordinator")` en `apps/internados/urls.py`, incluido en `config/api_urls.py`. Correcto. |
| **Filtros** | `filterset_fields = ["activo", "sedes__universidad", "sedes__ipress"]` usa el `related_name="sedes"` correcto. Correcto. |
| **Schema §5** | Tres tablas con columnas, restricciones y endpoints documentados correctamente. Correcto. |
| **ER global** | 6 líneas Mermaid con nodos y relaciones del coordinador agregadas. Correcto. |
| **CLAUDE.md** | Reglas RN-CRD-01..06 agregadas en la sección del módulo Registrar Internados. Correcto. |

---

## Dictamen

La implementación cumple todos los criterios de aceptación del spec. No hay errores altos ni medios. Se procede a generar la guía de pruebas manuales.
