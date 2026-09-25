"""Genera las tramas Excel (.xlsx) para carga masiva de RENADS.

Archivos generados en el mismo directorio:
  - TramaCargaMasivaEstudiantes.xlsx   — carga masiva de estudiantes (POST /students/bulk-upload/)
  - TramaDeterminacionCampos.xlsx      — determinación de campos de formación (CONAPRES)
  - TramaAsignacionCampos.xlsx         — asignación de campos de formación (Gobierno Regional)
"""

import csv
import os
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import (
    Alignment,
    Border,
    Font,
    PatternFill,
    Side,
)
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).parent

# Padrón de ubigeos usado para los cuadros combinados dependientes (mismo CSV que
# consume el cargador de la BD). Ruta: renads-api/loads/ubigeo.csv.
UBIGEO_CSV = HERE.parent.parent / "loads" / "ubigeo.csv"

# --- Cuadros combinados dependientes (espejo de apps/internados/services.py, F7) ---
# La MISMA sustitución debe aplicarse al construir el nombre del rango y en la fórmula
# INDIRECT, para que Python y Excel generen la misma clave. Asume ubigeo ASCII mayúsculas.
_RANGO_SUBS = [" ", "'", "-", ".", "(", ")", "/", ",", "&"]


def _nombre_rango(*partes) -> str:
    texto = "_".join(str(p).upper() for p in partes)
    for ch in _RANGO_SUBS:
        texto = texto.replace(ch, "_")
    return "R_" + texto


def _formula_subst(cell_ref: str) -> str:
    expr = f"UPPER({cell_ref})"
    for ch in _RANGO_SUBS:
        expr = f'SUBSTITUTE({expr},"{ch}","_")'
    return expr


def _leer_ubigeo():
    """Lee `loads/ubigeo.csv` y devuelve (deptos, prov_por_depto, dist_por_dp)."""
    deptos: list = []
    prov_por_depto: dict = {}
    dist_por_dp: dict = {}
    if not UBIGEO_CSV.exists():
        print(f"  AVISO: no se encontró {UBIGEO_CSV}; la trama saldrá sin cuadros de ubigeo.")
        return deptos, prov_por_depto, dist_por_dp
    # El padrón puede venir en UTF-8 o Latin-1 (Ñ = 0xD1); se intenta en ese orden.
    for enc in ("utf-8", "latin-1"):
        try:
            with open(UBIGEO_CSV, encoding=enc) as fh:
                filas = [
                    (r["departamento"].strip(), r["provincia"].strip(), r["distrito"].strip())
                    for r in csv.DictReader(fh, delimiter=";")
                    if str(r.get("activo", "1")).strip() not in ("0", "")
                ]
            break
        except UnicodeDecodeError:
            continue
    for depto, prov, dist in sorted(set(filas)):
        if depto not in prov_por_depto:
            prov_por_depto[depto] = []
            deptos.append(depto)
        if prov not in prov_por_depto[depto]:
            prov_por_depto[depto].append(prov)
        dist_por_dp.setdefault((depto, prov), [])
        if dist not in dist_por_dp[(depto, prov)]:
            dist_por_dp[(depto, prov)].append(dist)
    return deptos, prov_por_depto, dist_por_dp


_DJANGO_READY = None


def _bootstrap_django() -> bool:
    """Inicializa Django una sola vez para leer catálogos de la BD. False si no disponible."""
    global _DJANGO_READY
    if _DJANGO_READY is not None:
        return _DJANGO_READY
    try:
        import os
        import sys

        import django

        # La raíz del proyecto (donde vive `config/` y `manage.py`) es renads-api.
        raiz = HERE.parent.parent
        if str(raiz) not in sys.path:
            sys.path.insert(0, str(raiz))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
        django.setup()
        _DJANGO_READY = True
    except Exception as exc:  # noqa: BLE001 — dev tool: degradar a listas por defecto
        print(f"  AVISO: sin acceso a la BD ({exc}); se usan las listas por defecto.")
        _DJANGO_READY = False
    return _DJANGO_READY


def _cargar_tipos_documento():
    """Códigos de tipo de documento desde la BD (endpoint identity-document-types)."""
    if not _bootstrap_django():
        return list(TIPOS_DOCUMENTO)
    from apps.internados.models import IdentityDocumentType
    return list(
        IdentityDocumentType.objects.filter(activo=True).order_by("codigo").values_list("codigo", flat=True)
    ) or list(TIPOS_DOCUMENTO)


