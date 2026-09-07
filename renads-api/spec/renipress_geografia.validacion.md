# Validación — Normalización de la jerarquía geográfica sanitaria (RENIPRESS) — Módulo 1 `convenios`

**Fecha:** 2026-09-03
**Resultado:** ✅ **VALIDACIÓN EXITOSA** — sin errores altos/medios. Se genera la guía de pruebas manuales (`spec/renipress_geografia.guia_pruebas.md`).

## Alcance revisado

Refactor de los 3 ajustes de `spec/renipress_geografia.md` contra la spec, `docs/arquitectura_desarrollo.md` y `docs/db_schema_modulo_01_convenios.md`.

## Verificación por tarea

| Tarea | Criterio | Estado | Evidencia |
|-------|----------|--------|-----------|
| T1 | `codigo_renipress` → `unique=True`, sin `blank`, `help_text` actualizado | ✅ | `apps/convenios/models.py:371-374` |
| T2 | `Ipress.clean()` valida coherencia `microred ↔ ámbito` solo si `microred` no nula; no sobrescribe `ambito`; mensaje en español clave `microred` | ✅ | `apps/convenios/models.py:427-443` (guard `if self.microred_id and self.ambito_geografico_sanitario_id`) |
| T3 | Serializer explícito (`_IpressSerializer`) engancha la RN en create y PATCH parcial; traduce a DRF 400; conserva `*_detalle` y logo URL; `codigo_renipress` requerido | ✅ | `apps/convenios/views.py:555-614` |
| T4 | Migración `0036` = una sola `AlterField`, sin `RunPython`, depende de `0035` | ✅ | `apps/convenios/migrations/0036_alter_ipress_codigo_renipress.py` |
| T5 | Loader documental (no se implementa comando) | ✅ | Nota de mapeo RENIPRESS en `docs/db_schema_modulo_01_convenios.md:53` |
| T6 | Doc sincronizada (`codigo_renipress` unique+requerido, nota de coherencia, nota RENIPRESS/id surrogate) | ✅ | `docs/db_schema_modulo_01_convenios.md:183`, `:198`, `:53` |

## Verificaciones específicas solicitadas

1. **Coherencia microred↔ámbito en create Y PATCH parcial.** ✅ El `validate()` (`views.py:575-589`) resuelve el estado final leyendo los campos no enviados de `self.instance` vía `attrs.get("microred", getattr(self.instance, "microred", None))` y análogo para `ambito_geografico_sanitario`. En create `self.instance is None` y `getattr(None, ..., None)` devuelve `None` sin `AttributeError`. Construye una `Ipress` en memoria y llama `instance.clean()`.
2. **No rompe cuando `microred` es null.** ✅ El guard del modelo `if self.microred_id and self.ambito_geografico_sanitario_id` deja pasar el caso `microred=None`; `super().clean()` no impone otras reglas.
3. **`codigo_renipress` requerido en la API.** ✅ Confirmado en el schema OpenAPI generado: `_Ipress.required` incluye `codigo_renipress` (`schema.yml:16434`). `Patched_Ipress` (PATCH) no lo exige — correcto para actualización parcial.
4. **Migración correcta.** ✅ `AlterField` único sobre `ipress.codigo_renipress` (`unique=True`, `help_text` actualizado, sin `blank`), dependencia `0035_convention_parties_nomenclatura`, sin data migration (tabla con 0 filas).
5. **RN-25 intacta.** ✅ El ámbito directo sigue siendo la fuente autoritativa; `clean()` solo compara ids, nunca reasigna `ambito_geografico_sanitario`. `apps/internados/services.py:200` deriva de `campo_clinico.ipress.ambito_geografico_sanitario_id` directo (sin cambios).
6. **Traducción de error DRF.** ✅ El modelo lanza `ValidationError({"microred": "..."})` (dict); el serializer captura `DjangoValidationError` y usa `exc.message_dict` → respuesta 400 keyed por `microred`.
7. **Idioma/convenciones.** ✅ Clase en inglés (`_IpressSerializer`), columnas/mensajes en español, docstrings en español. Imports correctos (`from django.core.exceptions import ValidationError` en `models.py:9`; `import ValidationError as DjangoValidationError` en `views.py:4`; `from apps.convenios import models as m` en `views.py:19`).

## Sanidad técnica

| Comando | Resultado |
|---------|-----------|
| `manage.py check` | `System check identified no issues (0 silenced).` |
| `manage.py makemigrations --check --dry-run` | `No changes detected` |
| `manage.py spectacular --file schema.yml` | `Errors: 0` (126 warnings preexistentes de type-hints del patrón `_auto_serializer`, no introducidos por este cambio) |

## Notas menores (informativas, sin acción requerida)

- El warning de spectacular `IpressViewSet > _IpressSerializer: unable to resolve type hint for function "getter"` es idéntico al de los demás auto-serializers (`OrganDirectory`, `RegionalGovernment`, `University`); es una característica preexistente del patrón `_auto_serializer`, no una regresión de este refactor.
- El `_IpressSerializer` construye una `Ipress(microred=..., ambito_geografico_sanitario=...)` en memoria solo para invocar `clean()`; correcto y económico (no toca BD salvo el acceso lazy a `microred.red` cuando `microred` no es nula, aceptable en el volumen del MVP como indica la spec T2).
