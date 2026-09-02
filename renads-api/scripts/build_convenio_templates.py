"""Genera las 5 plantillas `.docx` templatizadas (Jinja de docxtpl) del módulo Convenios.

Uso (una sola vez, para (re)generar las plantillas en `apps/convenios/templates/convenio/`):

    .venv/Scripts/python.exe scripts/build_convenio_templates.py

Estrategia (best-effort): copia cada `.docx` fuente de `docs/plantillas_convenio/`,
reemplaza el TEXTO de los párrafos variables (título/encabezado, objetivo/carreras,
antecedentes, vigencia y cierre) por una versión con placeholders Jinja
`{{ ... }}` / `{% for %}`, e inserta el bloque de partes firmantes y de firmas.
Las cláusulas fijas del cuerpo se conservan tal cual del documento fuente.

La adenda (`adenda.docx`) se reconstruye desde cero con python-docx a partir del
texto/estructura de cláusulas del PDF de referencia
`docs/modelo_adenda/ADENDA_02_AL_CONVENIO_036-2010-MINSA.pdf`.

Este script NO forma parte del runtime; se ejecuta manualmente para producir los
binarios versionados. Comentarios/mensajes en español; código en inglés.
"""

from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "docs" / "plantillas_convenio"
DST = BASE / "apps" / "convenios" / "templates" / "convenio"

# Bloque Jinja reutilizable: recorre las partes firmantes con sus datos.
BLOQUE_PARTES = (
    "{% for parte in partes %}"
    "{{ parte.rol_display }}: {{ parte.organo.nombre }}"
    "{% if parte.organo.siglas %} ({{ parte.organo.siglas }}){% endif %}, "
    "representado/a por {{ parte.representante.nombre }}, "
    "identificado/a con documento N° {{ parte.representante.numero_documento_identidad }}, "
    "en el cargo de {{ parte.cargo.nombre }}"
    "{% if parte.representante.numero_resolucion_designacion %}, "
    "designado/a mediante Resolución N° {{ parte.representante.numero_resolucion_designacion }}"
    "{% endif %}"
    "{% if parte.representante.numero_resolucion_facultades %}, "
    "facultado/a mediante Resolución N° {{ parte.representante.numero_resolucion_facultades }}"
    "{% endif %}, con domicilio en {{ parte.domicilio }}.\n"
    "{% endfor %}"
)

# Encabezado "Conste por el presente documento…" (partes firmantes estructuradas).
ENCABEZADO_CONVENIO = (
    "Conste por el presente documento el {{ titulo }}, que celebran las siguientes "
    "partes:\n" + BLOQUE_PARTES +
    "En los términos y condiciones de las cláusulas siguientes:"
)


def _set_texto(parrafo, texto):
    """Reemplaza el texto de un párrafo por `texto`, conservando su primer estilo de run.

    docxtpl procesa la sintaxis Jinja sobre el texto plano de los runs; al colapsar
    el párrafo en un único run se garantiza que las etiquetas `{{ }}`/`{% %}` no
    queden partidas entre runs distintos.
    """
    if parrafo.runs:
        parrafo.runs[0].text = texto
        for run in parrafo.runs[1:]:
            run.text = ""
    else:
        parrafo.add_run(texto)