def _cargar_parentescos():
    """Nombres de parentesco desde la BD (tabla parentesco)."""
    if not _bootstrap_django():
        return list(PARENTESCOS)
    from apps.internados.models import RelationshipType
    return list(
        RelationshipType.objects.filter(activo=True).order_by("nombre").values_list("nombre", flat=True)
    ) or list(PARENTESCOS)


def _cargar_carreras(es_pregrado: bool):
    """Carreras (PREGRADO) o especialidades (no-PREGRADO) desde la BD. [] si no disponible."""
    if not _bootstrap_django():
        return []
    from apps.convenios.models import ProfessionalCareer, Specialty
    if es_pregrado:
        return list(
            ProfessionalCareer.objects.filter(activo=True, nivel_academico__codigo="PREGRADO")
            .order_by("nombre").values_list("nombre", flat=True)
        )
    return list(Specialty.objects.filter(activo=True).order_by("nombre").values_list("nombre", flat=True))


def _hoja_listas(wb, deptos, prov_por_depto, dist_por_dp, tipos_documento, parentescos,
                 carreras=None, nombre_carrera="CarreraProfesional"):
    """Crea la hoja oculta `_listas` con los rangos con nombre de los cuadros combinados."""
    ws = wb.create_sheet("_listas")
    ws.sheet_state = "hidden"
    estado = {"col": 1}

    def _agregar(nombre, valores):
        valores = [v for v in valores if v not in (None, "")]
        if not valores:
            return
        col = estado["col"]
        letra = get_column_letter(col)
        for i, valor in enumerate(valores, start=1):
            ws.cell(row=i, column=col, value=valor)
        ref = f"'_listas'!${letra}$1:${letra}${len(valores)}"
        wb.defined_names.add(DefinedName(nombre, attr_text=ref))
        estado["col"] = col + 1

    _agregar("Departamentos", deptos)
    for depto in deptos:
        _agregar(_nombre_rango(depto), prov_por_depto[depto])
    for (depto, prov), distritos in dist_por_dp.items():
        _agregar(_nombre_rango(depto, prov), distritos)
    _agregar("TipoDocumento", tipos_documento)
    _agregar("Parentesco", parentescos)
    if carreras:
        _agregar(nombre_carrera, carreras)

# ── Paleta ────────────────────────────────────────────────────────────────────
AZUL_HEADER  = "1F4E79"   # fondo encabezado principal
AZUL_REQ     = "D6E4F0"   # fondo columna requerida
GRIS_OPC     = "F5F5F5"   # fondo columna opcional
VERDE_DATOS  = "E8F5E9"   # fondo fila de ejemplo
AMARILLO     = "FFF9C4"   # fondo fila de instrucciones
ROJO_REQ     = "C00000"   # texto etiqueta (R)
VERDE_OPC    = "2D6A4F"   # texto etiqueta (O)

def _font(bold=False, color="000000", size=10, italic=False):
    return Font(name="Calibri", bold=bold, color=color, size=size, italic=italic)

def _fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def _border():
    thin = Side(style="thin", color="BDBDBD")
    return Border(left=thin, right=thin, top=thin, bottom=thin)

def _center(wrap=True):
    return Alignment(horizontal="center", vertical="center", wrap_text=wrap)

def _left(wrap=True):
    return Alignment(horizontal="left", vertical="center", wrap_text=wrap)


def _escribir_encabezado(ws, col_idx, texto, requerida=True):
    """Fila 1: nombre de la columna con color según obligatoriedad."""
    cell = ws.cell(row=1, column=col_idx, value=texto)
    cell.font = _font(bold=True, color="FFFFFF", size=10)
    cell.fill = _fill(AZUL_HEADER)
    cell.alignment = _center()
    cell.border = _border()


def _escribir_tipo(ws, col_idx, requerida=True):
    """Fila 2: etiqueta (R) o (O)."""
    label = "(R) Requerido" if requerida else "(O) Opcional"
    color = ROJO_REQ if requerida else VERDE_OPC
    cell = ws.cell(row=2, column=col_idx, value=label)
    cell.font = _font(bold=True, color=color, size=9)
    cell.fill = _fill(AZUL_REQ if requerida else GRIS_OPC)
    cell.alignment = _center()
    cell.border = _border()


