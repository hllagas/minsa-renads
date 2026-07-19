"""Genera el Diccionario de Datos de RENADS en formato Word (.docx).

Fuente de verdad: los esquemas Markdown de `docs/db_schema_modulo_0{1,2,3}_*.md`.
El script parsea las tablas de campos, los catálogos y los mapas de relaciones
de cada módulo y produce un único documento `docs/diccionario_datos.docx`.

Uso:
    .venv\\Scripts\\python.exe docs\\generar_diccionario.py
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

DOCS = Path(__file__).resolve().parent

MODULOS = [
    (1, "Módulo 1 — Gestionar Convenios", DOCS / "db_schema_modulo_01_convenios.md"),
    (2, "Módulo 2 — Registrar Internados", DOCS / "db_schema_modulo_02_internados.md"),
    (3, "Módulo 3 — Registrar Actividades", DOCS / "db_schema_modulo_03_actividades.md"),
]

ER_GLOBAL = DOCS / "db_schema_er_global.md"

SALIDA = DOCS / "diccionario_datos.docx"

# --------------------------------------------------------------------------- #
# Parser Markdown
# --------------------------------------------------------------------------- #

_PLACEHOLDER = "\x00"  # marcador temporal para el pipe escapado `\|`


def limpiar(texto: str) -> str:
    """Quita backticks y normaliza espacios de una celda."""
    return texto.replace("`", "").strip()


def parse_row(linea: str) -> list[str]:
    """Convierte una fila Markdown `| a | b | c |` en lista de celdas.

    Respeta los pipes escapados `\\|` dentro de las celdas.
    """
    linea = linea.strip().replace(r"\|", _PLACEHOLDER)
    celdas = [c.replace(_PLACEHOLDER, "|").strip() for c in linea.strip("|").split("|")]
    return celdas


def es_separador(linea: str) -> bool:
    return bool(re.match(r"^\|[\s:|-]+\|?\s*$", linea.strip()))


def parse_modulo(texto: str) -> dict:
    """Devuelve estructura con catálogos, entidades, enums y mapa de relaciones."""
    lineas = texto.splitlines()
    resultado = {
        "catalogos": [],        # lista de dicts {tabla, descripcion, extra}
        "enums": [],            # lista de dicts {titulo, valores}
        "entidades": [],        # lista de dicts {nombre, campos, unicos}
        "mapa": "",             # texto del mapa de relaciones
    }

    titulo_actual: str | None = None
    i = 0
    n = len(lineas)

    while i < n:
        linea = lineas[i]
        strip = linea.strip()

        # Encabezado de tabla técnica: ### `nombre`
        m = re.match(r"^###\s+`([^`]+)`", strip)
        if m:
            titulo_actual = m.group(1)
            i += 1
            continue

        # Encabezado "Valores ... `catalogo`"
        if strip.startswith("### Valores"):
            titulo = strip.lstrip("#").strip()
            # los párrafos siguientes contienen los valores; puede haber líneas
            # en blanco intermedias. Se recolecta hasta el próximo encabezado o
            # regla horizontal `---`.
            j = i + 1
            valores_lineas = []
            while j < n and not lineas[j].startswith("#") and lineas[j].strip() != "---":
                if lineas[j].strip():
                    valores_lineas.append(lineas[j].strip())
                j += 1
            resultado["enums"].append(
                {"titulo": limpiar(titulo), "valores": " ".join(valores_lineas)}
            )
            i = j
            continue

        # Mapa de relaciones (bloque de código a continuación)
        if "Mapa de relaciones" in strip and strip.startswith("#"):
            j = i + 1
            # buscar apertura de fence ```
            while j < n and not lineas[j].strip().startswith("```"):
                j += 1
            if j < n:
                j += 1  # saltar el fence de apertura
                bloque = []
                while j < n and not lineas[j].strip().startswith("```"):
                    bloque.append(lineas[j])
                    j += 1
                resultado["mapa"] = "\n".join(bloque)
            i = j
            continue

        # Tablas Markdown: detectar por la cabecera
        if strip.startswith("|") and i + 1 < n and es_separador(lineas[i + 1]):
            cabecera = [limpiar(c) for c in parse_row(strip)]
            filas = []
            j = i + 2
            while j < n and lineas[j].strip().startswith("|"):
                filas.append(parse_row(lineas[j]))
                j += 1

            low = [c.lower() for c in cabecera]
            # Tabla de campos de entidad
            if "columna" in low and "tipo" in low and "descripción" in low:
                campos = []
                unicos = []
                for fila in filas:
                    primera = fila[0]
                    if "Único" in primera or "**Único**" in primera:
                        unicos.append(limpiar(fila[1]) if len(fila) > 1 else "")
                        continue
                    campo = limpiar(fila[0]) if len(fila) > 0 else ""
                    tipo = limpiar(fila[1]) if len(fila) > 1 else ""
                    nulo = limpiar(fila[2]) if len(fila) > 2 else ""
                    desc = limpiar(fila[3]) if len(fila) > 3 else ""
                    if campo:
                        campos.append((campo, tipo, nulo, desc))
                if titulo_actual and campos:
                    resultado["entidades"].append(
                        {"nombre": titulo_actual, "campos": campos, "unicos": unicos}
                    )
            # Tabla resumen de catálogos
            elif "tabla" in low and "descripción" in low:
                for fila in filas:
                    tabla = limpiar(fila[0]) if len(fila) > 0 else ""
                    desc = limpiar(fila[1]) if len(fila) > 1 else ""
                    extra = limpiar(fila[2]) if len(fila) > 2 else ""
                    # ignorar la tabla de "tablas nativas de Django reutilizadas"
                    if tabla and desc:
                        resultado["catalogos"].append(
                            {"tabla": tabla, "descripcion": desc, "extra": extra}
                        )
            i = j
            continue

        i += 1

    return resultado


# --------------------------------------------------------------------------- #
# Generación del documento Word
# --------------------------------------------------------------------------- #

AZUL = RGBColor(0x1F, 0x4E, 0x79)


def set_cell_bold(cell, texto: str) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(texto)
    run.bold = True
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    run.font.size = Pt(9)


def add_field_table(doc: Document, entidad: dict) -> None:
    doc.add_heading(entidad["nombre"], level=3)
    tabla = doc.add_table(rows=1, cols=4)
    try:
        tabla.style = "Light Grid Accent 1"
    except KeyError:
        tabla.style = "Table Grid"
    hdr = tabla.rows[0].cells
    for cell, texto in zip(hdr, ("Campo", "Tipo", "Nulo", "Descripción")):
        set_cell_bold(cell, texto)
    for campo, tipo, nulo, desc in entidad["campos"]:
        fila = tabla.add_row().cells
        fila[0].text = campo
        fila[1].text = tipo
        fila[2].text = nulo
        fila[3].text = desc
        for c in fila:
            for p in c.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
    if entidad["unicos"]:
        for u in entidad["unicos"]:
            p = doc.add_paragraph()
            run = p.add_run(f"Restricción única: {u}")
            run.italic = True
            run.font.size = Pt(9)
    doc.add_paragraph()


def add_catalog_table(doc: Document, catalogos: list[dict]) -> None:
    tabla = doc.add_table(rows=1, cols=3)
    try:
        tabla.style = "Light Grid Accent 1"
    except KeyError:
        tabla.style = "Table Grid"
    hdr = tabla.rows[0].cells
    for cell, texto in zip(hdr, ("Tabla", "Descripción", "Columnas adicionales")):
        set_cell_bold(cell, texto)
    for cat in catalogos:
        fila = tabla.add_row().cells
        fila[0].text = cat["tabla"]
        fila[1].text = cat["descripcion"]
        fila[2].text = cat["extra"] or "—"
        for c in fila:
            for p in c.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
    doc.add_paragraph()


def add_mapa(doc: Document, mapa: str) -> None:
    if not mapa.strip():
        return
    doc.add_heading("Mapa de relaciones", level=2)
    p = doc.add_paragraph()
    run = p.add_run(mapa)
    run.font.name = "Consolas"
    run.font.size = Pt(8)
    doc.add_paragraph()


def add_generic_table(doc: Document, header: list[str], filas: list[list[str]]) -> None:
    if not header:
        return
    tabla = doc.add_table(rows=1, cols=len(header))
    try:
        tabla.style = "Light Grid Accent 1"
    except KeyError:
        tabla.style = "Table Grid"
    for cell, texto in zip(tabla.rows[0].cells, header):
        set_cell_bold(cell, texto)
    for fila in filas:
        celdas = tabla.add_row().cells
        for i, val in enumerate(fila):
            if i < len(celdas):
                celdas[i].text = val
                for p in celdas[i].paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)
    doc.add_paragraph()


def agregar_er_global(doc: Document, ruta) -> bool:
    """Renderiza `db_schema_er_global.md` como un capítulo: encabezados, tablas y
    bloques de código (incluye el diagrama ER en Mermaid y los mapas ASCII)."""
    if not ruta.exists():
        print(f"[AVISO] No se encontró {ruta.name}, se omite el ER global.")
        return False

    doc.add_page_break()
    doc.add_heading("Diagrama Entidad-Relación (global)", level=1)

    lineas = ruta.read_text(encoding="utf-8").splitlines()
    i, n = 0, len(lineas)
    while i < n:
        linea = lineas[i]
        s = linea.strip()

        if s.startswith("# "):  # H1 (título del archivo) → ya tenemos el capítulo
            i += 1
            continue

        m = re.match(r"^(#{2,4})\s+(.*)", s)
        if m:
            nivel = min(len(m.group(1)), 4)
            doc.add_heading(limpiar(m.group(2)), level=nivel)
            i += 1
            continue

        if s.startswith("```"):
            etiqueta = s[3:].strip().lower()
            j = i + 1
            bloque = []
            while j < n and not lineas[j].strip().startswith("```"):
                bloque.append(lineas[j])
                j += 1
            if etiqueta == "mermaid":
                cap = doc.add_paragraph()
                rc = cap.add_run("Diagrama ER (fuente Mermaid — renderizable en visores Mermaid):")
                rc.italic = True
                rc.font.size = Pt(9)
            p = doc.add_paragraph()
            run = p.add_run("\n".join(bloque))
            run.font.name = "Consolas"
            run.font.size = Pt(7.5)
            doc.add_paragraph()
            i = j + 1
            continue

        if s.startswith("|") and i + 1 < n and es_separador(lineas[i + 1]):
            header = [limpiar(c) for c in parse_row(s)]
            filas = []
            j = i + 2
            while j < n and lineas[j].strip().startswith("|"):
                filas.append([limpiar(c) for c in parse_row(lineas[j])])
                j += 1
            add_generic_table(doc, header, filas)
            i = j
            continue

        if s:
            texto = s[1:].strip() if s.startswith(">") else s
            p = doc.add_paragraph(texto)
            for run in p.runs:
                run.font.size = Pt(9.5)
        i += 1

    print("[OK] Diagrama Entidad-Relación (global) agregado.")
    return True


def construir_documento() -> None:
    doc = Document()

    # Portada
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run("Diccionario de Datos")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = AZUL

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("RENADS — Registro Nacional de Articulación Docencia-Servicio en Salud")
    r.font.size = Pt(13)

    org = doc.add_paragraph()
    org.alignment = WD_ALIGN_PARAGRAPH.CENTER
    org.add_run("Ministerio de Salud del Perú (MINSA)").font.size = Pt(11)

    fecha = doc.add_paragraph()
    fecha.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fecha.add_run(f"Generado el {date.today().strftime('%d/%m/%Y')}").font.size = Pt(10)

    nota = doc.add_paragraph()
    nota.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rn = nota.add_run(
        "Fuente: esquemas de base de datos de los módulos 1, 2 y 3 y el diagrama ER global "
        "(docs/db_schema_*.md)."
    )
    rn.italic = True
    rn.font.size = Pt(9)

    doc.add_page_break()

    total_entidades = 0
    total_catalogos = 0

    for num, titulo_mod, ruta in MODULOS:
        if not ruta.exists():
            print(f"[AVISO] No se encontró {ruta.name}, se omite.")
            continue
        data = parse_modulo(ruta.read_text(encoding="utf-8"))

        doc.add_heading(titulo_mod, level=1)

        if data["catalogos"]:
            doc.add_heading("Catálogos", level=2)
            add_catalog_table(doc, data["catalogos"])
            total_catalogos += len(data["catalogos"])

        if data["enums"]:
            doc.add_heading("Valores de catálogos de estado", level=2)
            for enum in data["enums"]:
                p = doc.add_paragraph()
                r = p.add_run(enum["titulo"])
                r.bold = True
                r.font.size = Pt(10)
                pv = doc.add_paragraph(enum["valores"])
                for run in pv.runs:
                    run.font.size = Pt(9)
            doc.add_paragraph()

        if data["entidades"]:
            doc.add_heading("Entidades", level=2)
            for entidad in data["entidades"]:
                add_field_table(doc, entidad)
                total_entidades += 1

        add_mapa(doc, data["mapa"])

        print(
            f"[OK] {titulo_mod}: {len(data['catalogos'])} catálogos, "
            f"{len(data['enums'])} enums, {len(data['entidades'])} entidades."
        )

        if num != MODULOS[-1][0]:
            doc.add_page_break()

    agregar_er_global(doc, ER_GLOBAL)

    doc.save(SALIDA)
    print("-" * 60)
    print(f"Total: {total_catalogos} catálogos, {total_entidades} entidades.")
    print(f"Documento generado: {SALIDA}")


if __name__ == "__main__":
    construir_documento()
