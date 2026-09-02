"""Generación de PDF del proyecto de convenio y del expediente consolidado.

Tres etapas (C2/C3 de `spec/convenios_solicitud.md`):

1. `construir_contexto(convenio)` — arma el diccionario Jinja para docxtpl desde el
   `Convention`, sus partes firmantes, nomenclatura, carreras de la facultad,
   vigencia efectiva y campos clínicos CONAPRES. No lanza por datos opcionales.
2. `generar_docx` / `convertir_a_pdf` — renderiza la plantilla `.docx` con docxtpl y
   la convierte a PDF con LibreOffice headless (`soffice --headless --convert-to pdf`).
3. `generar_expediente(convenio)` — genera el proyecto y lo concatena (pypdf) con los
   PDFs adjuntos (resoluciones de los representantes firmantes y resoluciones CONAPRES
   de los campos clínicos), omitiendo los faltantes.

Los imports de `docxtpl` y `pypdf` son **diferidos** (dentro de las funciones) para
no exigir esas dependencias en el arranque/`check`. Sin lógica de negocio de estado
aquí: las reglas viven en `services`. Código en inglés; docstrings/errores en español.
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from apps.convenios import selectors

logger = logging.getLogger(__name__)

# Directorio con las plantillas `.docx` templatizadas (docxtpl).
PLANTILLAS_DIR = Path(__file__).resolve().parent / "templates" / "convenio"

# Domicilio legal fijo del MINSA (independiente de la entidad de la parte).
DOMICILIO_MINSA = "Av. Salaverry 801, Jesús María, Lima"

# Nombres de mes en español para el desglose de fechas del documento.
_MESES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre",
]

# Tiempo máximo (segundos) de la conversión LibreOffice antes de abortar.
_TIMEOUT_SOFFICE = 120


def _iso(fecha) -> str:
    """Devuelve la fecha en ISO (`YYYY-MM-DD`) o cadena vacía si es nula."""
    return fecha.isoformat() if fecha else ""


def _cargo_por_sexo(cargo, sexo: str) -> str:
    """Nombre del cargo en femenino si `sexo == 'F'` y existe; masculino en otro caso."""
    if cargo is None:
        return ""
    if sexo == "F" and getattr(cargo, "nombre_femenino", ""):
        return cargo.nombre_femenino
    return getattr(cargo, "nombre_masculino", "") or ""


def _domicilio_entidad(convenio, rol: str) -> str:
    """Resuelve el domicilio de la parte por rol desde la dirección de su entidad.

    MINSA usa siempre el domicilio fijo. El resto deriva de la entidad relacionada
    del convenio (gobierno regional, unidad ejecutora, universidad o facultad). Si la
    entidad o su dirección faltan, devuelve cadena vacía (nunca lanza).
    """
    if rol == "MINSA":
        return DOMICILIO_MINSA
    if rol == "GOBIERNO_REGIONAL":
        gore = getattr(convenio.organo_directorio, "gobierno_regional", None)
        return getattr(gore, "direccion", "") or "" if gore else ""
    if rol == "UNIDAD_EJECUTORA":
        return getattr(convenio.unidad_ejecutora, "direccion", "") or ""
    if rol == "UNIVERSIDAD":
        return getattr(convenio.universidad, "direccion_legal", "") or ""
    if rol == "FACULTAD":
        return getattr(convenio.facultad, "direccion", "") or ""
    return ""


def _contexto_partes(convenio) -> list[dict]:
    """Construye la lista de partes firmantes para el contexto Jinja."""
    partes = []
    qs = convenio.partes_firmantes.select_related(
        "organo_directorio", "organo_representante", "cargo_ejecutivo"
    ).order_by("orden", "id")
    for parte in qs:
        organo = parte.organo_directorio
        rep = parte.organo_representante
        cargo = parte.cargo_ejecutivo
        sexo = getattr(rep, "sexo", "") or ""
        partes.append(
            {
                "rol": parte.rol,
                "rol_display": parte.get_rol_display(),
                "organo": {
                    "nombre": getattr(organo, "nombre", "") or "",
                    "siglas": getattr(organo, "siglas", "") or "",
                },
                "representante": {
                    "nombre": getattr(rep, "nombre", "") or "",
                    "numero_documento_identidad": (
                        getattr(rep, "numero_documento_identidad", "") or ""
                    ),
                    "numero_resolucion_designacion": (
                        getattr(rep, "numero_resolucion_designacion", "") or ""
                    ),
                    "numero_resolucion_facultades": (
                        getattr(rep, "numero_resolucion_facultades", "") or ""
                    ),
                    "sexo": sexo,
                },
                "cargo": {"nombre": _cargo_por_sexo(cargo, sexo)},
                "domicilio": _domicilio_entidad(convenio, parte.rol),
            }
        )
    return partes


def _contexto_carreras(convenio) -> list[str]:
    """Nombres de las carreras activas de la facultad del convenio."""
    if not convenio.facultad_id:
        return []
    from apps.convenios.models import UniversityCareer

    qs = (
        UniversityCareer.objects.filter(facultad=convenio.facultad, activo=True)
        .select_related("carrera_profesional")
        .order_by("carrera_profesional__nombre")
    )
    return [uc.carrera_profesional.nombre for uc in qs]


def _contexto_campos_clinicos(convenio) -> list[dict]:
    """Campos clínicos CONAPRES del Específico (para antecedentes/expediente)."""
    if not convenio.unidad_ejecutora_id or not convenio.facultad_id:
        return []
    filas = []
    for cc in selectors.campos_clinicos_del_especifico(convenio):
        filas.append(
            {
                "ipress": getattr(cc.ipress, "nombre", "") or str(cc.ipress),
                "carrera": getattr(cc.carrera_profesional, "nombre", "") or "",
                "especialidad": (
                    getattr(cc.especialidad, "nombre", "") if cc.especialidad_id else ""
                ),
                "registrados": cc.campos_clinicos_registrados,
                "resolucion": cc.numero_resolucion_conapres or "",
                "fecha_resolucion": _iso(cc.fecha_resolucion_conapres),
            }
        )
    return filas


def construir_contexto(convenio) -> dict:
    """Arma el diccionario Jinja para renderizar la plantilla del convenio.

    Es una función de lectura pura: no persiste ni valida estado, y nunca lanza por
    datos opcionales faltantes (usa cadenas vacías / listas vacías). El domicilio del
    MINSA es fijo; el resto deriva de la dirección de la entidad de cada parte.
    """
    marco = convenio.convenio_marco
    origen = convenio.convenio_origen
    fecha_ref = convenio.fecha_inicio or convenio.fecha_solicitud

    contexto: dict = {
        "titulo": convenio.titulo or "",
        "nomenclatura": convenio.nomenclatura or "",
        "es_adenda": convenio.es_adenda,
        "fecha_inicio": _iso(convenio.fecha_inicio),
        "fecha_fin": _iso(convenio.fecha_fin),
        "vigencia_efectiva": _iso(selectors.vigencia_efectiva(convenio)),
        "dia": str(fecha_ref.day) if fecha_ref else "",
        "mes": _MESES[fecha_ref.month] if fecha_ref else "",
        "anio": str(fecha_ref.year) if fecha_ref else "",
        "universidad": {
            "nombre": getattr(convenio.universidad, "nombre", "") or "",
            "siglas": getattr(convenio.universidad, "siglas", "") or "",
        },
        "carreras": _contexto_carreras(convenio),
        "campos_clinicos": _contexto_campos_clinicos(convenio),
        "partes": _contexto_partes(convenio),
        # Logos: los rellena `generar_expediente` con InlineImage; vacío por defecto.
        "logo_minsa": "",
        "logo_universidad": "",
    }

    contexto["convenio_marco"] = (
        {
            "nomenclatura": marco.nomenclatura or "",
            "vigencia_efectiva": _iso(selectors.vigencia_efectiva(marco)),
        }
        if marco
        else None
    )
    contexto["convenio_origen"] = (
        {
            "nomenclatura": origen.nomenclatura or "",
            "titulo": origen.titulo or "",
            "fecha_suscripcion": _iso(origen.fecha_inicio or origen.fecha_solicitud),
            "fecha_inicio": _iso(origen.fecha_inicio),
            "fecha_fin": _iso(origen.fecha_fin),
        }
        if origen
        else None
    )
    return contexto


def _seleccionar_plantilla(convenio) -> Path:
    """Devuelve la ruta de la plantilla `.docx` según (tipo, es_adenda, categoría).

    Determinista. Las adendas usan `adenda.docx`. Marco/Específico se separan por la
    categoría del órgano del directorio (`MINSA_DIRIS` = Lima; `GOBIERNO_REGIONAL` =
    región). Lanza `RuntimeError` en español si no hay plantilla para la combinación.
    """
    if convenio.es_adenda:
        return PLANTILLAS_DIR / "adenda.docx"

    tipo = (convenio.tipo_convenio.codigo or "").upper()
    categoria = getattr(convenio.organo_directorio, "categoria", "")

    mapa = {
        ("MARCO", "MINSA_DIRIS"): "modelo_1_marco_lima.docx",
        ("MARCO", "GOBIERNO_REGIONAL"): "modelo_2_marco_region.docx",
        ("ESPECIFICO", "MINSA_DIRIS"): "modelo_3_especifico_lima.docx",
        ("ESPECIFICO", "GOBIERNO_REGIONAL"): "modelo_4_especifico_region.docx",
    }
    nombre = mapa.get((tipo, categoria))
    if nombre is None:
        raise RuntimeError(
            "No existe una plantilla de convenio para la combinación "
            f"tipo='{tipo}', categoría='{categoria}'. Verifique el tipo de convenio "
            "y la categoría del órgano del directorio."
        )
    return PLANTILLAS_DIR / nombre


def generar_docx(convenio, contexto: dict | None = None) -> bytes:
    """Renderiza la plantilla del convenio con docxtpl y devuelve el `.docx` en bytes.

    El import de `docxtpl` es diferido: solo se exige la dependencia al generar. Si
    `contexto` no se pasa, se arma con `construir_contexto`.
    """
    try:
        from docxtpl import DocxTemplate
    except ImportError as exc:  # pragma: no cover - dependencia opcional
        raise RuntimeError(
            "La librería docxtpl no está instalada; no es posible generar el "
            "documento Word del convenio. Instale las dependencias del proyecto."
        ) from exc

    plantilla = _seleccionar_plantilla(convenio)
    if not plantilla.exists():
        raise RuntimeError(
            f"No se encontró la plantilla '{plantilla.name}' en {PLANTILLAS_DIR}."
        )

    if contexto is None:
        contexto = construir_contexto(convenio)

    plantilla_docx = DocxTemplate(str(plantilla))
    plantilla_docx.render(contexto)
    import io

    buffer = io.BytesIO()
    plantilla_docx.save(buffer)
    return buffer.getvalue()


def convertir_a_pdf(docx_bytes: bytes) -> bytes:
    """Convierte un `.docx` (en bytes) a PDF con LibreOffice headless.

    Escribe el `.docx` en un directorio temporal, invoca
    `soffice --headless --convert-to pdf --outdir <tmp> <docx>` con timeout, lee el
    PDF resultante y limpia los temporales. Lanza `RuntimeError` en español si
    `soffice` no está en el PATH o si la conversión falla.
    """
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if not soffice:
        raise RuntimeError(
            "LibreOffice (soffice) no está disponible en el PATH; no es posible "
            "convertir el documento a PDF. Instale LibreOffice y asegúrese de que "
            "'soffice' sea ejecutable en el entorno del servidor."
        )

    tmpdir = tempfile.mkdtemp(prefix="convenio_pdf_")
    try:
        ruta_docx = Path(tmpdir) / "convenio.docx"
        ruta_docx.write_bytes(docx_bytes)

        try:
            resultado = subprocess.run(
                [
                    soffice, "--headless", "--convert-to", "pdf",
                    "--outdir", tmpdir, str(ruta_docx),
                ],
                capture_output=True,
                timeout=_TIMEOUT_SOFFICE,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "La conversión a PDF con LibreOffice superó el tiempo máximo. "
                "Reintente o revise la carga del servidor de conversión."
            ) from exc

        ruta_pdf = Path(tmpdir) / "convenio.pdf"
        if resultado.returncode != 0 or not ruta_pdf.exists():
            detalle = (resultado.stderr or b"").decode("utf-8", "ignore").strip()
            raise RuntimeError(
                "LibreOffice no pudo convertir el documento a PDF. "
                f"Detalle: {detalle or 'sin salida de error'}."
            )
        return ruta_pdf.read_bytes()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def generar_proyecto(convenio) -> bytes:
    """Genera el proyecto de convenio (docx renderizado + conversión a PDF)."""
    return convertir_a_pdf(generar_docx(convenio))


def _descargar_binario(referencia: str) -> bytes | None:
    """Descarga el binario de un `Document` del storage activo; None si falla.

    Usa `get_document_storage().url_firmada` y descarga por HTTP. Si el backend
    devuelve una ruta local/externa (stub), intenta leerla directamente. Nunca lanza:
    omite el adjunto con log si no puede obtenerse.
    """
    from apps.common.storage import get_document_storage

    if not referencia:
        return None
    storage = get_document_storage()
    try:
        url = storage.url_firmada(referencia)
    except Exception:  # pragma: no cover - backend puede fallar
        logger.warning("No se pudo firmar la URL de '%s'; se omite el adjunto.", referencia)
        return None

    # Descarga por HTTP (presigned URL de R2/GCS).
    if url.startswith("http://") or url.startswith("https://"):
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
                return resp.read()
        except Exception:
            logger.warning("No se pudo descargar el adjunto '%s'; se omite.", referencia)
            return None

    # Backend stub / ruta local: intenta leer el archivo directamente.
    try:
        ruta = Path(url)
        if ruta.exists():
            return ruta.read_bytes()
    except OSError:
        pass
    logger.warning("El adjunto '%s' no es una URL descargable; se omite.", referencia)
    return None


def _pdfs_adjuntos_del_expediente(convenio) -> list[bytes]:
    """Reúne los PDFs adjuntos a incluir en el expediente (best-effort).

    Incluye las resoluciones (`Document` ACTIVO) de:
    - los representantes firmantes del convenio (actor `REPRESENTANTE`), y
    - los campos clínicos CONAPRES del Específico (actor `CAMPO_CLINICO`).
    Omite (con log) los binarios que no puedan descargarse.
    """
    from apps.convenios.selectors import documentos_de

    binarios: list[bytes] = []

    # Resoluciones de los representantes firmantes.
    representantes = {
        p.organo_representante
        for p in convenio.partes_firmantes.select_related("organo_representante").all()
        if p.organo_representante_id
    }
    for rep in representantes:
        for doc in documentos_de(rep).filter(estado="ACTIVO"):
            data = _descargar_binario(doc.referencia_externa)
            if data:
                binarios.append(data)

    # Resoluciones CONAPRES de los campos clínicos del Específico.
    if convenio.unidad_ejecutora_id and convenio.facultad_id:
        for cc in selectors.campos_clinicos_del_especifico(convenio):
            for doc in documentos_de(cc).filter(estado="ACTIVO"):
                data = _descargar_binario(doc.referencia_externa)
                if data:
                    binarios.append(data)

    return binarios


def generar_expediente(convenio) -> bytes:
    """Genera el expediente: proyecto (PDF) + merge de los PDFs adjuntos existentes.

    Concatena con pypdf el proyecto y las resoluciones de los representantes firmantes
    y de los campos clínicos CONAPRES. Los adjuntos faltantes o ilegibles se omiten
    (con log), sin fallar. El import de `pypdf` es diferido. Devuelve un único PDF.
    """
    try:
        import io

        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:  # pragma: no cover - dependencia opcional
        raise RuntimeError(
            "La librería pypdf no está instalada; no es posible consolidar el "
            "expediente. Instale las dependencias del proyecto."
        ) from exc

    proyecto_pdf = generar_proyecto(convenio)

    escritor = PdfWriter()
    for lector_bytes in [proyecto_pdf, *_pdfs_adjuntos_del_expediente(convenio)]:
        try:
            lector = PdfReader(io.BytesIO(lector_bytes))
            for pagina in lector.pages:
                escritor.add_page(pagina)
        except Exception:
            logger.warning("Un adjunto del expediente no es un PDF válido; se omite.")

    salida = io.BytesIO()
    escritor.write(salida)
    return salida.getvalue()