def _escribir_instruccion(ws, col_idx, texto):
    """Fila 3: descripción / formato esperado."""
    cell = ws.cell(row=3, column=col_idx, value=texto)
    cell.font = _font(size=9, italic=True)
    cell.fill = _fill(AMARILLO)
    cell.alignment = _left()
    cell.border = _border()


def _escribir_ejemplo(ws, col_idx, valor):
    """Fila 4: fila de ejemplo."""
    cell = ws.cell(row=4, column=col_idx, value=valor)
    cell.font = _font(italic=True, color="1B5E20", size=10)
    cell.fill = _fill(VERDE_DATOS)
    cell.alignment = _center()
    cell.border = _border()


def _ancho(ws, col_idx, ancho):
    ws.column_dimensions[get_column_letter(col_idx)].width = ancho


def _freeze(ws):
    ws.freeze_panes = "A5"


def _titulo_hoja(ws, texto):
    """Celdas fusionadas arriba de todo (encima de la fila 1)."""
    pass  # dejamos encabezado en fila 1


# ═════════════════════════════════════════════════════════════════════════════
# 1. TRAMA CARGA MASIVA DE ESTUDIANTES
# ═════════════════════════════════════════════════════════════════════════════

# Catálogos de las listas simples (deben coincidir con las semillas de la BD).
TIPOS_DOCUMENTO = ["DNI", "CE"]
PARENTESCOS = ["Padre", "Madre", "Hermano/a", "Cónyuge", "Hijo/a", "Abuelo/a", "Tío/a", "Otro"]

# Fila final de datos con cuadros combinados (espejo de services._TRAMA_FILAS_DATOS).
_FILAS_DATOS = 500


def _cols_estudiantes(es_pregrado: bool):
    """Columnas de la trama de estudiantes (espejo de services.generar_trama_excel).

    `universidad` y `periodo_internado` NO son columnas: se toman de los filtros de la
    UI. Devuelve una lista de (clave_interna, etiqueta_encabezado, ancho).
    """
    cols = [
        ("tipo_documento",    "tipo_documento\n(elija de la lista)",            22),
        ("numero_documento",  "numero_documento\n(8 dígitos DNI, 9 los demás)", 24),
        ("apellido_paterno",  "apellido_paterno",                               18),
        ("apellido_materno",  "apellido_materno",                               18),
        ("nombres",           "nombres",                                        20),
        ("fecha_nacimiento",  "fecha_nacimiento\n(dd/mm/yyyy)",                 18),
        ("sexo",              "sexo\n(M / F)",                                  10),
        ("correo",            "correo personal",                                26),
        ("telefono",          "teléfono móvil",                                 16),
        ("direccion",         "direccion",                                      30),
        ("departamento",      "Región\n(elija de la lista)",                    20),
        ("provincia",         "provincia\n(elija de la lista)",                 20),
        ("distrito",          "distrito\n(elija de la lista)",                  20),
    ]
    if es_pregrado:
        cols.append(("carrera_profesional", "carrera_profesional\n(elija de la lista)", 28))
    else:
        cols.append(("especialidad", "especialidad\n(elija de la lista)", 28))
    cols += [
        ("nota_promedio_ponderado",        "nota_promedio_ponderado\n(0–20, hasta 4 decimales)", 22),
        ("contacto_emergencia_nombre",     "contacto_emergencia_nombre",                         28),
        ("contacto_emergencia_telefono",   "contacto_emergencia_telefono",                       24),
        ("contacto_emergencia_parentesco", "contacto_emergencia_parentesco\n(elija de la lista)", 28),
    ]
    return cols


