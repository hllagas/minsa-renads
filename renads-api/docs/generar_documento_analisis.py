"""
Genera RENADS_Analisis_Diseno.docx con documentación completa de análisis y diseño.
Ejecutar desde la raíz del proyecto con el venv activado:
    python docs/generar_documento_analisis.py
"""
import io
import os
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines
import numpy as np

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ─── Constantes de color ──────────────────────────────────────────────────────
AZUL_MINSA   = "#1565C0"
AZUL_CLARO   = "#E3F2FD"
VERDE        = "#2E7D32"
GRIS_TABLA   = "#F5F5F5"
ROJO_TENUE   = "#FFEBEE"

OUT_PATH = Path(__file__).parent / "RENADS_Analisis_Diseno.docx"


# ══════════════════════════════════════════════════════════════════════════════
# UTILIDADES DOCX
# ══════════════════════════════════════════════════════════════════════════════

def set_cell_bg(cell, hex_color: str):
    """Rellena el fondo de una celda con color hex (sin #)."""
    hex_color = hex_color.lstrip("#")
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return p


def add_paragraph(doc, text, bold=False, italic=False, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Inches(0.3)
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    return p


def add_table_header(table, headers, bg="#1565C0"):
    row = table.rows[0]
    for i, h in enumerate(headers):
        cell = row.cells[i]
        cell.text = h
        set_cell_bg(cell, bg)
        for para in cell.paragraphs:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in para.runs:
                run.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                run.font.size = Pt(9)


def add_table_row(table, values, bg=None, bold_first=False):
    row = table.add_row()
    for i, v in enumerate(values):
        cell = row.cells[i]
        cell.text = str(v)
        if bg:
            set_cell_bg(cell, bg)
        for para in cell.paragraphs:
            for run in para.runs:
                run.font.size = Pt(9)
                if bold_first and i == 0:
                    run.bold = True
    return row


def embed_figure(doc, fig, width_inches=6.5, caption=None):
    """Guarda figura matplotlib en buffer y la inserta en el doc."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    doc.add_picture(buf, width=Inches(width_inches))
    last = doc.paragraphs[-1]
    last.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        cp = doc.add_paragraph(caption)
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in cp.runs:
            run.italic = True
            run.font.size = Pt(9)


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAMAS MATPLOTLIB
# ══════════════════════════════════════════════════════════════════════════════

def fig_package_diagram():
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_facecolor("#FAFAFA")
    fig.patch.set_facecolor("#FAFAFA")

    def pkg(x, y, w, h, name, sub="", color="#1565C0", textcolor="white"):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                              linewidth=1.5, edgecolor=color,
                              facecolor=color if sub == "" else "#E3F2FD")
        ax.add_patch(rect)
        # pestaña superior
        tab = FancyBboxPatch((x, y+h-0.3), min(w*0.55, 2.2), 0.3,
                             boxstyle="round,pad=0.05",
                             linewidth=1, edgecolor=color, facecolor=color)
        ax.add_patch(tab)
        ax.text(x + min(w*0.55, 2.2)/2, y+h-0.15, "«package»",
                ha="center", va="center", fontsize=6, color="white")
        ax.text(x + w/2, y + h/2 + 0.1, name,
                ha="center", va="center", fontsize=9, fontweight="bold",
                color=color if sub else textcolor)
        if sub:
            ax.text(x + w/2, y + h/2 - 0.25, sub,
                    ha="center", va="center", fontsize=7, color="#555")

    # config
    pkg(0.3, 6.2, 2.2, 1.4, "config", "settings / urls\nwsgi / asgi", "#37474F")
    # common
    pkg(0.3, 4.4, 2.2, 1.4, "apps.common", "auth · perfiles\nauditoría · storage", "#6A1B9A")
    # módulos dominio
    pkg(3.2, 5.5, 2.4, 2.0, "apps.convenios", "M1 – Gestionar\nConvenios")
    pkg(6.0, 5.5, 2.4, 2.0, "apps.internados", "M2 – Registrar\nInternados")
    pkg(8.8, 5.5, 2.4, 2.0, "apps.actividades", "M3 – Registrar\nActividades")
    pkg(6.0, 3.2, 2.4, 1.8, "apps.calendario", "M4 – Calendario\nAdministrativo")
    # productos
    pkg(3.2, 3.2, 2.4, 1.8, "apps.common\n(permisos)", "IsModuleEnabled\nIsConapresOrReadOnly", "#01579B")

    # dependencias
    arrows = [
        (1.4, 6.2, 1.4, 5.8),          # config → common
        (2.5, 5.1, 3.2, 6.5),           # common → convenios
        (2.5, 5.1, 6.0, 6.5),           # common → internados
        (2.5, 5.1, 8.8, 6.5),           # common → actividades
        (2.5, 5.1, 6.0, 4.1),           # common → calendario
        (5.6, 6.5, 6.0, 6.5),           # convenios → internados
        (8.4, 6.5, 8.8, 6.5),           # internados → actividades
        (7.2, 5.5, 7.2, 5.0),           # internados → calendario
    ]
    for x1, y1, x2, y2 in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#555",
                                   lw=1.2, connectionstyle="arc3,rad=0.0"))

    # leyenda
    ax.text(6.0, 0.4, "«use»  →  dependencia entre paquetes",
            fontsize=8, color="#555", style="italic")
    ax.set_title("Diagrama de Paquetes — RENADS", fontsize=13,
                 fontweight="bold", pad=10, color="#1565C0")
    return fig


def fig_usecase(title, actors, usecases, links, actor_colors=None):
    """
    actors: [(name, x, y), ...]
    usecases: [(name, x, y), ...]
    links: [(actor_name, uc_name), ...]  o  [(uc1, uc2, style), ...]
    """
    n_uc = len(usecases)
    fig_h = max(6, n_uc * 0.7 + 2)
    fig, ax = plt.subplots(figsize=(13, fig_h))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    ax.set_facecolor("#FAFAFA")
    fig.patch.set_facecolor("#FAFAFA")

    # sistema boundary
    sys_x, sys_y, sys_w = 3.0, 0.4, 9.5
    sys_h = fig_h - 0.8
    rect = mpatches.Rectangle((sys_x, sys_y), sys_w, sys_h,
                               linewidth=2, edgecolor="#1565C0",
                               facecolor="#E3F2FD", alpha=0.3)
    ax.add_patch(rect)
    ax.text(sys_x + sys_w/2, sys_y + sys_h - 0.3, "Sistema RENADS",
            ha="center", va="top", fontsize=9, color="#1565C0", style="italic")

    def stick_figure(x, y, label, color="#333"):
        # cabeza
        circle = plt.Circle((x, y+0.55), 0.18, color=color, fill=False, lw=1.5)
        ax.add_patch(circle)
        # cuerpo
        ax.plot([x, x], [y+0.37, y-0.1], color=color, lw=1.5)
        # brazos
        ax.plot([x-0.3, x+0.3], [y+0.15, y+0.15], color=color, lw=1.5)
        # piernas
        ax.plot([x, x-0.25], [y-0.1, y-0.45], color=color, lw=1.5)
        ax.plot([x, x+0.25], [y-0.1, y-0.45], color=color, lw=1.5)
        # nombre
        wrapped = textwrap.fill(label, 14)
        ax.text(x, y-0.65, wrapped, ha="center", va="top",
                fontsize=7, color=color, fontweight="bold",
                multialignment="center")

    uc_pos = {}
    actor_pos = {}

    for name, x, y in usecases:
        ell = mpatches.Ellipse((x, y), 2.8, 0.55,
                               linewidth=1.2, edgecolor="#1565C0",
                               facecolor="white")
        ax.add_patch(ell)
        wrapped = textwrap.fill(name, 30)
        ax.text(x, y, wrapped, ha="center", va="center",
                fontsize=7, color="#0D47A1", multialignment="center")
        uc_pos[name] = (x, y)

    colors = actor_colors or {}
    for name, x, y in actors:
        c = colors.get(name, "#1A237E")
        stick_figure(x, y, name, c)
        actor_pos[name] = (x, y)

    for link in links:
        if len(link) == 2:
            a, b = link
            style = "solid"
        else:
            a, b, style = link

        p1 = actor_pos.get(a) or uc_pos.get(a)
        p2 = actor_pos.get(b) or uc_pos.get(b)
        if not p1 or not p2:
            continue

        ls = "--" if style in ("include", "extend") else "-"
        ax.annotate("", xy=p2, xytext=p1,
                    arrowprops=dict(arrowstyle="-", color="#555",
                                   lw=1, linestyle=ls))
        if style in ("include", "extend"):
            mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
            ax.text(mx, my+0.12, f"«{style}»", fontsize=6,
                    color="#777", ha="center", style="italic")

    ax.set_title(title, fontsize=12, fontweight="bold",
                 pad=8, color="#1565C0")
    return fig


def fig_deployment():
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_facecolor("#ECEFF1")
    fig.patch.set_facecolor("#ECEFF1")

    def node(x, y, w, h, label, sublabel="", color="#1565C0", icon=""):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                              linewidth=2, edgecolor=color,
                              facecolor="white")
        ax.add_patch(rect)
        # cabecera
        hdr = FancyBboxPatch((x, y+h-0.45), w, 0.45,
                             boxstyle="square,pad=0",
                             linewidth=0, facecolor=color)
        ax.add_patch(hdr)
        ax.text(x+w/2, y+h-0.22, f"«node» {label}",
                ha="center", va="center", fontsize=8,
                fontweight="bold", color="white")
        if sublabel:
            ax.text(x+w/2, y+h/2 - 0.1, sublabel,
                    ha="center", va="center", fontsize=7.5,
                    color="#333", multialignment="center")

    def component(x, y, w, h, label, color="#37474F"):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                              linewidth=1.2, edgecolor=color,
                              facecolor="#F5F5F5")
        ax.add_patch(rect)
        ax.text(x+w/2, y+h/2, label, ha="center", va="center",
                fontsize=7.5, color=color, multialignment="center")

    def arrow(x1, y1, x2, y2, label="", style="->"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle=style, color="#455A64",
                                   lw=1.3, connectionstyle="arc3,rad=0.05"))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx+0.05, my+0.12, label, fontsize=6.5,
                    color="#555", style="italic")

    # Navegador / Cliente
    node(0.2, 5.8, 2.4, 1.9, "Cliente Web", "Navegador\nChrome / Firefox\nEdge", "#37474F")
    component(0.4, 6.0, 2.0, 0.7, "Next.js 16\n(Browser SPA)", "#37474F")

    # Servidor Next.js
    node(3.2, 5.2, 2.6, 2.5, "App Server", "Next.js 16\n(Node.js 20 LTS)", "#1565C0")
    component(3.4, 5.4, 2.2, 0.6, "React 19 / App Router", "#1565C0")
    component(3.4, 6.05, 2.2, 0.6, "Zustand · TanStack Q5", "#1565C0")
    component(3.4, 6.7, 2.2, 0.55, "Tailwind + shadcn/ui", "#1565C0")

    # Servidor Django API
    node(6.5, 4.5, 2.8, 3.2, "API Server", "Django 6.0 + DRF 3.17\nPython 3.14", "#6A1B9A")
    component(6.7, 4.7, 2.4, 0.5, "JWT SimpleJWT + 2FA", "#6A1B9A")
    component(6.7, 5.25, 2.4, 0.5, "apps.convenios M1", "#6A1B9A")
    component(6.7, 5.8, 2.4, 0.5, "apps.internados M2", "#6A1B9A")
    component(6.7, 6.35, 2.4, 0.5, "apps.actividades M3", "#6A1B9A")
    component(6.7, 6.9, 2.4, 0.45, "apps.calendario M4", "#6A1B9A")

    # PostgreSQL
    node(10.2, 5.5, 2.5, 2.0, "BD Server", "PostgreSQL 16\n(producción)", "#01579B")
    component(10.4, 5.7, 2.1, 0.7, "SQLite\n(desarrollo)", "#757575")

    # Cloudflare R2
    node(6.5, 1.0, 2.8, 2.0, "Object Storage", "Cloudflare R2\nBucket renads-media", "#E65100")
    component(6.7, 1.2, 2.4, 0.55, "PDFs convenios\ndocumentos adjuntos", "#E65100")
    component(6.7, 1.8, 2.4, 0.55, "Logos (STORAGES\ndefault S3Boto3)", "#E65100")

    # SMTP
    node(10.2, 1.0, 2.5, 2.0, "Email SMTP", "Gmail / Brevo\n(OTP · notif.)", "#2E7D32")
    component(10.4, 1.2, 2.1, 0.6, "EMAIL_BACKEND\ndjango.core.mail", "#2E7D32")

    # Flechas
    arrow(2.6, 6.6, 3.2, 6.5, "HTTPS/443")
    arrow(5.8, 6.5, 6.5, 6.5, "REST JSON\nHTTPS/443")
    arrow(9.3, 6.5, 10.2, 6.5, "psycopg2\nTCP 5432")
    arrow(8.1, 4.5, 8.1, 3.0, "boto3\nS3 API")
    arrow(9.3, 4.8, 10.2, 3.0, "SMTP\nTLS 587")

    ax.set_title("Diagrama de Despliegue — RENADS", fontsize=13,
                 fontweight="bold", pad=10, color="#1565C0")

    # leyenda env
    ax.text(0.2, 0.5, "DEV: SQLite + consola email  |  PROD: PostgreSQL + R2 + SMTP",
            fontsize=8, color="#666", style="italic")
    return fig


def fig_er_simplified():
    """ER simplificado mostrando las 12 entidades clave y sus relaciones."""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_facecolor("#FAFAFA")
    fig.patch.set_facecolor("#FAFAFA")

    entities = {
        # name:        (x, y,  w,   h,  color,  fields_short)
        "convenio":       (5.5, 7.5, 2.8, 1.8, "#1565C0", "id · tipo · estado\norg.directorio · universidad\nunidad_ejecutora · facultad"),
        "organo_directorio": (1.0, 7.5, 2.6, 1.4, "#37474F", "id · categoria · nombre"),
        "universidad":    (9.2, 7.5, 2.6, 1.4, "#37474F", "id · nombre · ruc"),
        "ipress":         (9.2, 5.0, 2.6, 1.4, "#4A148C", "codigo_renipress PK\nunidad_ejecutora · nombre"),
        "campo_clinico_ipress": (5.5, 5.0, 2.8, 1.4, "#6A1B9A",
                                 "id · ipress · carrera\ncampos_registrados"),
        "campo_clinico_univ": (3.0, 2.8, 2.8, 1.4, "#7B1FA2",
                               "id · campo_clinico_ipress\nconvenio · universidad"),
        "estudiante":     (0.3, 5.0, 2.5, 1.4, "#01579B", "id · num_documento\nuniversidad · carrera"),
        "interno":        (3.0, 5.0, 2.3, 1.6, "#0277BD",
                           "id · estudiante · convenio\ncampo_clinico · ipress · tutor"),
        "rotacion":       (0.3, 2.8, 2.5, 1.4, "#006064", "id · interno\nipress_origen · destino"),
        "actividad":      (9.2, 2.5, 2.8, 1.6, "#1B5E20",
                           "id · estudiante · interno\nipress · rotacion · tutor"),
        "actividad_calendario": (5.5, 2.5, 2.8, 1.4, "#BF360C",
                                 "id · nombre · fechas\ncontrola_acceso · content_types"),
        "auth_user":      (11.8, 7.0, 2.0, 1.2, "#4E342E", "id · username\nis_active"),
    }

    pos = {}
    for name, (x, y, w, h, color, fields) in entities.items():
        # cabecera
        hdr = FancyBboxPatch((x, y+h-0.4), w, 0.4, boxstyle="square,pad=0",
                             linewidth=0, facecolor=color)
        ax.add_patch(hdr)
        ax.text(x+w/2, y+h-0.2, name, ha="center", va="center",
                fontsize=7.5, fontweight="bold", color="white")
        # cuerpo
        body = FancyBboxPatch((x, y), w, h-0.4, boxstyle="round,pad=0.05",
                              linewidth=1.5, edgecolor=color, facecolor="white")
        ax.add_patch(body)
        ax.text(x+w/2, y+(h-0.4)/2, fields, ha="center", va="center",
                fontsize=6.5, color="#333", multialignment="center")
        pos[name] = (x+w/2, y+h/2)

    rels = [
        ("convenio", "organo_directorio", "N:1"),
        ("convenio", "universidad", "N:1"),
        ("convenio", "ipress", ""),
        ("convenio", "campo_clinico_univ", "1:N"),
        ("campo_clinico_ipress", "ipress", "N:1"),
        ("campo_clinico_ipress", "campo_clinico_univ", "1:N"),
        ("campo_clinico_univ", "interno", "1:N"),
        ("estudiante", "interno", "1:N"),
        ("interno", "rotacion", "1:N"),
        ("interno", "actividad", "1:N"),
        ("actividad", "ipress", "N:1"),
        ("auth_user", "convenio", ""),
    ]

    for a, b, label in rels:
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#888",
                                   lw=1.1, connectionstyle="arc3,rad=0.05"))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx, my+0.12, label, fontsize=6.5, color="#555",
                    ha="center", style="italic")

    ax.set_title("Diagrama Entidad-Relación (entidades clave) — RENADS",
                 fontsize=13, fontweight="bold", pad=10, color="#1565C0")
    ax.text(7, 0.4, "Diagrama simplificado — ver er_diagram.md para especificación completa Mermaid",
            fontsize=8, color="#888", ha="center", style="italic")
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# CONTENIDO: REQUERIMIENTOS
# ══════════════════════════════════════════════════════════════════════════════

RF = [
    # id, módulo, descripción
    ("RF-01", "M1 – Convenios", "Registrar solicitud de Convenio Marco por GERESA/DIRESA u Órgano del MINSA."),
    ("RF-02", "M1 – Convenios", "Registrar solicitud de Convenio Específico (con o sin Convenio Marco según tipo de órgano)."),
    ("RF-03", "M1 – Convenios", "Gestionar ciclo de vida del convenio: evaluación técnica (DIGEP), opinión jurídica (OGAJ) y opinión favorable (CONAPRES)."),
    ("RF-04", "M1 – Convenios", "Registrar firmas de convenio por las partes suscritas."),
    ("RF-05", "M1 – Convenios", "Publicar y registrar vigencia de convenios aprobados."),
    ("RF-06", "M1 – Convenios", "Registrar y gestionar Adendas de ampliación de convenios vigentes."),
    ("RF-07", "M1 – Convenios", "Registrar campos clínicos por IPRESS/carrera (CONAPRES) y asignarlos por universidad (Órgano Regional)."),
    ("RF-08", "M1 – Convenios", "Generar proyecto de convenio y expediente en PDF desde plantillas Word."),
    ("RF-09", "M1 – Convenios", "Adjuntar y versionar documentos PDF (resoluciones, anexos) por convenio."),
    ("RF-10", "M1 – Convenios", "Mantener nomenclatura única del Convenio Marco asignada al validar DIGEP."),
    ("RF-11", "M2 – Internados", "Registrar estudiantes de forma individual o masiva (Excel)."),
    ("RF-12", "M2 – Internados", "Asignar internados a campos clínicos disponibles por orden de mérito."),
    ("RF-13", "M2 – Internados", "Gestionar rotaciones de internos con autorización de partes firmantes."),
    ("RF-14", "M2 – Internados", "Adjuntar declaraciones juradas del interno y gestionar su estado de validación."),
    ("RF-15", "M2 – Internados", "Crear automáticamente usuario del sistema al registrar un internado (onboarding RN-22)."),
    ("RF-16", "M2 – Internados", "Registrar tutores con 1 o 2 universidades asignadas."),
    ("RF-17", "M3 – Actividades", "Registrar actividades docente-asistenciales del estudiante con sede, rotación y tutor."),
    ("RF-18", "M3 – Actividades", "Validar y consultar actividades registradas por los tutores."),
    ("RF-19", "M4 – Calendario", "Crear y gestionar actividades del calendario administrativo con ventanas de fechas."),
    ("RF-20", "M4 – Calendario", "Bloquear escritura de módulos fuera de ventana temporal vigente (IsModuleEnabled)."),
    ("RF-21", "Common – Auth",   "Autenticar usuarios con usuario/contraseña + 2FA (TOTP o Email OTP)."),
    ("RF-22", "Common – Auth",   "Gestionar expiración de contraseña cada 90 días."),
    ("RF-23", "Common – Auth",   "Controlar acceso por rol y perfil institucional (universidad, IPRESS, órgano)."),
    ("RF-24", "Common – Auth",   "Registrar bitácora de auditoría por operación crítica."),
    ("RF-25", "Common – Docs",   "Almacenar documentos PDF en Cloudflare R2 con presigned URLs."),
]

RNF = [
    ("RNF-SEG-01", "Seguridad", "Autenticación basada en JWT con refresh token y lista negra."),
    ("RNF-SEG-02", "Seguridad", "Autorización por roles (grupos Django) y perfiles institucionales (perfil_usuario_entidad)."),
    ("RNF-SEG-03", "Seguridad", "2FA obligatorio configurable: TOTP (autenticador) o Email OTP (6 dígitos, TTL 10 min)."),
    ("RNF-SEG-04", "Seguridad", "Contraseñas almacenadas con hash PBKDF2-SHA256; expiración a 90 días."),
    ("RNF-SEG-05", "Seguridad", "Comunicación TLS/HTTPS en todos los endpoints públicos."),
    ("RNF-SEG-06", "Seguridad", "Expiración automática de sesión por inactividad (token access de vida corta)."),
    ("RNF-SEG-07", "Seguridad", "Formularios web con method=POST para evitar exposición de credenciales en URL."),
    ("RNF-AUD-01", "Auditoría", "Bitácora de auditoría por usuario, fecha/hora, acción, entidad, valor anterior y nuevo."),
    ("RNF-AUD-02", "Auditoría", "Trazabilidad completa de cambios de estado en convenios, internados y rotaciones."),
    ("RNF-DOC-01", "Documental", "Almacenamiento de PDFs en Cloudflare R2 (S3-compatible); fallback GCS o FileSystem."),
    ("RNF-DOC-02", "Documental", "Versionado de documentos por (objeto, documento_anexo); acceso vía presigned URL."),
    ("RNF-DOC-03", "Documental", "Generación de PDFs desde plantillas Word con docxtpl + LibreOffice headless."),
    ("RNF-REN-01", "Rendimiento", "Filtros eficientes por convenio, universidad, región, sede, estudiante y periodo."),
    ("RNF-REN-02", "Rendimiento", "Paginación en todos los listados con page_size máximo configurable."),
    ("RNF-INT-01", "Integración", "API REST JSON con Django REST Framework; documentación OpenAPI/Swagger."),
    ("RNF-INT-02", "Integración", "Frontend Next.js consume API vía TanStack Query v5 con caché y revalidación."),
    ("RNF-INT-03", "Integración", "Exportación de reportes en PDF y Excel (RNF-INT-03)."),
    ("RNF-MAN-01", "Mantenib.", "Catálogos maestros parametrizables sin cambios de código (CRUD admin)."),
    ("RNF-MAN-02", "Mantenib.", "Migraciones Django versionadas; datos de catálogo cargados con fixtures/seeds."),
    ("RNF-MAN-03", "Mantenib.", "Separación de configuración por entorno: base.py / dev.py / prod.py."),
]

# ══════════════════════════════════════════════════════════════════════════════
# CONTENIDO: REGLAS DE NEGOCIO
# ══════════════════════════════════════════════════════════════════════════════

RN = [
    ("RN-01", "M1", "Solo GERESA o DIRESA pueden solicitar un Convenio Marco. Las DIRIS no requieren Convenio Marco para solicitar un Convenio Específico."),
    ("RN-02", "M1", "Un Convenio Específico requiere un Convenio Marco vigente, excepto para órganos DIRIS (Lima Metropolitana)."),
    ("RN-03", "M1", "La opinión jurídica (OGAJ) se solicita exclusivamente para Convenios Marco."),
    ("RN-04", "M1", "La opinión favorable (CONAPRES) se solicita exclusivamente para Convenios Específicos."),
    ("RN-05", "M1", "CONAPRES autoriza y registra las IPRESS como sedes docentes que sean: asistenciales, del MINSA o FFAA/PNP, y de gestión pública."),
    ("RN-06", "M1", "CONAPRES autoriza y registra el total de campos clínicos por sede docente y carrera profesional (campo_clinico_ipress)."),
    ("RN-07", "M1", "El Órgano Regional (GERESA/DIRESA/DIRIS) asigna campos clínicos por universidad y carrera en el mismo ámbito geográfico sanitario."),
    ("RN-08", "M1", "campos_clinicos_autorizados ≤ campos_clinicos_registrados − Σ(autorizados de otras asignaciones del mismo registro)."),
    ("RN-09", "M1", "Un Convenio Específico no avanza a suscripción sin ≥1 campo_clinico_ipress con número de resolución CONAPRES sobre una sede de su unidad ejecutora."),
    ("RN-10", "M1", "La nomenclatura del Convenio Marco se asigna al aprobar la evaluación técnica DIGEP (resultado=VALIDADO). No es editable libremente."),
    ("RN-11", "M1", "Una adenda hereda tipo, marco, universidad, órgano, unidad ejecutora, facultad y solicitante del convenio origen."),
    ("RN-12", "M1", "Al pasar una adenda a VIGENTE, el convenio origen se marca AMPLIADO (salvo que esté CERRADO, ANULADO o ya AMPLIADO)."),
    ("RN-13", "M1", "Convenio Marco: sin unidad_ejecutora ni facultad. Convenio Específico: ambos obligatorios; facultad.universidad == convenio_marco.universidad."),
    ("RN-14", "M1", "Los estados del convenio son forward-only: no se puede retroceder un convenio a un estado anterior."),
    ("RN-15", "M2", "El internado solo se registra sobre un Convenio Específico vigente y autorizado."),
    ("RN-16", "M2", "Rotaciones solo dentro del mismo ámbito geográfico sanitario."),
    ("RN-17", "M2", "Rotaciones requieren autorización de las autoridades suscritas en el Convenio Específico."),
    ("RN-18", "M2", "El interno se asigna a campo_clinico_ipress_universidad (asignación por universidad), no al registro global de CONAPRES."),
    ("RN-19", "M2", "PREGRADO: periodo_academico obligatorio, especialidad nula. SEGUNDA_ESPECIALIDAD/MAESTRIA/DOCTORADO: especialidad obligatoria, periodo_academico nulo."),
    ("RN-20", "M2", "El rol Universidad solo puede registrar/ver internos de las universidades en su ámbito institucional (perfil_usuario_entidad)."),
    ("RN-21", "M2", "Un estudiante no puede tener más de un internado vigente (estados: REGISTRADO, PENDIENTE_VALIDACION, OBSERVADO, VALIDADO, ACTIVO, EN_ROTACION_*)."),
    ("RN-22", "M2", "Al registrar el internado se crea/reutiliza un usuario del sistema (username=DNI, grupo=Interno, debe_cambiar_password=True). Se notifica por correo."),
    ("RN-23", "M2", "El internado no pasa a ACTIVO sin estado_declaraciones=VALIDADAS."),
    ("RN-24", "M2", "Un tutor pertenece a 1 o 2 universidades (tope de negocio) vía tabla puente tutor_universidad."),
    ("RN-25", "M2", "Actividad docente-asistencial debe asociarse a: estudiante + sede (IPRESS) + rotación/periodo + tutor."),
    ("RN-26", "M4", "Una CalendarActivity con controla_acceso=True y activo=True bloquea la escritura (POST/PUT/PATCH/DELETE) de los modelos referenciados fuera de ventana vigente."),
]

# ══════════════════════════════════════════════════════════════════════════════
# CONTENIDO: ACTORES
# ══════════════════════════════════════════════════════════════════════════════

ACTORS = [
    # nombre, tipo, descripción, módulos
    ("Administrador RENADS",    "Interno / Sistema", "Gestiona catálogos, usuarios, auditoría y calendario administrativo. Exento de restricción temporal de módulos.",           "Todos"),
    ("DIGEP",                   "Institucional",     "Evalúa técnicamente los Convenios Marco y los valida con nomenclatura.",                                                   "M1"),
    ("CONAPRES",                "Institucional",     "Emite opinión favorable sobre Convenios Específicos; autoriza y registra sedes docentes y campos clínicos.",               "M1"),
    ("OGAJ",                    "Institucional",     "Emite opinión jurídica exclusivamente sobre Convenios Marco.",                                                             "M1"),
    ("Secretaría General / SG", "Institucional",     "Recibe y formaliza el expediente del convenio para firma por las autoridades.",                                            "M1"),
    ("VICEPAS",                 "Institucional",     "Supervisión general de procesos de articulación docencia-servicio.",                                                       "M1, M2"),
    ("GORE / GERESA / DIRESA",  "Institucional",     "Solicita Convenios Marco (GERESA/DIRESA) y Específicos. Asigna campos clínicos por universidad en su ámbito sanitario.",  "M1"),
    ("DIRIS",                   "Institucional",     "Solicita directamente Convenios Específicos sin requerir Convenio Marco previo (Lima Metropolitana).",                     "M1"),
    ("Universidad",             "Académico",         "Registra internados de sus estudiantes en los campos clínicos disponibles; gestiona tutores y adjunta documentos.",        "M1, M2"),
    ("Sede Docente (IPRESS)",   "Asistencial",       "Recibe estudiantes en rotación; el tutor registra y valida actividades docente-asistenciales.",                            "M2, M3"),
    ("Tutor / Docente",         "Operativo",         "Supervisa al estudiante en la sede; registra y valida actividades docente-asistenciales.",                                "M2, M3"),
    ("Estudiante / Interno",    "Operativo",         "Accede al sistema para adjuntar declaraciones juradas; consulta sus datos de internado y rotaciones.",                    "M2"),
    ("Auditor / Supervisor",    "Control",           "Consulta bitácora de auditoría y reportes de seguimiento del proceso.",                                                   "Todos"),
]

# ══════════════════════════════════════════════════════════════════════════════
# GENERADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def build_document():
    doc = Document()

    # ── Márgenes ──────────────────────────────────────────────────────────────
    for section in doc.sections:
        section.page_width  = Cm(21.59)
        section.page_height = Cm(27.94)
        section.left_margin   = Cm(2.54)
        section.right_margin  = Cm(2.54)
        section.top_margin    = Cm(2.54)
        section.bottom_margin = Cm(2.54)

    # ── PORTADA ───────────────────────────────────────────────────────────────
    doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("RENADS")
    run.bold = True
    run.font.size = Pt(32)
    run.font.color.rgb = RGBColor(0x15, 0x65, 0xC0)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("Registro Nacional de Articulación Docencia-Servicio en Salud")
    r.font.size = Pt(16)
    r.font.color.rgb = RGBColor(0x37, 0x47, 0x4F)

    doc.add_paragraph()
    doc2 = doc.add_paragraph()
    doc2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = doc2.add_run("Documento de Análisis y Diseño del Sistema")
    r2.bold = True
    r2.font.size = Pt(18)

    doc.add_paragraph()
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run("MINSA — Ministerio de Salud del Perú\n")
    meta.add_run("Versión 1.0  |  Septiembre 2026").italic = True
    doc.add_page_break()

    # ── ÍNDICE (manual) ───────────────────────────────────────────────────────
    add_heading(doc, "Tabla de Contenidos", 1)
    toc_items = [
        "1. Requerimientos Funcionales y No Funcionales",
        "2. Reglas del Negocio",
        "3. Actores del Sistema",
        "4. Diagrama de Paquetes",
        "5. Diagramas de Caso de Uso por Módulo",
        "   5.1. M1 – Gestionar Convenios",
        "   5.2. M2 – Registrar Internados",
        "   5.3. M3 – Registrar Actividades",
        "   5.4. M4 – Calendario Administrativo",
        "   5.5. Módulo Común – Autenticación y Seguridad",
        "6. Diagrama de Despliegue",
        "7. Diagrama Entidad-Relación de la Base de Datos",
    ]
    for item in toc_items:
        p = doc.add_paragraph(item)
        p.paragraph_format.left_indent = Inches(0.3 if item.startswith(" ") else 0)
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 1 — REQUERIMIENTOS
    # ══════════════════════════════════════════════════════════════════════════
    add_heading(doc, "1. Requerimientos Funcionales y No Funcionales", 1)
    doc.add_paragraph(
        "Los requerimientos del sistema RENADS se clasifican en funcionales (RF), que describen las "
        "capacidades del sistema, y no funcionales (RNF), que establecen las restricciones de calidad, "
        "seguridad y operación."
    )

    add_heading(doc, "1.1. Requerimientos Funcionales", 2)
    tbl = doc.add_table(rows=1, cols=3)
    tbl.style = "Table Grid"
    add_table_header(tbl, ["ID", "Módulo", "Descripción"])
    alt = False
    for row in RF:
        bg = GRIS_TABLA if alt else None
        add_table_row(tbl, row, bg=bg, bold_first=True)
        alt = not alt
    # Ajustar anchos
    for row in tbl.rows:
        row.cells[0].width = Cm(2.0)
        row.cells[1].width = Cm(3.5)
        row.cells[2].width = Cm(11.5)
    doc.add_paragraph()

    add_heading(doc, "1.2. Requerimientos No Funcionales", 2)
    tbl2 = doc.add_table(rows=1, cols=3)
    tbl2.style = "Table Grid"
    add_table_header(tbl2, ["ID", "Categoría", "Descripción"])
    alt = False
    for row in RNF:
        bg = GRIS_TABLA if alt else None
        add_table_row(tbl2, row, bg=bg, bold_first=True)
        alt = not alt
    for row in tbl2.rows:
        row.cells[0].width = Cm(2.8)
        row.cells[1].width = Cm(2.7)
        row.cells[2].width = Cm(11.5)
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 2 — REGLAS DE NEGOCIO
    # ══════════════════════════════════════════════════════════════════════════
    add_heading(doc, "2. Reglas del Negocio", 1)
    doc.add_paragraph(
        "Las reglas del negocio son restricciones y condiciones que el sistema debe cumplir para "
        "garantizar la integridad y consistencia del proceso de articulación docencia-servicio."
    )
    tbl3 = doc.add_table(rows=1, cols=3)
    tbl3.style = "Table Grid"
    add_table_header(tbl3, ["ID", "Módulo", "Descripción"])
    alt = False
    for row in RN:
        bg = GRIS_TABLA if alt else None
        add_table_row(tbl3, row, bg=bg, bold_first=True)
        alt = not alt
    for row in tbl3.rows:
        row.cells[0].width = Cm(2.0)
        row.cells[1].width = Cm(1.5)
        row.cells[2].width = Cm(13.5)
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3 — ACTORES
    # ══════════════════════════════════════════════════════════════════════════
    add_heading(doc, "3. Actores del Sistema", 1)
    doc.add_paragraph(
        "Los actores son las entidades externas o internas que interactúan con el sistema RENADS. "
        "Se clasifican en actores institucionales, académicos, operativos y de control."
    )

    # Figura: actores agrupados
    fig_act, ax_act = plt.subplots(figsize=(13, 5))
    ax_act.set_xlim(0, 13)
    ax_act.set_ylim(0, 5)
    ax_act.axis("off")
    ax_act.set_facecolor("#FAFAFA")
    fig_act.patch.set_facecolor("#FAFAFA")

    groups = {
        "Institucionales": (0.2, 0.5, 4.0, 4.0, "#1565C0",
            ["DIGEP", "CONAPRES", "OGAJ", "Sec. General", "VICEPAS", "GORE/GERESA\nDIRESA/DIRIS"]),
        "Académicos": (4.5, 0.5, 3.0, 4.0, "#6A1B9A",
            ["Universidad", "Facultad", "Sede Docente\n(IPRESS)"]),
        "Operativos": (7.8, 0.5, 2.5, 4.0, "#01579B",
            ["Tutor/Docente", "Estudiante\n/Interno"]),
        "Sistema/Control": (10.5, 0.5, 2.3, 4.0, "#2E7D32",
            ["Admin RENADS", "Auditor\nSupervisor"]),
    }

    def mini_stick(ax, x, y, label, c):
        circle = plt.Circle((x, y+0.22), 0.09, color=c, fill=True, lw=0, alpha=0.8)
        ax.add_patch(circle)
        ax.plot([x, x], [y+0.13, y-0.05], color=c, lw=1.2)
        ax.plot([x-0.15, x+0.15], [y+0.07, y+0.07], color=c, lw=1.2)
        ax.plot([x, x-0.12], [y-0.05, y-0.22], color=c, lw=1.2)
        ax.plot([x, x+0.12], [y-0.05, y-0.22], color=c, lw=1.2)
        wrapped = textwrap.fill(label, 10)
        ax_act.text(x, y-0.35, wrapped, ha="center", va="top",
                    fontsize=6.5, color=c, multialignment="center")

    for grp, (gx, gy, gw, gh, gc, members) in groups.items():
        rect = mpatches.Rectangle((gx, gy), gw, gh, linewidth=1.5,
                                  edgecolor=gc, facecolor=gc, alpha=0.08)
        ax_act.add_patch(rect)
        ax_act.text(gx+gw/2, gy+gh-0.25, grp, ha="center", va="top",
                    fontsize=8, fontweight="bold", color=gc)
        n = len(members)
        for i, m in enumerate(members):
            px = gx + (i % 3) * (gw / min(3, n)) + (gw / min(3, n)) / 2
            row = i // 3
            py = gy + gh - 0.6 - row * 1.3
            mini_stick(ax_act, px, py, m, gc)

    ax_act.set_title("Actores del Sistema RENADS", fontsize=12,
                     fontweight="bold", pad=8, color="#1565C0")
    embed_figure(doc, fig_act, caption="Figura 3.1 — Actores del Sistema RENADS")

    tbl4 = doc.add_table(rows=1, cols=4)
    tbl4.style = "Table Grid"
    add_table_header(tbl4, ["Actor", "Tipo", "Descripción", "Módulos"])
    alt = False
    for row in ACTORS:
        bg = GRIS_TABLA if alt else None
        add_table_row(tbl4, row, bg=bg, bold_first=True)
        alt = not alt
    for row in tbl4.rows:
        row.cells[0].width = Cm(3.5)
        row.cells[1].width = Cm(2.5)
        row.cells[2].width = Cm(9.5)
        row.cells[3].width = Cm(2.0)
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 4 — DIAGRAMA DE PAQUETES
    # ══════════════════════════════════════════════════════════════════════════
    add_heading(doc, "4. Diagrama de Paquetes", 1)
    doc.add_paragraph(
        "El sistema se organiza en paquetes Django separados por responsabilidad. El paquete "
        "apps.common provee infraestructura transversal (autenticación, auditoría, almacenamiento). "
        "Los paquetes de dominio (convenios, internados, actividades, calendario) dependen de common "
        "y entre sí en el orden del flujo de negocio."
    )
    embed_figure(doc, fig_package_diagram(), width_inches=6.5,
                 caption="Figura 4.1 — Diagrama de Paquetes del Sistema RENADS")

    add_heading(doc, "4.1. Descripción de Paquetes", 2)
    pkg_desc = [
        ("config/",            "Configuración del proyecto: settings por entorno (base/dev/prod), URLconf raíz, wsgi, asgi."),
        ("apps/common/",       "Infraestructura transversal: modelos de seguridad y auditoría, perfiles de usuario, permisos (IsModuleEnabled), storage (R2/GCS/FS), serializers base, middleware JWT."),
        ("apps/convenios/",    "M1 – Gestionar Convenios: modelos, servicios, serializers y vistas para convenios, campos clínicos, directorio de órganos, representantes, partes firmantes y generación de PDFs."),
        ("apps/internados/",   "M2 – Registrar Internados: modelos, servicios, serializers y vistas para estudiantes, tutores, internados, rotaciones, declaraciones juradas y carga masiva Excel."),
        ("apps/actividades/",  "M3 – Registrar Actividades: modelos y flujo de actividades docente-asistenciales con validación por tutor."),
        ("apps/calendario/",   "M4 – Calendario Administrativo: modelo CalendarActivity, selector de ventana temporal y enforcement de escritura por ContentType."),
    ]
    tbl5 = doc.add_table(rows=1, cols=2)
    tbl5.style = "Table Grid"
    add_table_header(tbl5, ["Paquete", "Responsabilidad"])
    for p, d in pkg_desc:
        r = tbl5.add_row()
        r.cells[0].text = p
        r.cells[1].text = d
        for cell in r.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(9)
        r.cells[0].paragraphs[0].runs[0].bold = True
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 5 — DIAGRAMAS DE CASO DE USO
    # ══════════════════════════════════════════════════════════════════════════
    add_heading(doc, "5. Diagramas de Caso de Uso por Módulo", 1)
    doc.add_paragraph(
        "Se presenta un diagrama de caso de uso por cada módulo del sistema, mostrando los actores "
        "participantes y las funcionalidades principales que el sistema ofrece."
    )

    # ── 5.1 M1 CONVENIOS ────────────────────────────────────────────────────
    add_heading(doc, "5.1. M1 – Gestionar Convenios", 2)
    actors_m1 = [
        ("GORE/GERESA/DIRESA", 1.0, 7.5),
        ("DIRIS",              1.0, 5.5),
        ("DIGEP",              1.0, 3.5),
        ("CONAPRES",          12.0, 7.5),
        ("OGAJ",              12.0, 5.5),
        ("Sec. General",      12.0, 3.5),
        ("Admin RENADS",       1.0, 1.5),
    ]
    uc_m1 = [
        ("Registrar Convenio Marco",             5.5, 9.5),
        ("Registrar Convenio Específico",         7.5, 9.5),
        ("Registrar Adenda",                      9.5, 9.5),
        ("Evaluar Técnicamente (DIGEP)",          5.5, 8.2),
        ("Emitir Opinión Jurídica (OGAJ)",        7.5, 8.2),
        ("Emitir Opinión Favorable (CONAPRES)",   9.5, 8.2),
        ("Registrar Firma de Convenio",           5.5, 6.9),
        ("Publicar Convenio",                     7.5, 6.9),
        ("Registrar Campos Clínicos (CONAPRES)",  9.5, 6.9),
        ("Asignar Campos Clínicos (Regional)",    5.5, 5.6),
        ("Generar PDF Proyecto/Expediente",       7.5, 5.6),
        ("Adjuntar Documentos PDF",               9.5, 5.6),
        ("Gestionar Catálogos Maestros",          7.5, 4.3),
    ]
    links_m1 = [
        ("GORE/GERESA/DIRESA", "Registrar Convenio Marco"),
        ("GORE/GERESA/DIRESA", "Registrar Convenio Específico"),
        ("DIRIS", "Registrar Convenio Específico"),
        ("DIGEP", "Evaluar Técnicamente (DIGEP)"),
        ("OGAJ", "Emitir Opinión Jurídica (OGAJ)"),
        ("CONAPRES", "Emitir Opinión Favorable (CONAPRES)"),
        ("CONAPRES", "Registrar Campos Clínicos (CONAPRES)"),
        ("GORE/GERESA/DIRESA", "Asignar Campos Clínicos (Regional)"),
        ("Sec. General", "Registrar Firma de Convenio"),
        ("Admin RENADS", "Gestionar Catálogos Maestros"),
        ("Admin RENADS", "Publicar Convenio"),
        ("GORE/GERESA/DIRESA", "Generar PDF Proyecto/Expediente"),
        ("GORE/GERESA/DIRESA", "Registrar Adenda"),
        ("GORE/GERESA/DIRESA", "Adjuntar Documentos PDF"),
    ]
    embed_figure(doc, fig_usecase("Casos de Uso — M1: Gestionar Convenios",
                                  actors_m1, uc_m1, links_m1),
                 caption="Figura 5.1 — Diagrama de Caso de Uso M1: Gestionar Convenios")

    # ── 5.2 M2 INTERNADOS ───────────────────────────────────────────────────
    add_heading(doc, "5.2. M2 – Registrar Internados", 2)
    actors_m2 = [
        ("Universidad",  1.0, 7.0),
        ("CONAPRES",    12.0, 7.0),
        ("Tutor",        1.0, 4.0),
        ("Estudiante",  12.0, 4.0),
        ("Admin RENADS", 1.0, 1.5),
    ]
    uc_m2 = [
        ("Registrar Estudiante (individual)",   5.5, 8.5),
        ("Carga Masiva de Estudiantes (Excel)", 7.5, 8.5),
        ("Asignar Internado a Campo Clínico",   9.5, 8.5),
        ("Registrar Tutor",                     5.5, 7.2),
        ("Asignar Tutor a Universidad",         7.5, 7.2),
        ("Registrar Rotación",                  5.5, 5.9),
        ("Autorizar Rotación",                  7.5, 5.9),
        ("Adjuntar Declaraciones Juradas",      9.5, 5.9),
        ("Revisar Declaraciones Juradas",       5.5, 4.6),
        ("Activar Internado",                   7.5, 4.6),
        ("Gestionar Onboarding Usuario",        9.5, 4.6),
        ("Consultar Estado de Internado",       7.5, 3.3),
    ]
    links_m2 = [
        ("Universidad", "Registrar Estudiante (individual)"),
        ("Universidad", "Carga Masiva de Estudiantes (Excel)"),
        ("Universidad", "Asignar Internado a Campo Clínico"),
        ("Universidad", "Registrar Tutor"),
        ("Universidad", "Asignar Tutor a Universidad"),
        ("Universidad", "Registrar Rotación"),
        ("Universidad", "Revisar Declaraciones Juradas"),
        ("CONAPRES", "Autorizar Rotación"),
        ("Estudiante", "Adjuntar Declaraciones Juradas"),
        ("Estudiante", "Consultar Estado de Internado"),
        ("Admin RENADS", "Gestionar Onboarding Usuario"),
        ("Admin RENADS", "Activar Internado"),
    ]
    embed_figure(doc, fig_usecase("Casos de Uso — M2: Registrar Internados",
                                  actors_m2, uc_m2, links_m2),
                 caption="Figura 5.2 — Diagrama de Caso de Uso M2: Registrar Internados")

    # ── 5.3 M3 ACTIVIDADES ──────────────────────────────────────────────────
    add_heading(doc, "5.3. M3 – Registrar Actividades", 2)
    actors_m3 = [
        ("Tutor/Docente", 1.0, 5.0),
        ("Estudiante",    1.0, 3.0),
        ("Admin RENADS", 12.0, 4.0),
        ("Auditor",      12.0, 2.0),
    ]
    uc_m3 = [
        ("Registrar Actividad Docente-Asistencial", 6.5, 6.5),
        ("Validar Actividad",                       6.5, 5.2),
        ("Observar / Rechazar Actividad",           6.5, 3.9),
        ("Consultar Actividades por Estudiante",    6.5, 2.6),
        ("Exportar Reporte de Actividades",         6.5, 1.3),
    ]
    links_m3 = [
        ("Tutor/Docente", "Registrar Actividad Docente-Asistencial"),
        ("Tutor/Docente", "Validar Actividad"),
        ("Tutor/Docente", "Observar / Rechazar Actividad"),
        ("Estudiante", "Consultar Actividades por Estudiante"),
        ("Admin RENADS", "Validar Actividad"),
        ("Auditor", "Consultar Actividades por Estudiante"),
        ("Auditor", "Exportar Reporte de Actividades"),
    ]
    embed_figure(doc, fig_usecase("Casos de Uso — M3: Registrar Actividades",
                                  actors_m3, uc_m3, links_m3),
                 caption="Figura 5.3 — Diagrama de Caso de Uso M3: Registrar Actividades")

    # ── 5.4 M4 CALENDARIO ───────────────────────────────────────────────────
    add_heading(doc, "5.4. M4 – Calendario Administrativo", 2)
    actors_m4 = [
        ("Admin RENADS", 1.0, 4.0),
        ("Usuario Auth", 12.0, 4.0),
    ]
    uc_m4 = [
        ("Crear Actividad de Calendario",          6.5, 6.0),
        ("Definir Ventana Temporal por Módulo",    6.5, 4.8),
        ("Habilitar / Deshabilitar Escritura",     6.5, 3.6),
        ("Consultar Módulos Habilitados (/me)",    6.5, 2.4),
        ("Bloquear Operación Fuera de Ventana",    6.5, 1.2),
    ]
    links_m4 = [
        ("Admin RENADS", "Crear Actividad de Calendario"),
        ("Admin RENADS", "Definir Ventana Temporal por Módulo"),
        ("Admin RENADS", "Habilitar / Deshabilitar Escritura"),
        ("Usuario Auth", "Consultar Módulos Habilitados (/me)"),
        ("Bloquear Operación Fuera de Ventana", "Habilitar / Deshabilitar Escritura", "include"),
    ]
    embed_figure(doc, fig_usecase("Casos de Uso — M4: Calendario Administrativo",
                                  actors_m4, uc_m4, links_m4),
                 caption="Figura 5.4 — Diagrama de Caso de Uso M4: Calendario Administrativo")

    # ── 5.5 COMMON AUTH ─────────────────────────────────────────────────────
    add_heading(doc, "5.5. Módulo Común – Autenticación y Seguridad", 2)
    actors_auth = [
        ("Usuario",      1.0, 5.0),
        ("Admin RENADS", 1.0, 2.0),
        ("Sistema",     12.0, 3.5),
    ]
    uc_auth = [
        ("Iniciar Sesión (JWT)",             6.5, 7.0),
        ("Verificar 2FA (TOTP / Email OTP)", 6.5, 5.8),
        ("Cambiar Contraseña",               6.5, 4.6),
        ("Recuperar Contraseña",             6.5, 3.4),
        ("Gestionar Perfil de Usuario",      6.5, 2.2),
        ("Gestionar Roles y Permisos",       6.5, 1.0),
    ]
    links_auth = [
        ("Usuario", "Iniciar Sesión (JWT)"),
        ("Usuario", "Verificar 2FA (TOTP / Email OTP)"),
        ("Usuario", "Cambiar Contraseña"),
        ("Usuario", "Recuperar Contraseña"),
        ("Usuario", "Gestionar Perfil de Usuario"),
        ("Admin RENADS", "Gestionar Roles y Permisos"),
        ("Sistema", "Verificar 2FA (TOTP / Email OTP)"),
        ("Verificar 2FA (TOTP / Email OTP)", "Iniciar Sesión (JWT)", "include"),
        ("Cambiar Contraseña", "Iniciar Sesión (JWT)", "extend"),
    ]
    embed_figure(doc, fig_usecase("Casos de Uso — Módulo Común: Autenticación y Seguridad",
                                  actors_auth, uc_auth, links_auth),
                 caption="Figura 5.5 — Diagrama de Caso de Uso: Autenticación y Seguridad")
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 6 — DIAGRAMA DE DESPLIEGUE
    # ══════════════════════════════════════════════════════════════════════════
    add_heading(doc, "6. Diagrama de Despliegue", 1)
    doc.add_paragraph(
        "El diagrama muestra la distribución física de los componentes del sistema RENADS "
        "en los nodos de infraestructura para el entorno de producción. En desarrollo se usa "
        "SQLite y el backend de email de consola."
    )
    embed_figure(doc, fig_deployment(), width_inches=6.5,
                 caption="Figura 6.1 — Diagrama de Despliegue — RENADS")

    add_heading(doc, "6.1. Descripción de Nodos", 2)
    deploy_desc = [
        ("Cliente Web",     "Navegador del usuario (Chrome/Firefox/Edge). Ejecuta el bundle React compilado por Next.js."),
        ("App Server",      "Servidor Node.js 20 LTS con Next.js 16. Renderiza SSR/SSG; enruta al API Django vía HTTPS."),
        ("API Server",      "Python 3.14 + Django 6.0 + DRF 3.17. Expone REST JSON en /api/v1/. JWT + 2FA. Gunicorn en producción."),
        ("BD Server",       "PostgreSQL 16 en producción. SQLite en desarrollo local. Conexión psycopg2 por TCP 5432."),
        ("Object Storage",  "Cloudflare R2 (S3-compatible) para PDFs y documentos adjuntos. boto3 con presigned URLs SigV4."),
        ("Email SMTP",      "Gmail App Password / Brevo para envío de OTP y notificaciones. Consola en desarrollo."),
    ]
    tbl6 = doc.add_table(rows=1, cols=2)
    tbl6.style = "Table Grid"
    add_table_header(tbl6, ["Nodo", "Descripción"])
    for n, d in deploy_desc:
        r = tbl6.add_row()
        r.cells[0].text = n
        r.cells[1].text = d
        r.cells[0].paragraphs[0].runs[0].bold = True
        for cell in r.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(9)
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 7 — DIAGRAMA ER
    # ══════════════════════════════════════════════════════════════════════════
    add_heading(doc, "7. Diagrama Entidad-Relación de la Base de Datos", 1)
    doc.add_paragraph(
        "Se muestra el diagrama ER con las entidades principales del sistema y sus relaciones. "
        "La base de datos cuenta con más de 50 tablas de dominio distribuidas en 4 módulos. "
        "A continuación se presenta el diagrama simplificado con las entidades nucleares; "
        "la especificación completa en notación Mermaid está disponible en docs/er_diagram.md."
    )
    embed_figure(doc, fig_er_simplified(), width_inches=6.8,
                 caption="Figura 7.1 — Diagrama ER (entidades clave) — RENADS")

    add_heading(doc, "7.1. Tablas Principales por Módulo", 2)
    er_tables = [
        ("M0 – Seguridad", "auth_user, seguridad_usuario, perfil_usuario, perfil_usuario_entidad, bitacora_auditoria, documento_adjunto, documento_anexo"),
        ("M1 – Convenios", "convenio, tipo_convenio, estado_convenio, organo_directorio, organo_representante, cargo_ejecutivo, gobierno_regional, universidad, facultad, unidad_ejecutora, ipress, campo_clinico_ipress, campo_clinico_ipress_universidad, parte_convenio, evaluacion_tecnica, opinion_conapres, opinion_juridica"),
        ("M1 – Catálogos geo.", "ubigeo, region, ambito_geografico_sanitario, red, microred"),
        ("M2 – Internados", "estudiante, tutor, tutor_universidad, interno, rotacion, autorizacion_rotacion, historial_estado_internado, historial_estado_rotacion"),
        ("M3 – Actividades", "actividad_docente_asistencial, validacion_actividad"),
        ("M4 – Calendario", "actividad_calendario, actividad_calendario_content_types (M2M)"),
    ]
    tbl7 = doc.add_table(rows=1, cols=2)
    tbl7.style = "Table Grid"
    add_table_header(tbl7, ["Módulo", "Tablas"])
    for m, t in er_tables:
        r = tbl7.add_row()
        r.cells[0].text = m
        r.cells[1].text = t
        r.cells[0].paragraphs[0].runs[0].bold = True
        for cell in r.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(9)

    add_heading(doc, "7.2. Notas de Diseño del Modelo de Datos", 2)
    notes = [
        "ipress.codigo_renipress es la clave primaria (CharField max 8); no existe columna id numérica en esa tabla.",
        "unidad_ejecutora.codigo también es PK textual (código presupuestal).",
        "convenio tiene dos FK self-referenciales: convenio_marco_id (para Convenio Específico) y convenio_origen_id (para Adendas).",
        "Los polimórficos (documento_adjunto, bitacora_auditoria, perfil_usuario_entidad) usan django_content_type + id_objeto (CharField para normalizar IPRESS varchar y demás int).",
        "Todos los estados de convenio, internado y rotación siguen un historial append-only (forward-only); no se eliminan registros de historial.",
        "campos_clinicos_asignados en campo_clinico_ipress es un acumulador calculado automáticamente por el service tras cada create/update/delete de asignación.",
    ]
    for i, n in enumerate(notes, 1):
        p = doc.add_paragraph(f"{i}. {n}")
        p.paragraph_format.left_indent = Inches(0.3)
        for run in p.runs:
            run.font.size = Pt(9)

    doc.add_paragraph()
    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = footer_p.add_run("RENADS — Documento de Análisis y Diseño  |  MINSA Perú  |  2026")
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x90, 0x90, 0x90)

    doc.save(OUT_PATH)
    print(f"Documento generado: {OUT_PATH}")


if __name__ == "__main__":
    build_document()
