# Plantillas de generación de convenios (docxtpl)

Plantillas Word (`.docx`) templatizadas con sintaxis **Jinja de docxtpl** que
`apps/convenios/pdf.py` renderiza con el contexto de `construir_contexto(convenio)`.

## Selección de plantilla

`pdf._seleccionar_plantilla(convenio)` elige de forma determinista por
`(tipo_convenio.codigo, es_adenda, unidad_organica.categoria)`:

| Archivo | Uso | Condición |
|---|---|---|
| `modelo_1_marco_lima.docx` | Convenio Marco, Lima | `MARCO` + no adenda + categoría `MINSA_DIRIS` |
| `modelo_2_marco_region.docx` | Convenio Marco, región | `MARCO` + no adenda + categoría `GOBIERNO_REGIONAL` |
| `modelo_3_especifico_lima.docx` | Específico, Lima | `ESPECIFICO` + no adenda + categoría `MINSA_DIRIS` |
| `modelo_4_especifico_region.docx` | Específico, región | `ESPECIFICO` + no adenda + categoría `GOBIERNO_REGIONAL` |
| `adenda.docx` | Adenda (Marco o Específico) | `es_adenda == True` |

Los cuatro primeros se derivan de `docs/plantillas_convenio/modelo 1..4.docx`
(cláusulas fijas conservadas; párrafos variables templatizados). `adenda.docx` se
reconstruyó con python-docx a partir de
`docs/modelo_adenda/ADENDA_02_AL_CONVENIO_036-2010-MINSA.pdf`.

Regeneración: `.venv/Scripts/python.exe scripts/build_convenio_templates.py`.

## Contrato de placeholders (contexto Jinja)

Todos los campos son opcionales en el render: `construir_contexto` nunca lanza por
datos faltantes (usa `""`). Claves del contexto:

- `titulo` — título/denominación del convenio.
- `nomenclatura` — nomenclatura oficial (solo Marco; `""` si no asignada).
- `dia`, `mes`, `anio` — fecha de suscripción/emisión desglosada.
- `fecha_inicio`, `fecha_fin` — periodo de vigencia (ISO `YYYY-MM-DD` o `""`).
- `vigencia_efectiva` — mayor `fecha_fin` de la cadena de adendas vigentes.
- `universidad` — `{ nombre, siglas }`.
- `convenio_marco` — `{ nomenclatura, vigencia_efectiva }` (Específico con Marco; `None` si no aplica).
- `convenio_origen` — `{ nomenclatura, titulo, fecha_suscripcion, fecha_inicio, fecha_fin }` (adendas).
- `carreras` — lista de nombres de carreras de la facultad del convenio (`university_careers` activas).
- `campos_clinicos` — lista de `{ ipress, carrera, especialidad, registrados, resolucion, fecha_resolucion }`.
- `partes` — lista de partes firmantes; cada elemento:
  - `rol_display` — etiqueta legible del rol (`get_rol_display`).
  - `organo` — `{ nombre, siglas }`.
  - `representante` — `{ nombre, numero_documento_identidad, numero_resolucion_designacion, numero_resolucion_facultades, sexo }`.
  - `cargo` — `{ nombre }` (masculino/femenino según `representante.sexo`).
  - `domicilio` — dirección de la entidad (MINSA fijo `Av. Salaverry 801, Jesús María, Lima`).
- `logo_minsa`, `logo_universidad` — `docxtpl.InlineImage` (o `""`), incrustados por `generar_expediente`.

## Uso por modelo

- **Encabezado / partes** (`{% for parte in partes %}…{% endfor %}`): todos los modelos.
- **Nomenclatura** (`{{ nomenclatura }}`): modelos Marco y adenda.
- **Objetivo / carreras** (`{% for carrera in carreras %}`): modelos Específico.
- **Antecedentes** (SUNEDU + cadena de Marco `{{ convenio_marco.* }}` + resoluciones
  CONAPRES/COREPRES `{% for cc in campos_clinicos %}`): modelos Específico.
- **Vigencia** (`{{ fecha_inicio }}`, `{{ fecha_fin }}`, `{{ vigencia_efectiva }}`): todos.
- **Adenda** (`{{ convenio_origen.* }}`, nuevo periodo): `adenda.docx`.