def generar_estudiantes(ruta: Path, es_pregrado: bool = True):
    """Genera la trama de estudiantes con cuadros combinados dependientes (F7).

    Espejo de `apps/internados/services.generar_trama_excel` — **fuente de verdad**; ante
    dudas regenerar desde el endpoint `GET /api/v1/students/bulk-template`.
    """
    columnas = _cols_estudiantes(es_pregrado)
    deptos, prov_por_depto, dist_por_dp = _leer_ubigeo()
    carreras = _cargar_carreras(es_pregrado)
    tipos_documento = _cargar_tipos_documento()
    parentescos = _cargar_parentescos()
    clave_nivel = "carrera_profesional" if es_pregrado else "especialidad"
    nombre_rango_carrera = "CarreraProfesional" if es_pregrado else "Especialidad"

    wb = Workbook()
    ws = wb.active
    ws.title = "Estudiantes"
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 42

    letra_de = {}
    for idx, (clave, etiqueta, ancho) in enumerate(columnas, start=1):
        letra_de[clave] = get_column_letter(idx)
        cell = ws.cell(row=1, column=idx, value=etiqueta)
        cell.font = _font(bold=True, color="FFFFFF", size=10)
        cell.fill = _fill(AZUL_HEADER)
        cell.alignment = _center()
        cell.border = _border()
        _ancho(ws, idx, ancho)

    # Hoja oculta con las listas y los rangos con nombre.
    _hoja_listas(wb, deptos, prov_por_depto, dist_por_dp, tipos_documento, parentescos,
                 carreras=carreras, nombre_carrera=nombre_rango_carrera)

    fila_ini, fila_fin = 2, 1 + _FILAS_DATOS

    def _dv(clave, *, tipo, formula1):
        letra = letra_de.get(clave)
        if not letra:
            return
        formula1 = formula1[1:] if formula1.startswith("=") else formula1
        dv = DataValidation(type=tipo, formula1=formula1, allow_blank=True,
                            showErrorMessage=True, showDropDown=False)
        ws.add_data_validation(dv)
        dv.add(f"{letra}{fila_ini}:{letra}{fila_fin}")

    dep, prov = letra_de["departamento"], letra_de["provincia"]
    tdoc, ndoc = letra_de["tipo_documento"], letra_de["numero_documento"]
    correo, tel = letra_de["correo"], letra_de["telefono"]
    ctel = letra_de["contacto_emergencia_telefono"]

    _dv("tipo_documento", tipo="list", formula1="=TipoDocumento")
    _dv("contacto_emergencia_parentesco", tipo="list", formula1="=Parentesco")
    _dv("sexo", tipo="list", formula1='"M,F"')
    if carreras:
        _dv(clave_nivel, tipo="list", formula1=f"={nombre_rango_carrera}")
    _dv("departamento", tipo="list", formula1="=Departamentos")
    _dv("provincia", tipo="list", formula1=f'=INDIRECT("R_"&{_formula_subst(f"${dep}{fila_ini}")})')
    _dv("distrito", tipo="list", formula1=(
        f'=INDIRECT("R_"&{_formula_subst(f"${dep}{fila_ini}")}'
        f'&"_"&{_formula_subst(f"${prov}{fila_ini}")})'))
    # numero_documento: TEXTO solo dígitos 0-9 (conserva ceros a la izquierda), long. 8/9.
    _celda_num = f"${ndoc}{fila_ini}"
    _solo_digitos = (
        f'SUMPRODUCT(--ISNUMBER(--MID({_celda_num},ROW(INDIRECT("1:"&LEN({_celda_num}))),1)))=LEN({_celda_num})'
    )
    _dv("numero_documento", tipo="custom",
        formula1=f'=AND(LEN({_celda_num})=IF(${tdoc}{fila_ini}="DNI",8,9),{_solo_digitos})')
    for _fila in range(fila_ini, fila_fin + 1):
        ws[f"{ndoc}{_fila}"].number_format = "@"
    _dv("correo", tipo="custom",
        formula1=(f'=OR(LEN(${correo}{fila_ini})=0,'
                  f'AND(ISNUMBER(SEARCH("@",${correo}{fila_ini})),'
                  f'ISNUMBER(SEARCH(".",${correo}{fila_ini}))))'))
    _dv("telefono", tipo="custom", formula1=f'=OR(LEN(${tel}{fila_ini})=0,ISNUMBER(-${tel}{fila_ini}))')
    _dv("contacto_emergencia_telefono", tipo="custom",
        formula1=f'=OR(LEN(${ctel}{fila_ini})=0,ISNUMBER(-${ctel}{fila_ini}))')
    nota = letra_de["nota_promedio_ponderado"]
    _nota = f"${nota}{fila_ini}"
    _dv("nota_promedio_ponderado", tipo="custom",
        formula1=f'=OR(LEN({_nota})=0,AND(ISNUMBER({_nota}),{_nota}>=0,{_nota}<=20,ROUND({_nota},4)={_nota}))')

    # Hoja de instrucciones.
    nivel_txt = "PREGRADO" if es_pregrado else "no-PREGRADO (segunda especialidad / maestría / doctorado)"
    ws_ref = wb.create_sheet("Instrucciones")
    tipos_txt = ", ".join(tipos_documento) or "—"
    notas = [
        ("RENADS — Trama Carga Masiva de Estudiantes", True),
        (f"Nivel académico de esta trama: {nivel_txt}", False),
        ("Todos los campos son obligatorios.", False),
        ("", False),
        ("REGLAS IMPORTANTES:", True),
        ("• La fila 1 son los encabezados que el sistema reconoce; los datos van desde la fila 2.", False),
        ("• tipo_documento, sexo, Región, provincia, distrito, parentesco y carrera/especialidad se ELIGEN de la lista.", False),
        (f"• tipo_documento: {tipos_txt} (según el catálogo vigente).", False),
        ("• Región → provincia → distrito son cuadros combinados EN CASCADA.", False),
        ("• numero_documento: texto de solo dígitos 0-9 (conserva ceros a la izquierda); 8 si es DNI, 9 para otro tipo.", False),
        ("• correo personal: formato usuario@dominio.  teléfono móvil: solo dígitos.", False),
        ("• La universidad y el periodo de internado NO son columnas: se eligen en la pantalla de carga.", False),
        ("", False),
        ("CARGA EN DOS PASOS:", True),
        ("  1. POST /api/v1/students/bulk-validate  → valida y resalta las celdas con errores.", False),
        ("  2. POST /api/v1/students/bulk-upload    → crea todo (solo si no hay errores).", False),
        ("", False),
        ("RN-19 — Nivel vs. periodo/especialidad:", True),
        ("  • PREGRADO → periodo de internado (en pantalla), sin especialidad.", False),
        ("  • no-PREGRADO → columna 'especialidad' requerida, sin periodo.", False),
        ("RN-18 — Prelación por mayor nota_promedio_ponderado.", False),
        ("RN-21 — Unicidad por (tipo_documento, numero_documento).", False),
    ]
    ws_ref.column_dimensions["A"].width = 95
    for fila, (texto, negrita) in enumerate(notas, start=1):
        c = ws_ref.cell(row=fila, column=1, value=texto)
        c.font = _font(bold=negrita, size=10)
        c.alignment = _left(wrap=False)

    wb.save(ruta)
    print(f"  OK  {ruta.name}")