def _templatizar_convenio(nombre_fuente, nombre_destino, *, es_especifico):
    """Copia un modelo de convenio y templatiza sus párrafos variables."""
    doc = docx.Document(str(SRC / nombre_fuente))
    parrafos = doc.paragraphs

    # Índice del párrafo "Conste por el presente documento…" y de la nomenclatura.
    idx_conste = next(
        i for i, p in enumerate(parrafos)
        if p.text.strip().startswith("Conste por el presente")
    )
    _set_texto(parrafos[idx_conste], ENCABEZADO_CONVENIO)

    # Título / nomenclatura: el primer párrafo con "CONVENIO N°" o el título en negrita.
    for p in parrafos:
        t = p.text.strip()
        if t.startswith("CONVENIO N") or t.startswith("CONVENIO Nº"):
            _set_texto(
                p,
                "{% if nomenclatura %}{{ nomenclatura }}{% else %}CONVENIO N° "
                "______-{{ anio }}-MINSA{% endif %}",
            )
            break

    # Objetivo / carreras: párrafo de la cláusula de objeto/objetivo con carreras.
    for p in parrafos:
        t = p.text.strip()
        if es_especifico and t.startswith("Establecer los acuerdos"):
            _set_texto(
                p,
                "Establecer los acuerdos para desarrollar actividades de formación "
                "correspondientes al pregrado para la/s carrera/s profesional/es de: "
                "{% for carrera in carreras %}{{ carrera }}"
                "{% if not loop.last %}, {% endif %}{% endfor %}, mediante acciones "
                "de docencia-servicio e investigación a ser realizadas por los "
                "estudiantes de LA FACULTAD en la sede docente.",
            )
            break

    # Antecedentes (solo Específico): licenciamiento SUNEDU + cadena de Marco + CONAPRES/COREPRES.
    if es_especifico:
        for p in parrafos:
            t = p.text.strip()
            if t.startswith("La Universidad") and "SUNEDU" in t:
                _set_texto(
                    p,
                    "LA UNIVERSIDAD {{ universidad.nombre }} cuenta con Licencia "
                    "Institucional otorgada por la Superintendencia Nacional de "
                    "Educación Superior Universitaria (SUNEDU).",
                )
            elif t.startswith("La Universidad") and "Convenio Marco" in t:
                _set_texto(
                    p,
                    "{% if convenio_marco %}LA UNIVERSIDAD suscribió con el Ministerio "
                    "de Salud el Convenio Marco {{ convenio_marco.nomenclatura }}, "
                    "Convenio Marco de Cooperación Docente Asistencial, con vigencia "
                    "hasta el {{ convenio_marco.vigencia_efectiva }}.{% endif %}",
                )
            elif t.startswith("Mediante Acuerdo") and (
                "CONAPRES" in t or "COREPRES" in t
            ):
                _set_texto(
                    p,
                    "Mediante Acuerdo del Comité de Pregrado de Salud "
                    "(CONAPRES/COREPRES) se otorgó opinión favorable al presente "
                    "Convenio Específico. Los campos clínicos autorizados constan en "
                    "las resoluciones CONAPRES adjuntas al expediente"
                    "{% if campos_clinicos %}: {% for cc in campos_clinicos %}"
                    "{{ cc.ipress }} — {{ cc.carrera }} "
                    "(Res. {{ cc.resolucion }}){% if not loop.last %}; {% endif %}"
                    "{% endfor %}{% endif %}.",
                )

    # Vigencia: párrafo de la cláusula de vigencia.
    for p in parrafos:
        t = p.text.strip()
        if t.startswith("El presente convenio tiene una vigencia") or t.startswith(
            "El presente Convenio Específico tendr"
        ):
            _set_texto(
                p,
                "El presente convenio tiene vigencia desde el {{ fecha_inicio }} "
                "hasta el {{ fecha_fin }} (vigencia efectiva de la cadena: "
                "{{ vigencia_efectiva }}), contados a partir de la fecha de su "
                "suscripción, pudiendo ser renovado de común acuerdo entre las "
                "partes mediante adenda.",
            )
            break

    # Cierre: párrafo "En señal de conformidad…".
    for p in parrafos:
        t = p.text.strip()
        if t.startswith("En señal de conformidad"):
            _set_texto(
                p,
                "En señal de conformidad suscriben las partes el presente convenio, "
                "a los {{ dia }} días del mes de {{ mes }} del año {{ anio }}.",
            )
            break

    # Bloque de firmas al final del documento.
    doc.add_paragraph()
    firma_par = doc.add_paragraph()
    _set_texto(
        firma_par,
        BLOQUE_PARTES
        + "{% for parte in partes %}________________________\n"
        + "{{ parte.representante.nombre }}\n{{ parte.cargo.nombre }}\n"
        + "{{ parte.organo.nombre }}\n\n{% endfor %}",
    )

    doc.save(str(DST / nombre_destino))
    print("Generado:", nombre_destino)


