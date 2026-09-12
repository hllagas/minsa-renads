"""Genera las tramas Excel (.xlsx) para carga masiva de RENADS.

Archivos generados en el mismo directorio:
  - TramaCargaMasivaEstudiantes.xlsx   — carga masiva de estudiantes (POST /students/bulk-upload/)
  - TramaDeterminacionCampos.xlsx      — determinación de campos de formación (CONAPRES)
  - TramaAsignacionCampos.xlsx         — asignación de campos de formación (Gobierno Regional)
"""

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
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).parent

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

COLS_ESTUDIANTES = [
    # (nombre_columna, requerida, instruccion, ejemplo, ancho)
    (
        "tipo_documento_identidad_id",
        True,
        "Código del tipo de doc. de identidad.\nValores: DNI | CE | PASAPORTE",
        "DNI",
        22,
    ),
    (
        "numero_documento",
        True,
        "Número de documento de identidad.\nEj: 8 dígitos para DNI.",
        "74521836",
        20,
    ),
    (
        "nombres",
        True,
        "Nombres del estudiante (tal como figura en el documento).",
        "Ana María",
        20,
    ),
    (
        "apellido_paterno",
        True,
        "Apellido paterno.",
        "García",
        18,
    ),
    (
        "apellido_materno",
        False,
        "Apellido materno (dejar vacío si no aplica).",
        "López",
        18,
    ),
    (
        "fecha_nacimiento",
        False,
        "Fecha de nacimiento. Formato: YYYY-MM-DD.",
        "2000-05-14",
        18,
    ),
    (
        "sexo",
        False,
        "Sexo biológico. Valores: M | F",
        "F",
        10,
    ),
    (
        "correo",
        False,
        "Correo electrónico del estudiante.",
        "ana.garcia@uni.pe",
        28,
    ),
    (
        "telefono",
        False,
        "Teléfono de contacto (incluir código de país si es extranjero).",
        "987654321",
        18,
    ),
    (
        "direccion",
        False,
        "Dirección de residencia.",
        "Av. Universitaria 1234, Lima",
        30,
    ),
    (
        "ubigeo_id",
        False,
        "Código UBIGEO de 6 dígitos (INEI). Ej: Lima=150101.",
        "150101",
        14,
    ),
    (
        "universidad_id",
        True,
        "ID numérico o código INEI de la universidad.\nDebe coincidir con el ámbito del usuario.",
        "1",
        20,
    ),
    (
        "carrera_profesional_id",
        True,
        "ID numérico o nombre exacto de la carrera profesional.",
        "Medicina Humana",
        28,
    ),
    (
        "periodo_internado_id",
        False,
        "Código o ID del periodo de internado.\nRequerido si nivel = PREGRADO (RN-19).\nEj: 2025-I | 2025-II",
        "2025-I",
        22,
    ),
    (
        "especialidad_id",
        False,
        "Código o ID de la especialidad.\nRequerido si nivel ≠ PREGRADO (RN-19).\nDejar vacío para Pregrado.",
        "",
        22,
    ),
    (
        "nota_promedio_ponderado",
        False,
        "Nota promedio ponderado. Escala 0–20. Máx. 3 decimales.\nUsado en prelación RN-18.",
        "16.500",
        22,
    ),
    (
        "contacto_emergencia_nombre",
        False,
        "Nombre completo del contacto de emergencia.",
        "Carlos García Pérez",
        28,
    ),
    (
        "contacto_emergencia_telefono",
        False,
        "Teléfono del contacto de emergencia.",
        "999888777",
        24,
    ),
    (
        "contacto_emergencia_parentesco",
        False,
        "Código o ID del tipo de parentesco.\nValores: PADRE | MADRE | HERMANO | CONYUGE | HIJO | ABUELO | TIO | OTRO",
        "MADRE",
        28,
    ),
]