# ═════════════════════════════════════════════════════════════════════════════
# 2. TRAMA DETERMINACIÓN DE CAMPOS DE FORMACIÓN (CONAPRES)
# ═════════════════════════════════════════════════════════════════════════════

COLS_DETERMINACION = [
    (
        "ipress",
        True,
        "Código RENIPRESS de 8 caracteres de la sede docente\n(ipress.es_sede_docente debe ser True).",
        "00123456",
        22,
    ),
    (
        "carrera_profesional",
        True,
        "ID numérico o nombre exacto de la carrera profesional.",
        "Medicina Humana",
        28,
    ),
    (
        "especialidad",
        False,
        "ID o código de la especialidad.\nDejar vacío si la carrera no tiene especialidad asociada.",
        "",
        18,
    ),
    (
        "campos_clinicos_registrados",
        True,
        "Total de campos clínicos disponibles en esta sede\npara esta carrera. Entero ≥ 1.",
        "10",
        26,
    ),
    (
        "numero_resolucion_conapres",
        False,
        "Número de la resolución CONAPRES que aprueba los\ncampos clínicos. Máx. 100 caracteres.\nSin este dato el convenio no puede avanzar a suscripción.",
        "RD-CONAPRES-2025-0042",
        30,
    ),
    (
        "fecha_resolucion_conapres",
        False,
        "Fecha de la resolución CONAPRES. Formato: YYYY-MM-DD.",
        "2025-03-10",
        26,
    ),
]