def _construir_adenda():
    """Reconstruye `adenda.docx` desde cero según el PDF de referencia."""
    doc = docx.Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Arial"
    estilo.font.size = Pt(11)

    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run(
        "{% if nomenclatura %}{{ nomenclatura }}{% else %}ADENDA N° ___ AL "
        "{{ convenio_origen.nomenclatura }}{% endif %}"
    )
    run.bold = True

    subtitulo = doc.add_paragraph()
    subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitulo.add_run("{{ titulo }}")
    run.bold = True

    doc.add_paragraph(
        "Conste por el presente documento la Adenda al "
        "{{ convenio_origen.nomenclatura }}, que celebran las siguientes partes:\n"
        + BLOQUE_PARTES
        + "En los términos y condiciones siguientes:"
    )

    p = doc.add_paragraph()
    p.add_run("CLÁUSULA PRIMERA: ANTECEDENTES").bold = True
    doc.add_paragraph(
        "Con fecha {{ convenio_origen.fecha_suscripcion }} se suscribió el "
        "{{ convenio_origen.nomenclatura }}, {{ convenio_origen.titulo }}, el mismo "
        "que tiene por objeto crear el marco de cooperación entre las partes para la "
        "adecuada formación y capacitación de profesionales de la salud."
    )
    doc.add_paragraph(
        "LA UNIVERSIDAD {{ universidad.nombre }} solicita la ampliación de la "
        "vigencia del convenio de origen."
    )

    p = doc.add_paragraph()
    p.add_run("CLÁUSULA SEGUNDA: OBJETO DE LA ADENDA").bold = True
    doc.add_paragraph(
        "Mediante la presente Adenda las partes acuerdan ampliar el plazo de "
        "vigencia del {{ convenio_origen.nomenclatura }}, estableciendo un nuevo "
        "periodo de vigencia desde el {{ fecha_inicio }} hasta el {{ fecha_fin }} "
        "(vigencia efectiva de la cadena: {{ vigencia_efectiva }}), pudiendo ser "
        "renovado de común acuerdo entre las partes."
    )

    p = doc.add_paragraph()
    p.add_run("CLÁUSULA TERCERA: DECLARACIÓN").bold = True
    doc.add_paragraph(
        "Por la presente cláusula las partes reconocen la vigencia de las demás "
        "cláusulas contenidas en el {{ convenio_origen.nomenclatura }}, en todo lo "
        "que no se oponga a la presente Adenda."
    )

    doc.add_paragraph(
        "En señal de conformidad, las partes suscriben la presente Adenda en dos "
        "ejemplares de un solo tenor e igualmente válidos, en la ciudad de Lima a "
        "los {{ dia }} días del mes de {{ mes }} del año {{ anio }}."
    )

    doc.add_paragraph()
    doc.add_paragraph(
        BLOQUE_PARTES
        + "{% for parte in partes %}________________________\n"
        + "{{ parte.representante.nombre }}\n{{ parte.cargo.nombre }}\n"
        + "{{ parte.organo.nombre }}\n\n{% endfor %}"
    )

    doc.save(str(DST / "adenda.docx"))
    print("Generado: adenda.docx (reconstruido con python-docx)")


def main():
    DST.mkdir(parents=True, exist_ok=True)
    _templatizar_convenio("modelo 1.docx", "modelo_1_marco_lima.docx", es_especifico=False)
    _templatizar_convenio("modelo 2.docx", "modelo_2_marco_region.docx", es_especifico=False)
    _templatizar_convenio("modelo 3.docx", "modelo_3_especifico_lima.docx", es_especifico=True)
    _templatizar_convenio("modelo 4.docx", "modelo_4_especifico_region.docx", es_especifico=True)
    _construir_adenda()


if __name__ == "__main__":
    main()