def generar_estudiantes(ruta: Path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Estudiantes"
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 50
    ws.row_dimensions[4].height = 20

    for idx, (col, req, instr, ejemplo, ancho) in enumerate(COLS_ESTUDIANTES, start=1):
        _escribir_encabezado(ws, idx, col, req)
        _escribir_tipo(ws, idx, req)
        _escribir_instruccion(ws, idx, instr)
        _escribir_ejemplo(ws, idx, ejemplo)
        _ancho(ws, idx, ancho)

    # Validación de datos — sexo
    col_sexo = next(i + 1 for i, (c, *_) in enumerate(COLS_ESTUDIANTES) if c == "sexo")
    dv_sexo = DataValidation(type="list", formula1='"M,F"', allow_blank=True, showDropDown=False)
    dv_sexo.sqref = f"{get_column_letter(col_sexo)}5:{get_column_letter(col_sexo)}10000"
    ws.add_data_validation(dv_sexo)

    # Validación de datos — tipo_documento
    col_tdoc = 1
    dv_tdoc = DataValidation(
        type="list", formula1='"DNI,CE,PASAPORTE"', allow_blank=False, showDropDown=False
    )
    dv_tdoc.sqref = f"A5:A10000"
    ws.add_data_validation(dv_tdoc)

    # Validación de datos — periodo_internado
    col_pi = next(i + 1 for i, (c, *_) in enumerate(COLS_ESTUDIANTES) if c == "periodo_internado_id")
    dv_pi = DataValidation(
        type="list",
        formula1='"2025-I,2025-II,2026-I,2026-II"',
        allow_blank=True,
        showDropDown=False,
    )
    dv_pi.sqref = f"{get_column_letter(col_pi)}5:{get_column_letter(col_pi)}10000"
    ws.add_data_validation(dv_pi)

    # Validación de datos — contacto_emergencia_parentesco
    col_par = next(i + 1 for i, (c, *_) in enumerate(COLS_ESTUDIANTES) if c == "contacto_emergencia_parentesco")
    dv_par = DataValidation(
        type="list",
        formula1='"PADRE,MADRE,HERMANO,CONYUGE,HIJO,ABUELO,TIO,OTRO"',
        allow_blank=True,
        showDropDown=False,
    )
    dv_par.sqref = f"{get_column_letter(col_par)}5:{get_column_letter(col_par)}10000"
    ws.add_data_validation(dv_par)

    _freeze(ws)

    # Hoja de referencia
    ws_ref = wb.create_sheet("Referencia")
    notas = [
        ("RENADS — Trama Carga Masiva de Estudiantes", True),
        ("", False),
        ("REGLAS IMPORTANTES:", True),
        ("• La fila 1 contiene los nombres de columna exactos que el sistema reconoce.", False),
        ("• (R) = campo requerido. Dejar vacío genera error en esa fila.", False),
        ("• (O) = campo opcional.", False),
        ("• La fila 4 es un ejemplo; puede eliminarla antes de enviar.", False),
        ("• Los datos se ingresan desde la fila 5 en adelante.", False),
        ("", False),
        ("RN-19 — Periodo de internado vs. Especialidad:", True),
        ("  • Nivel PREGRADO → periodo_internado_id REQUERIDO, especialidad_id VACÍO.", False),
        ("  • Nivel SEGUNDA_ESPECIALIDAD / MAESTRÍA / DOCTORADO → especialidad_id REQUERIDO, periodo_internado_id VACÍO.", False),
        ("", False),
        ("RN-18 — Prelación:", True),
        ("  • Los internos se asignan a los campos clínicos en orden de mayor nota_promedio_ponderado.", False),
        ("", False),
        ("RN-20 — Alcance institucional:", True),
        ("  • El usuario Universidad solo puede registrar estudiantes de las universidades de su ámbito.", False),
        ("", False),
        ("RN-21 — Unicidad:", True),
        ("  • Un estudiante con internado vigente no puede registrarse de nuevo.", False),
        ("  • Se identifica por (tipo_documento, numero_documento).", False),
        ("", False),
        ("ENDPOINT:", True),
        ("  POST /api/v1/students/bulk-upload/", False),
        ("  Content-Type: multipart/form-data   campo: archivo", False),
    ]
    ws_ref.column_dimensions["A"].width = 90
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
        "organo_directorio",
        True,
        "ID numérico del órgano directivo principal\n(GERESA/DIRESA/DIRIS/MINSA/Universidad).\nConsultar: GET /api/v1/organ-directories/",
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
        ("  • organo_directorio: categoría GOBIERNO_REGIONAL, ORGANO_MINSA o UNIVERSIDAD.", False),
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
        ("  GET /api/v1/organ-directories/     → IDs de órganos directivos", False),
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
    generar_estudiantes(HERE / "TramaCargaMasivaEstudiantes.xlsx")
    generar_determinacion(HERE / "TramaDeterminacionCamposFormacion.xlsx")
    generar_asignacion(HERE / "TramaAsignacionCamposFormacion.xlsx")
    generar_convenios(HERE / "TramaCargaMasivaConvenios.xlsx")
    print("Listo.")