def generar_determinacion(ruta: Path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Determinación Campos"
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 55
    ws.row_dimensions[4].height = 20

    for idx, (col, req, instr, ejemplo, ancho) in enumerate(COLS_DETERMINACION, start=1):
        _escribir_encabezado(ws, idx, col, req)
        _escribir_tipo(ws, idx, req)
        _escribir_instruccion(ws, idx, instr)
        _escribir_ejemplo(ws, idx, ejemplo)
        _ancho(ws, idx, ancho)

    _freeze(ws)

    # Hoja de referencia
    ws_ref = wb.create_sheet("Referencia")
    notas = [
        ("RENADS — Trama Determinación de Campos de Formación (CONAPRES)", True),
        ("", False),
        ("ROLES RESPONSABLES: CONAPRES / Administrador RENADS", True),
        ("", False),
        ("REGLAS IMPORTANTES:", True),
        ("• Cada fila registra el total de campos clínicos disponibles para una sede + carrera.", False),
        ("• La IPRESS debe ser una sede docente (ipress.es_sede_docente = True).", False),
        ("• El registro es global por sede + carrera (no está ligado a un convenio específico).", False),
        ("", False),
        ("REQUISITO PREVIO A SUSCRIPCIÓN:", True),
        ("  El convenio Específico no puede avanzar a suscripción sin ≥1 registro con", False),
        ("  numero_resolucion_conapres no vacío sobre sede docente de su unidad ejecutora.", False),
        ("", False),
        ("EFECTO EN DISPONIBILIDAD:", True),
        ("  disponibilidad = campos_clinicos_registrados − Σ campos_clinicos_autorizados (asignaciones)", False),
        ("", False),
        ("ENDPOINT (carga masiva):", True),
        ("  POST /api/v1/clinical-field-registrations/bulk-upload/", False),
        ("  Roles con acceso: CONAPRES, Administrador RENADS.", False),
        ("", False),
        ("ENDPOINT (registro individual):", True),
        ("  POST /api/v1/clinical-field-registrations/", False),
        ("  Adjuntar resolución PDF: POST /api/v1/clinical-field-registrations/{id}/annex-upload/", False),
    ]
    ws_ref.column_dimensions["A"].width = 90
    for fila, (texto, negrita) in enumerate(notas, start=1):
        c = ws_ref.cell(row=fila, column=1, value=texto)
        c.font = _font(bold=negrita, size=10)
        c.alignment = _left(wrap=False)

    wb.save(ruta)
    print(f"  OK  {ruta.name}")


# ═════════════════════════════════════════════════════════════════════════════
# 3. TRAMA ASIGNACIÓN DE CAMPOS DE FORMACIÓN (GOBIERNO REGIONAL)
# ═════════════════════════════════════════════════════════════════════════════

COLS_ASIGNACION = [
    (
        "campo_clinico_ipress",
        True,
        "ID del registro de campo clínico (ClinicalFieldRegistration).\nObtenible en GET /api/v1/clinical-field-registrations/",
        "15",
        28,
    ),
    (
        "convenio",
        True,
        "ID del Convenio Específico de la universidad a asignar.\nDebe estar vigente y pertenecer a una universidad con\nconvenio en el mismo ámbito geográfico sanitario.",
        "42",
        14,
    ),
    (
        "campos_clinicos_autorizados",
        True,
        "Cupos asignados a esta universidad para esta sede + carrera.\nEntero ≥ 1. No puede superar la disponibilidad del registro padre\n(campos_clinicos_registrados − Σ ya asignados).",
        "3",
        28,
    ),
    (
        "fecha_inicio",
        False,
        "Fecha de inicio de la asignación. Formato: YYYY-MM-DD.\n(Opcional según implementación del convenio.)",
        "2025-04-01",
        18,
    ),
    (
        "fecha_fin",
        False,
        "Fecha de fin de la asignación. Formato: YYYY-MM-DD.",
        "2025-12-31",
        18,
    ),
]


def generar_asignacion(ruta: Path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Asignación Campos"
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 60
    ws.row_dimensions[4].height = 20

    for idx, (col, req, instr, ejemplo, ancho) in enumerate(COLS_ASIGNACION, start=1):
        _escribir_encabezado(ws, idx, col, req)
        _escribir_tipo(ws, idx, req)
        _escribir_instruccion(ws, idx, instr)
        _escribir_ejemplo(ws, idx, ejemplo)
        _ancho(ws, idx, ancho)

    _freeze(ws)

    # Hoja de referencia
    ws_ref = wb.create_sheet("Referencia")
    notas = [
        ("RENADS — Trama Asignación de Campos de Formación (Gobierno Regional)", True),
        ("", False),
        ("ROL RESPONSABLE: Gobierno Regional (GERESA / DIRESA / DIRIS)", True),
        ("", False),
        ("FLUJO PREVIO REQUERIDO:", True),
        ("  1. CONAPRES debe haber registrado campos clínicos para la sede + carrera.", False),
        ("  2. El Convenio Específico de la universidad debe estar vigente.", False),
        ("  3. La universidad debe tener convenio en el mismo ámbito geográfico sanitario.", False),
        ("", False),
        ("REGLAS IMPORTANTES:", True),
        ("• El campo `ipress`, `carrera_profesional`, `universidad` se DERIVAN automáticamente", False),
        ("  del registro padre (campo_clinico_ipress) y del convenio; no se ingresan.", False),
        ("• La suma de campos_clinicos_autorizados de todas las asignaciones de un mismo", False),
        ("  registro padre no puede superar campos_clinicos_registrados.", False),
        ("• Cada combinación (campo_clinico_ipress × universidad) debe ser única.", False),
        ("", False),
        ("RELACIÓN CON INTERNOS:", True),
        ("  Los internos (tabla `interno`) referencian esta asignación en `campo_clinico_id`.", False),
        ("  El número de internos no puede superar campos_clinicos_autorizados (RN-13).", False),
        ("", False),
        ("ENDPOINT:", True),
        ("  POST /api/v1/clinical-field-allocations/", False),
        ("  Solo escritura con grupo 'Gobierno Regional'.", False),
    ]
    ws_ref.column_dimensions["A"].width = 90
    for fila, (texto, negrita) in enumerate(notas, start=1):
        c = ws_ref.cell(row=fila, column=1, value=texto)
        c.font = _font(bold=negrita, size=10)
        c.alignment = _left(wrap=False)

    wb.save(ruta)
    print(f"  OK  {ruta.name}")


# ═════════════════════════════════════════════════════════════════════════════
# 4. TRAMA CARGA MASIVA DE CONVENIOS (ADMINISTRADOR RENADS)
# ═════════════════════════════════════════════════════════════════════════════

COLS_CONVENIOS = [
    (
        "tipo_convenio",
        True,
        "Tipo de convenio. Valores: MARCO | ESPECIFICO",
        "MARCO",
        16,
    ),
    (
        "titulo",
        True,
        "Título / denominación oficial del convenio.",
        "Convenio Marco entre GORE Junín y UNCP",
        50,
    ),
    (
        "unidad_organica",
        True,
        "ID numérico de la unidad orgánica principal\n(GERESA/DIRESA/DIRIS/MINSA/Universidad).\nConsultar: GET /api/v1/organic-units/",
        "12",
        22,
    ),
    (
        "universidad",
        True,
        "ID numérico o código INEI de la universidad.",
        "5",
        18,
    ),
    (
        "convenio_marco",
        False,
        "ID del Convenio Marco vigente.\nRequerido para ESPECIFICO (salvo DIRIS).\nDejar vacío para MARCO.",
        "",
        18,
    ),
    (
        "gobierno_regional",
        False,
        "ID del Gobierno Regional.\nSolo para Convenio Marco de GOBIERNO_REGIONAL.\nDejar vacío en otros casos.",
        "3",
        20,
    ),
    (
        "unidad_ejecutora",
        False,
        "ID o código de la Unidad Ejecutora.\nRequerido para ESPECIFICO.",
        "010101",
        20,
    ),
    (
        "facultad",
        False,
        "ID numérico de la Facultad.\nRequerido para ESPECIFICO.\nDebe pertenecer a la universidad del convenio.",
        "8",
        16,
    ),
    (
        "nomenclatura",
        False,
        "Nomenclatura oficial asignada por DIGEP.\nSolo aplica a Convenio Marco.",
        "CM-GORE-JUN-UNCP-2023-001",
        28,
    ),
    (
        "fecha_solicitud",
        True,
        "Fecha de solicitud/registro. Formato: YYYY-MM-DD.",
        "2023-03-15",
        18,
    ),
    (
        "fecha_inicio",
        False,
        "Fecha de inicio de vigencia. Formato: YYYY-MM-DD.",
        "2023-06-01",
        18,
    ),
    (
        "fecha_fin",
        False,
        "Fecha de fin de vigencia. Formato: YYYY-MM-DD.",
        "2026-05-31",
        18,
    ),
    (
        "estado_destino",
        False,
        "Estado en que se registrará el convenio.\nValores: VIGENTE | PUBLICADO\nDefault: PUBLICADO",
        "PUBLICADO",
        18,
    ),
]


def generar_convenios(ruta: Path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Convenios"
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 55
    ws.row_dimensions[4].height = 20

    for idx, (col, req, instr, ejemplo, ancho) in enumerate(COLS_CONVENIOS, start=1):
        _escribir_encabezado(ws, idx, col, req)
        _escribir_tipo(ws, idx, req)
        _escribir_instruccion(ws, idx, instr)
        _escribir_ejemplo(ws, idx, ejemplo)
        _ancho(ws, idx, ancho)

    # Validación — tipo_convenio
    dv_tipo = DataValidation(type="list", formula1='"MARCO,ESPECIFICO"', allow_blank=False, showDropDown=False)
    dv_tipo.sqref = "A5:A10000"
    ws.add_data_validation(dv_tipo)

    # Validación — estado_destino
    col_est = next(i + 1 for i, (c, *_) in enumerate(COLS_CONVENIOS) if c == "estado_destino")
    dv_est = DataValidation(type="list", formula1='"VIGENTE,PUBLICADO"', allow_blank=True, showDropDown=False)
    dv_est.sqref = f"{get_column_letter(col_est)}5:{get_column_letter(col_est)}10000"
    ws.add_data_validation(dv_est)

    _freeze(ws)

    ws_ref = wb.create_sheet("Referencia")
    notas = [
        ("RENADS — Trama Carga Masiva de Convenios", True),
        ("", False),
        ("ROL RESPONSABLE: Administrador RENADS (acceso exclusivo)", True),
        ("", False),
        ("ENDPOINT:", True),
        ("  POST /api/v1/conventions/bulk-upload/", False),
        ("  Content-Type: multipart/form-data   campo: archivo", False),
        ("", False),
        ("REGLAS IMPORTANTES:", True),
        ("• Esta trama es para registrar convenios YA SUSCRITOS Y PUBLICADOS (carga histórica).", False),
        ("• El sistema los crea directamente en el estado indicado (PUBLICADO por defecto).", False),
        ("• No pasan por el flujo de aprobación (DIGEP/OGAJ/CONAPRES).", False),
        ("", False),
        ("REGLAS POR TIPO DE CONVENIO:", True),
        ("MARCO:", True),
        ("  • unidad_organica: categoría GOBIERNO_REGIONAL, ORGANO_MINSA o UNIVERSIDAD.", False),
        ("  • gobierno_regional: requerido si el órgano es GOBIERNO_REGIONAL.", False),
        ("  • convenio_marco, unidad_ejecutora, facultad: deben estar VACÍOS.", False),
        ("  • nomenclatura: asignada por DIGEP (opcional).", False),
        ("", False),
        ("ESPECIFICO:", True),
        ("  • convenio_marco: requerido salvo DIRIS (MINSA_DIRIS).", False),
        ("  • unidad_ejecutora + facultad: REQUERIDOS.", False),
        ("  • facultad.universidad debe coincidir con el campo universidad (RN-FC-02).", False),
        ("  • gobierno_regional: dejar vacío.", False),
        ("", False),
        ("CÓMO OBTENER LOS IDs:", True),
        ("  GET /api/v1/organic-units/     → IDs de unidades orgánicas", False),
        ("  GET /api/v1/universities/          → IDs y código INEI de universidades", False),
        ("  GET /api/v1/executing-units/       → IDs y códigos de unidades ejecutoras", False),
        ("  GET /api/v1/faculties/             → IDs de facultades", False),
        ("  GET /api/v1/regional-governments/  → IDs de gobiernos regionales", False),
        ("  GET /api/v1/conventions/           → IDs de convenios Marco existentes", False),
    ]
    ws_ref.column_dimensions["A"].width = 90
    for fila, (texto, negrita) in enumerate(notas, start=1):
        c = ws_ref.cell(row=fila, column=1, value=texto)
        c.font = _font(bold=negrita, size=10)
        c.alignment = _left(wrap=False)

    wb.save(ruta)
    print(f"  OK  {ruta.name}")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generando tramas RENADS…")
    generar_estudiantes(HERE / "TramaCargaMasivaEstudiantes_PREGRADO.xlsx", es_pregrado=True)
    generar_estudiantes(HERE / "TramaCargaMasivaEstudiantes_noPREGRADO.xlsx", es_pregrado=False)
    generar_determinacion(HERE / "TramaDeterminacionCamposFormacion.xlsx")
    generar_asignacion(HERE / "TramaAsignacionCamposFormacion.xlsx")
    generar_convenios(HERE / "TramaCargaMasivaConvenios.xlsx")
    print("Listo.")
