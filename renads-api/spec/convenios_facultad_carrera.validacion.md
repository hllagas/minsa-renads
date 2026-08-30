# Validación — `convenios_facultad_carrera`

**Veredicto: APROBADO (sin errores altos/medios).** Se genera la guía de pruebas manuales `spec/convenios_facultad_carrera.guia_pruebas.md`.

Fecha: 2026-08-30 · App: `apps/convenios` · Spec: `spec/convenios_facultad_carrera.md`

## Verificación técnica (T8)

| Comando | Resultado |
|---|---|
| `makemigrations --check --dry-run` | **No changes detected** |
| `manage.py check` | **System check identified no issues (0 silenced)** |
| `spectacular --file nul` | **Errors: 0** (solo warnings preexistentes de type hints en `*_detalle`, patrón común a todo el proyecto; no introducidos por este refactor) |

## Cobertura de tareas

| Tarea | Estado | Evidencia |
|---|---|---|
| T1 — Modelo `UniversityCareer.facultad` | OK | `models.py:651-655` FK `Faculty`, `PROTECT`, `db_column="facultad_id"`, `related_name="carreras_facultad"` (único), `null=True, blank=True`, `help_text` español. `unique_together = (("universidad","carrera_profesional"),)` intacto (`:662`). `Faculty` (`:608`) definido antes de `UniversityCareer` (`:640`). Docstring en español. |
| T2 — Migración `0026_universitycareer_facultad` | OK | Depende de `0025`, único `AddField` con `null=True`, sin tocar `unique_together` ni otros modelos. Coherente con el modelo. |
| T3.1 — `UniversityCareerSerializer` | OK | `serializers.py:573-612`. `facultad` `required=True, allow_null=False`; `validate()` aplica RN-FC-02 con soporte PATCH (valor entrante o instancia); expone `universidad_detalle`, `carrera_profesional_detalle`, `facultad_detalle`. Mensaje de error en español. |
| T3.2 — Enlace al ViewSet | OK | `views.py:538-552` `UniversityCareerViewSet` hereda de `_entity_viewset(...)` (patrón `IpressViewSet`), fija `serializer_class = UniversityCareerSerializer` y `select_related`. Permisos `IsAdminRoleOrReadOnly` heredados del factory; auditoría heredada. |
| T4.1 — `FacultyCareersSyncSerializer` | OK | `serializers.py:615-624`. `carreras` = `PrimaryKeyRelatedField(queryset=ProfessionalCareer.objects.all(), many=True, allow_empty=True)`. |
| T4.2 — `FacultyViewSet` + acción `careers` | OK | `views.py:506-535`. `@action(detail=True, methods=["post"], url_path="careers")`; `exigir_roles(request, "Administrador RENADS")`; valida body; delega en el service; responde `{"carreras": [...]}`. Registrado en `ENTITY_VIEWSETS["faculties"]` (`:645`). |
| T5 — `sincronizar_carreras_facultad` | OK | `services.py:670-740`. `@transaction.atomic`; deriva universidad de facultad; upsert respetando `unique_together` (RN-FC-01); RN-FC-02 defensiva; baja por facultad (`activo=False`, sin borrado); auditoría solo ante cambio real (idempotente); devuelve activas ordenadas. |
| T6 — Filtro `facultad` | OK | `views.py:541` `filterset_fields=["universidad","carrera_profesional","facultad","activo"]`. |
| T7 — Docs | OK | `docs/db_schema_modulo_01_convenios.md:264-278` (columna `facultad_id`, reglas de unicidad/coherencia, endpoint CRUD y endpoint en lote); `docs/db_schema_er_global.md:47` (`facultad ||--o{ universidad_carrera`); `CLAUDE.md:101` (viñeta actualizada con `facultad`, validación y acción en lote). |

## Observaciones menores (no bloqueantes, informativas)

- Los campos `*_detalle` devuelven `{id, nombre}` vía `_detalle_fk` (no `{id, codigo, nombre}`). La spec (T3.1, nota) admite explícitamente esta variante; coherente con el resto de serializers del módulo. Sin acción requerida.
- Las warnings de `spectacular` sobre type hints de `SerializerMethodField` son un patrón global preexistente en el proyecto; no es defecto de este refactor.

## Reglas del proyecto

- Idioma: tablas/columnas/`help_text`/docstrings en español; clases/atributos/endpoints en inglés. Cumple.
- Arquitectura: lógica de negocio en `services` (`sincronizar_carreras_facultad`), vista delgada que solo orquesta, permisos por rol, auditoría explícita, `transaction.atomic`. Cumple.
