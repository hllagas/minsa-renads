# Validación — Mejora del flujo de convenios (Marco/Específico + Adendas)

> Fuente: `spec/convenios_flujo.md` (Tareas T1–T20) + puntos de decisión D1–D5.
> Resultado global: **VALIDACIÓN EXITOSA — sin errores altos/medios.** Se genera la guía
> de pruebas manuales `spec/convenios_flujo.guia_pruebas.md`.

## Sanidad técnica (solo diagnóstico)

| Comando | Resultado |
|---|---|
| `makemigrations --check --dry-run` | `No changes detected` — OK |
| `check` | `System check identified no issues (0 silenced)` — OK |
| `spectacular --file …` | **Errors: 0** (117 warnings preexistentes de type hints en `SerializerMethodField`, no bloqueantes) — OK |
| `migrate` | `No migrations to apply` (0025 / 0019 ya aplicadas) — OK |
| Seed `documento_anexo` | `[('RESOL_MARCO','CONVENIO'),('RESOL_ESPECIFICO','CONVENIO'),('RESOL_ADENDA','CONVENIO'),('RESOL_CONAPRES','CAMPO_CLINICO')]` — OK |
| `related_name='adendas'` | presente en `Convention` — OK |
| Router | `conventions/{id}/adenda`, `conventions/{id}/annex-upload`, `conventions/{id}/annex-checklist`, `clinical-field-registrations/{id}/annex-upload`/`annex-checklist` registrados — OK |

## Resultado por tarea

| Tarea | Estado | Nota |
|---|---|---|
| T1 — `Convention`: `convenio_origen`/`es_adenda`/`unidad_ejecutora`/`facultad` | OK | `models.py:748–790`; `db_column`/`on_delete=PROTECT`/`related_name` correctos; sin colisión de `related_name='convenios'`. |
| T2 — `ClinicalFieldRegistration`: resolución CONAPRES | OK | `models.py:947–954`; ambos opcionales. |
| T3 — Migración convenios `0025` | OK | `0025_convention_adenda_partes_resol_conapres.py`, dep. `0024`; 6 `AddField`. |
| T4 — `crear_adenda` | OK | `services.py:245–296`; hereda tipo/marco/universidad/UE/facultad/solicitante, `es_adenda=True`, estado `SOLICITUD_REGISTRADA`, historial + auditoría, sin límite de cadena, deriva `fecha_fin`, valida `fecha_fin > fecha_inicio`. |
| T5 — `_validar_partes_por_tipo` en crear/actualizar | OK | `services.py:110–138`, integrado en `crear_convenio` (204) y `actualizar_convenio` (313, revalida contra estado final del objeto). DIRIS sin Marco contemplado. |
| T6 — `_exigir_campos_clinicos_conapres` (gate) | OK | `services.py:141–168`; enganchado en `registrar_firma` (572, todos los tipos, early-return para no-Específico) y `cambiar_estado` cuando destino `ENVIADO_SG` (329). |
| T7 — sede pertenece a la UE del convenio | OK | `services.py:393–399`; valida solo si el convenio tiene UE (guarda contra datos previos). |
| T8 — `vigencia_efectiva` + origen `AMPLIADO` | OK | selector `selectors.py:56–78` (recorre cadena recursiva, mayor `fecha_fin` vigente); efecto en `cambiar_estado` (334–345) con guarda contra `CERRADO/ANULADO/AMPLIADO`. |
| T9 — `ConventionWriteSerializer` | OK | `serializers.py:91–99`; `unidad_ejecutora`/`facultad` opcionales; no expone `convenio_origen`/`es_adenda`. |
| T10 — `ConventionReadSerializer` | OK | `serializers.py:44–88`; `es_adenda`, `convenio_origen`, `unidad_ejecutora(+detalle)`, `facultad(+detalle)`, `adendas`, `vigencia_efectiva`. `convenios_visibles` con `select_related`/`prefetch_related` (selectors.py:23–27). |
| T11 — `ClinicalFieldRegistrationSerializer` | OK | `serializers.py:201`; ambos campos de resolución de escritura; fluyen por `**datos` en create y `editables` en update (services.py:429). |
| T12 — `ConventionFilter`: adenda | OK | `filters.py:25–26`; `es_adenda`, `convenio_origen` (más `convenio_marco` existente). |
| T13 — `ANNEX_ACTOR` (internados) | OK | `internados/models.py:73–74`; `CONVENIO`, `CAMPO_CLINICO`; cabe en `max_length=30`. |
| T14 — Migración internados `0019` | OK | `0019_annex_actor_convenio_seed.py`; `AlterField` + `RunPython`; seed idempotente `update_or_create`; `obligatorio=False`. |
| T15 — `ConventionViewSet` + `AnnexAttachmentMixin` | OK | `views.py:60,69`; `annex_actor="CONVENIO"`; permisos conservados. Ver observación L-1 (gate de ventana). |
| T16 — `ClinicalFieldRegistrationViewSet` + mixin (D2) | OK | `views.py:263,277`; `annex_actor="CAMPO_CLINICO"`. |
| T17 — Acción `conventions/{id}/adenda` | OK | `views.py:194–216`; `AdendaWriteSerializer` (`fecha_inicio` requerido), alcance por `exigir_ambito` sobre el solicitante del origen, responde 201 con `ConventionReadSerializer`. |
| T18 — `docs/db_schema_modulo_01_convenios.md` | OK | 10 menciones de los campos/reglas nuevas. |
| T19 — `docs/db_schema_modulo_02_internados.md` + almacenamiento | OK | 6 menciones (`RESOL_CONAPRES`/`CAMPO_CLINICO`/`CONVENIO`). |
| T20 — `CLAUDE.md` | OK | Reglas nuevas documentadas (partes por tipo, adendas + `vigencia_efectiva` + `AMPLIADO`, requisito CONAPRES, resolución en `campo_clinico_ipress`). |

