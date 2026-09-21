# Spec: Mejoras al registro de tutores

**Fecha:** 2026-09-20
**Módulo:** Internados / Tutores
**Estado de tareas:** ✅ = listo · ⬜ = pendiente

---

## Motivación

El registro de tutores necesita:
1. Subir tope de universidades por tutor de 2 → 5.
2. Limitar a 5 internos activos por tutor.
3. Endpoint de búsqueda por documento para el wizard de 2 pasos.
4. Detalles legibles (`universidades_detalle`, `tipo_documento_identidad_detalle`) en la respuesta del API.
5. Validación de alcance institucional: un usuario rol "Universidad" solo puede asignar universidades de su propio ámbito.
6. Frontend: wizard de 2 pasos en la creación de tutores (buscar → crear/asignar).
7. Frontend: columnas y form actualizados (ya implementados en sesión anterior).

---

## Tareas

### Backend

- ✅ **B1** — `services.py`: `MAX_UNIVERSIDADES_TUTOR = 2` → `5`; actualizar docstrings.
- ✅ **B2** — `serializers.py` `InternshipWriteSerializer.validate_tutor`: máximo 5 internos activos por tutor (cuenta `Internship` no terminados).
- ✅ **B3** — `views.py` `TutorViewSet`: acción `buscar/` (`GET /tutors/buscar/?tipo_documento_identidad=<id>&numero_documento=<str>`). Devuelve 200+datos si existe, 404 si no, 400 si faltan params.
- ✅ **B4** — `serializers.py` `TutorSerializer`: añadir `universidades_detalle: [{id,nombre,siglas}]` y `tipo_documento_identidad_detalle: {id,codigo,nombre}`. Actualizar `queryset` del ViewSet con `select_related("tipo_documento_identidad","profesion")`.
- ✅ **B5** — `serializers.py` `TutorSerializer.validate_universidades`: usuario rol "Universidad" solo puede incluir universidades de su propio ámbito institucional (`UserEntityProfile`). Superusuario y `Administrador RENADS` exentos.

### Frontend

- ✅ **F0** — `lib/internados/persons.ts`: columnas y form de tutores actualizados (tipo doc, N° doc, apellidos+nombres, profesión, teléfono, universidades-admin; form con secciones; label "hasta 5"). **Ya implementado.**
- ✅ **F1** — Wizard de 2 pasos en creación de tutor:
  - Paso 1: ingresar `tipo_documento_identidad` + `numero_documento` → llama `GET /tutors/buscar/?...`.
  - Paso 2a (no encontrado): form completo editable → crea tutor nuevo.
  - Paso 2b (encontrado): muestra datos protegidos (read-only) + selector de universidad (solo la del alcance del usuario) → PATCH `universidades`.
  - Componente: `components/internados/tutor-create-wizard.tsx`.
  - Integrarlo en `TutorsView` (reemplaza botón «Nuevo» estándar de `ResourceCrud`).

---

## Contrato de `buscar/`

```
GET /api/v1/tutors/buscar/?tipo_documento_identidad=<id>&numero_documento=<str>
```

| Caso | HTTP | Cuerpo |
|------|------|--------|
| Params faltantes | 400 | `{"detail": "Se requieren tipo_documento_identidad y numero_documento."}` |
| No encontrado | 404 | `{"detail": "No encontrado."}` |
| Encontrado | 200 | `TutorSerializer` completo (incluye `tipo_documento_identidad_detalle`, `universidades_detalle`, `profesion_detalle`) |

---

## Notas

- El tope de internos (B2) aplica solo a estados no terminados. Estados terminados: `CULMINADO`, `RETIRADO`, `ANULADO`. Tutor con 5 internos activos bloquea la creación de uno más.
- `universidades_detalle` usa `prefetch_related("universidades")` que ya está en el queryset.
- La migración de `MAX_UNIVERSIDADES_TUTOR` no requiere cambio de modelo ni migración Django.