## Reglas de negocio verificadas (services.py)

- Marco: `unidad_ejecutora`/`facultad` deben ser nulos; `universidad` obligatoria (NOT NULL) — OK.
- Específico: `convenio_marco` vigente (salvo DIRIS); `unidad_ejecutora` y `facultad` obligatorias; `facultad.universidad_id == convenio_marco.universidad_id` (o universidad propia para DIRIS sin Marco) — OK.
- `crear_adenda`: herencia completa del origen, nuevo periodo exigido, `es_adenda=True`, estado `SOLICITUD_REGISTRADA`, sin límite — OK.
- Adenda → `VIGENTE` marca origen `AMPLIADO` con guarda contra estados terminales — OK.
- `crear_registro_campo_clinico`: valida `es_sede_docente` y `ipress.unidad_ejecutora_id == convenio.unidad_ejecutora_id` (si el convenio tiene UE) — OK.
- `vigencia_efectiva`: mayor `fecha_fin` de las adendas vigentes de la cadena; fallback `fecha_fin` propia — OK.

## Confirmación de puntos de decisión

- **D1** — Confirmado: gate en `registrar_firma` (para Específicos; Marco pasa por early-return) **y** en `cambiar_estado` con destino `ENVIADO_SG`. Correcto.
- **D2** — Confirmado: `RESOL_CONAPRES` → `tipo_actor="CAMPO_CLINICO"` sobre `ClinicalFieldRegistrationViewSet`; `RESOL_MARCO/ESPECIFICO/ADENDA` → `CONVENIO` sobre `ConventionViewSet`. Correcto.
- **D3** — Confirmado: una sola migración `0019` (`AlterField` + `RunPython`). Correcto.
- **D4** — Confirmado: adenda de Marco hereda UE/facultad `None`; `crear_adenda` no revalida partes de Específico (no invoca `_validar_partes_por_tipo`). Correcto.
- **D5** — Confirmado: `actualizar_convenio` revalida partes contra el estado final del objeto (lee del objeto tras aplicar el payload). Correcto.

## Observaciones (severidad baja — no bloquean el cierre)

- **L-1 (decisión de negocio, Tarea 15).** `conventions/{id}/annex-upload` es POST y `ConventionViewSet` declara `module_content_type=("convenios","convention")`, por lo que `IsModuleEnabled` **bloquea la subida de anexos cuando el módulo de convenios está fuera de ventana** (403 `MODULO_FUERA_DE_VENTANA`), salvo superusuario/`Administrador RENADS`. La recomendación (no vinculante) del spec era permitir adjuntar anexos aun fuera de ventana. Confirmar con negocio si esto es el comportamiento deseado; si no, excluir las acciones `annex-*` del gate. Igual consideración aplica a `clinical-field-registrations/` (no declara `module_content_type`, por lo que sus annex NO se gatean — asimetría a revisar).
- **L-2 (cosmético).** El docstring de `AnnexAttachmentMixin` (`mixins.py:136–137`) aún enumera solo `INTERNO/AUTORIDAD_UNIVERSIDAD/REPRESENTANTE`; ampliar a `CONVENIO`/`CAMPO_CLINICO` para no confundir. Idéntico caso ya existía antes de esta mejora.
- **L-3 (informativo).** Marcadores `TODO(D1/D4/D5/D8/validator)` presentes en `services.py:149,253,310,333,391`, `serializers.py:73`, `views.py:201`. Todos corresponden a puntos de decisión **ya confirmados** en esta validación; pueden retirarse (o dejarse como referencia). El `TODO(D8/...)` en `cambiar_estado:333` referencia un identificador D8 inexistente en el spec (el punto real es D-menor de la Tarea 8); ya está implementado con la guarda correcta.

## Cierre

Sin errores altos/medios. Módulo apto para cierre una vez el negocio confirme L-1.
Guía de pruebas manuales generada en `spec/convenios_flujo.guia_pruebas.md`.
