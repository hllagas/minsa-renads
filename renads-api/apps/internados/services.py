"""Services del módulo Internados: casos de uso de escritura y reglas de negocio (RN).

Toda escritura en `transaction.atomic()`, con auditoría en `bitacora_auditoria` y
registro en el historial de estado correspondiente. Ver §6 del módulo 2.
"""

import datetime
import decimal
import logging
import re
import secrets

import openpyxl
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.common.models import UserSecurity
from apps.common.selectors import usuario_pertenece_a_entidad
from apps.common.services import registrar_auditoria
from apps.convenios.models import (
    Document,
    ProfessionalCareer,
    Specialty,
    Ubigeo,
    University,
    UserEntityProfile,
)
from apps.internados.models import (
    InternshipPeriod,
    AnnexDocument,
    IdentityDocumentType,
    Internship,
    InternshipStatus,
    InternshipStatusHistory,
    RelationshipType,
    Rotation,
    RotationAuthorization,
    RotationStatus,
    RotationStatusHistory,
    Student,
    TutorConvenio,
    TutorHistory,
)

logger = logging.getLogger(__name__)

# Estados del Convenio Específico que habilitan registrar internados (RN-2/3).
ESTADOS_CONVENIO_VIGENTE = {"VIGENTE", "PUBLICADO", "SUSCRITO"}
MAX_ROTACIONES = 4  # RN-9

# RN-21 — Estados del internado que bloquean una nueva asignación (internado vigente).
ESTADOS_INTERNADO_BLOQUEANTES = {
    "REGISTRADO", "PENDIENTE_VALIDACION", "OBSERVADO", "VALIDADO", "ACTIVO",
    "EN_ROTACION_SOLICITADA", "EN_ROTACION_AUTORIZADA", "EN_ROTACION_OBSERVADA",
}
# Estados liberadores (no bloquean un nuevo registro): SUSPENDIDO, RETIRADO, CULMINADO, ANULADO.

# RN-22 — Grupo (rol) asignado al interno aprovisionado.
GRUPO_INTERNO = "Interno"

# RN-24 — Un tutor pertenece de 1 a 2 universidades (tope de negocio).
MAX_UNIVERSIDADES_TUTOR = 2


def validar_universidades_tutor(universidades) -> None:
    """Valida la regla RN-24: un tutor pertenece de 1 a ``MAX_UNIVERSIDADES_TUTOR`` universidades.

    ``universidades`` es la colección de universidades a asignar. Lanza
    ``ValidationError`` (mensaje en español) si está vacía o excede el tope.
    Fuente única compartida por el registro individual (serializer) y cualquier
    otro flujo que asigne universidades a un tutor.
    """
    cantidad = len(universidades)
    if cantidad < 1:
        raise ValidationError({"universidades": "El tutor debe pertenecer al menos a una universidad."})
    if cantidad > MAX_UNIVERSIDADES_TUTOR:
        raise ValidationError(
            {"universidades": f"El tutor no puede pertenecer a más de {MAX_UNIVERSIDADES_TUTOR} universidades."}
        )
    if len({u.pk for u in universidades}) != cantidad:
        raise ValidationError({"universidades": "Hay universidades repetidas en la lista."})


@transaction.atomic
def crear_tutor_convenio(*, tutor, convenio, ipress, usuario) -> TutorConvenio:
    """Vincula un tutor a un Convenio Específico e IPRESS (RN-TC-01, RN-TC-02).

    - RN-TC-01: solo se admiten Convenios Específicos.
    - RN-TC-02: la combinación (tutor, convenio) debe ser única; se anticipa el
      ``IntegrityError`` con un mensaje legible antes del hit a la BD.
    Registra auditoría tras crear el vínculo.
    """
    # RN-TC-01: solo Convenios Específicos.
    if convenio.tipo_convenio.codigo != "ESPECIFICO":
        raise ValidationError("Solo se pueden asociar Convenios Específicos a un tutor.")
    # RN-TC-02: unicidad anticipada (mensaje legible antes del IntegrityError).
    if TutorConvenio.objects.filter(tutor=tutor, convenio=convenio).exists():
        raise ValidationError("El tutor ya está asociado a este convenio.")

    tutor_convenio = TutorConvenio.objects.create(
        tutor=tutor,
        convenio=convenio,
        ipress=ipress,
    )
    registrar_auditoria(usuario, "CREAR", tutor_convenio)
    return tutor_convenio


@transaction.atomic
def eliminar_tutor_convenio(*, tutor_convenio: TutorConvenio, usuario) -> None:
    """Elimina el vínculo tutor ↔ convenio. Registra auditoría antes de borrar."""
    registrar_auditoria(usuario, "ELIMINAR", tutor_convenio)
    tutor_convenio.delete()


# Columnas requeridas del Excel de carga masiva de estudiantes (RN-16, §6 bis schema M2).
# Se expresan con la clave canónica interna (ver CARGA_ALIAS_COLUMNAS).
# Columnas base requeridas (siempre). El campo de nivel (carrera_profesional o
# especialidad) se detecta dinámicamente del encabezado — ver registrar_estudiantes_masivo.
CARGA_COLUMNAS_REQUERIDAS = {
    "tipo_documento", "numero_documento", "nombres", "apellido_paterno",
}

# Alias de encabezados del Excel → clave canónica interna.
# `universidad` y `periodo_internado` ya no vienen en el Excel: se reciben como
# parámetros fijos del endpoint (tomados de los filtros de la UI).
# `ubigeo` se reemplazó por los tres campos: departamento / provincia / distrito.
CARGA_ALIAS_COLUMNAS = {
    "tipo_documento_identidad_id": "tipo_documento",
    "contacto_emergencia_parentesco_id": "contacto_emergencia_parentesco",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sumar_anios(fecha: datetime.date, anios: int) -> datetime.date:
    try:
        return fecha.replace(year=fecha.year + anios)
    except ValueError:
        return fecha.replace(year=fecha.year + anios, day=28)


def _estado_internado(codigo: str) -> InternshipStatus:
    try:
        return InternshipStatus.objects.get(codigo=codigo)
    except InternshipStatus.DoesNotExist as exc:
        raise ValidationError(f"Estado de internado inexistente: {codigo}.") from exc


def _estado_rotacion(codigo: str) -> RotationStatus:
    try:
        return RotationStatus.objects.get(codigo=codigo)
    except RotationStatus.DoesNotExist as exc:
        raise ValidationError(f"Estado de rotación inexistente: {codigo}.") from exc


def _set_estado_internado(internado: Internship, codigo: str, usuario, observacion: str = "") -> Internship:
    estado = _estado_internado(codigo)
    anterior = internado.estado_actual.codigo if internado.estado_actual_id else ""
    internado.estado_actual = estado
    internado.save(update_fields=["estado_actual", "actualizado_en"])
    InternshipStatusHistory.objects.create(
        interno=internado, estado=estado, cambiado_por=usuario, observacion=observacion
    )
    registrar_auditoria(
        usuario, "CAMBIO_ESTADO", internado,
        nombre_campo="estado_actual", valor_anterior=anterior, valor_nuevo=codigo,
    )
    return internado


def _set_estado_rotacion(rotacion: Rotation, codigo: str, usuario, observacion: str = "") -> Rotation:
    estado = _estado_rotacion(codigo)
    anterior = rotacion.estado_actual.codigo if rotacion.estado_actual_id else ""
    rotacion.estado_actual = estado
    rotacion.save(update_fields=["estado_actual"])
    RotationStatusHistory.objects.create(
        rotacion=rotacion, estado=estado, cambiado_por=usuario, observacion=observacion
    )
    registrar_auditoria(
        usuario, "CAMBIO_ESTADO", rotacion,
        nombre_campo="estado_actual", valor_anterior=anterior, valor_nuevo=codigo,
    )
    return rotacion


# ---------------------------------------------------------------------------
# Internado
# ---------------------------------------------------------------------------
@transaction.atomic
def crear_internado(*, datos: dict, usuario) -> Internship:
    convenio = datos["convenio"]
    campo_clinico = datos["campo_clinico"]
    fecha_inicio = datos["fecha_inicio"]
    fecha_fin = datos["fecha_fin"]
    estudiante = datos["estudiante"]

    # RN-20: el acceso por universidad (alcance institucional) se valida en la vista
    # (`InternshipViewSet.create` → `exigir_ambito(usuario, ContentType(University), universidad_del_estudiante)`).
    # RN-21: unicidad de interno por DNI — rechazar si ya tiene un internado vigente.
    if tiene_internado_vigente(estudiante):
        raise ValidationError(
            {"estudiante": "El estudiante ya tiene un internado vigente; no puede registrarse otro."}
        )

    # RN-4: no se permite sobre Convenio Marco.
    if convenio.tipo_convenio.codigo != "ESPECIFICO":
        raise ValidationError({"convenio": "El internado requiere un Convenio Específico."})
    # RN-2/3: convenio vigente.
    if not convenio.estado_actual_id or convenio.estado_actual.codigo not in ESTADOS_CONVENIO_VIGENTE:
        raise ValidationError({"convenio": "El Convenio Específico debe estar vigente."})
    # El campo clínico debe pertenecer al convenio.
    if campo_clinico.convenio_id != convenio.id:
        raise ValidationError({"campo_clinico": "El campo clínico no pertenece al convenio indicado."})
    # RN-13: no exceder los campos clínicos autorizados de la asignación.
    usados = Internship.objects.filter(campo_clinico=campo_clinico).count()
    if usados >= campo_clinico.campos_clinicos_autorizados:
        raise ValidationError({"campo_clinico": "Se alcanzó el máximo de campos clínicos autorizados."})
    # RN-6: duración máxima de un año.
    if fecha_fin > _sumar_anios(fecha_inicio, 1):
        raise ValidationError({"fecha_fin": "El internado no puede durar más de un año."})
    if fecha_fin < fecha_inicio:
        raise ValidationError({"fecha_fin": "La fecha de fin no puede ser anterior a la de inicio."})
    # Ámbito geográfico sanitario: se DERIVA de la IPRESS (sede docente) del campo clínico —que
    # pertenece a la unidad ejecutora del convenio— ya que no lo elige el usuario. Si el cliente lo
    # envía, debe coincidir (retrocompatibilidad); si no, se toma el de la sede docente.
    ambito_sede = campo_clinico.ipress.ambito_geografico_sanitario
    ambito_enviado = datos.get("ambito_geografico_sanitario")
    if ambito_enviado is not None and ambito_enviado.id != ambito_sede.id:
        raise ValidationError(
            {"ambito_geografico_sanitario": "Debe coincidir con el ámbito de la sede docente."}
        )
    ambito = ambito_enviado or ambito_sede

    estado_inicial = _estado_internado("REGISTRADO")
    internado = Internship.objects.create(
        estudiante=estudiante,
        convenio=convenio,
        campo_clinico=campo_clinico,
        ipress=datos["ipress"],
        tutor=datos["tutor"],
        ambito_geografico_sanitario=ambito,
        estado_actual=estado_inicial,
        estado_declaraciones="PENDIENTE",
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        observaciones=datos.get("observaciones", ""),
        creado_por=usuario,
    )
    InternshipStatusHistory.objects.create(
        interno=internado, estado=estado_inicial, cambiado_por=usuario
    )
    registrar_auditoria(usuario, "CREAR", internado)

    # RN-22: onboarding del interno — usuario con rol `Interno` y perfil sobre su Student.
    aprovisionar_interno(internado, usuario)
    # Notificación por correo best-effort (post-commit; un fallo no revierte el registro).
    transaction.on_commit(lambda: notificar_registro_interno(internado))
    return internado


# ---------------------------------------------------------------------------
# RN-21 — Unicidad de interno por DNI (un internado vigente por estudiante)
# ---------------------------------------------------------------------------
def tiene_internado_vigente(estudiante: Student) -> bool:
    """Indica si el estudiante tiene un `Internship` en estado bloqueante (RN-21).

    Los estados **liberadores** (``SUSPENDIDO``, ``RETIRADO``, ``CULMINADO``,
    ``ANULADO``) no bloquean una nueva asignación.
    """
    return Internship.objects.filter(
        estudiante=estudiante, estado_actual__codigo__in=ESTADOS_INTERNADO_BLOQUEANTES
    ).exists()


# ---------------------------------------------------------------------------
# RN-22 — Aprovisionamiento del interno (usuario + rol + perfil)
# ---------------------------------------------------------------------------
def aprovisionar_interno(internado: Internship, usuario) -> User:
    """Crea (o recupera) el usuario `Interno` del estudiante del internado (RN-22).

    - ``username = estudiante.numero_documento``. Si el usuario ya existe (reingreso
      tras un estado liberador), se reutiliza sin resetear su contraseña.
    - Al crear: contraseña temporal aleatoria, ``is_staff=False`` y
      ``debe_cambiar_password=True`` (vía ``UserSecurity``).
    - Asigna el grupo ``Interno`` y un ``UserEntityProfile`` idempotente sobre el
      ``Student`` (rol ``Interno``, ``activo=True``).
    Devuelve el ``User``.
    """
    estudiante = internado.estudiante
    username = estudiante.numero_documento

    interno_group, _ = Group.objects.get_or_create(name=GRUPO_INTERNO)
    usuario_interno = User.objects.filter(username=username).first()
    creado = usuario_interno is None
    if creado:
        usuario_interno = User(
            username=username,
            email=estudiante.correo or "",
            first_name=estudiante.nombres[:150],
            last_name=f"{estudiante.apellido_paterno} {estudiante.apellido_materno}".strip()[:150],
            is_staff=False,
            is_active=True,
        )
        usuario_interno.set_password(secrets.token_urlsafe(16))
        usuario_interno.save()
        registrar_auditoria(usuario, "CREAR", usuario_interno)

    usuario_interno.groups.add(interno_group)

    seguridad, _ = UserSecurity.objects.get_or_create(usuario=usuario_interno)
    if creado and not seguridad.debe_cambiar_password:
        seguridad.debe_cambiar_password = True
        seguridad.save(update_fields=["debe_cambiar_password", "actualizado_en"])

    ct_student = ContentType.objects.get_for_model(Student)
    UserEntityProfile.objects.get_or_create(
        usuario=usuario_interno,
        tipo_contenido=ct_student,
        id_objeto=estudiante.pk,
        grupo=interno_group,
        defaults={"activo": True},
    )
    return usuario_interno


# ---------------------------------------------------------------------------
# RN-22 — Notificación por correo al interno (best-effort)
# ---------------------------------------------------------------------------
def notificar_registro_interno(internado: Internship) -> bool:
    """Notifica por correo al estudiante su registro como interno (RN-22).

    Best-effort: si el estudiante no tiene correo, o el envío falla, se registra un
    aviso en el log y **no** se propaga la excepción (no revierte el registro).
    Devuelve ``True`` si se intentó el envío, ``False`` si se omitió.
    """
    estudiante = internado.estudiante
    correo = (estudiante.correo or "").strip()
    if not correo:
        logger.warning(
            "No se envió correo de onboarding: el estudiante %s no tiene correo registrado.",
            estudiante.numero_documento,
        )
        return False

    ipress = internado.ipress
    campo = internado.campo_clinico
    tutor = internado.tutor
    nombre_estudiante = f"{estudiante.nombres} {estudiante.apellido_paterno}".strip()
    sede = ipress.nombre if ipress else "(no registrada)"
    carrera = getattr(campo.carrera_profesional, "nombre", "") if campo else ""
    campo_txt = f"{carrera} (campo clínico #{campo.pk})".strip() if campo else "(no registrado)"
    tutor_txt = f"{tutor.nombres} {tutor.apellido_paterno}".strip() if tutor else "(no asignado)"
    tutor_correo = (tutor.correo or "").strip() if tutor else ""

    asunto = "RENADS — Registro como interno"
    cuerpo = (
        f"Estimado(a) {nombre_estudiante}:\n\n"
        f"Ha sido registrado(a) como interno(a) en el sistema RENADS con los siguientes datos:\n\n"
        f"- Sede docente (IPRESS): {sede}\n"
        f"- Campo clínico: {campo_txt}\n"
        f"- Fecha de inicio: {internado.fecha_inicio}\n"
        f"- Fecha de fin: {internado.fecha_fin}\n"
        f"- Tutor asignado: {tutor_txt}"
        + (f" ({tutor_correo})" if tutor_correo else "")
        + "\n\n"
        f"Debe adjuntar sus declaraciones juradas en el sistema. Consulte su checklist en:\n"
        f"  /api/v1/interns/{internado.pk}/annex-checklist/\n"
        f"y adjunte cada anexo en:\n"
        f"  /api/v1/interns/{internado.pk}/annex-upload/\n\n"
        f"Atentamente,\nRENADS — MINSA"
    )
    try:
        send_mail(
            asunto,
            cuerpo,
            settings.DEFAULT_FROM_EMAIL,
            [correo],
            fail_silently=False,
        )
        return True
    except Exception:  # noqa: BLE001 — best-effort: no revertir el registro
        logger.exception(
            "Falló el envío del correo de onboarding al interno %s.",
            estudiante.numero_documento,
        )
        return False


# ---------------------------------------------------------------------------
# RN-23 — Estado de las declaraciones juradas del interno
# ---------------------------------------------------------------------------
def _declaraciones_completas(internado: Internship) -> bool:
    """True si todas las DJ obligatorias del interno tienen una versión ACTIVO adjunta.

    Los anexos (declaraciones juradas) se adjuntan por interno (``Internship``) vía
    ``AnnexAttachmentMixin`` (actor ``INTERNO``); aquí se cruza el catálogo maestro
    con los ``Document`` ``ACTIVO`` del internado.
    """
    obligatorios = set(
        AnnexDocument.objects.filter(
            activo=True, tipo_actor="INTERNO", obligatorio=True
        ).values_list("id", flat=True)
    )
    if not obligatorios:
        return True
    ct_interno = ContentType.objects.get_for_model(Internship)
    adjuntados = set(
        Document.objects.filter(
            tipo_contenido=ct_interno,
            id_objeto=internado.pk,
            estado="ACTIVO",
            documento_anexo__isnull=False,
        ).values_list("documento_anexo_id", flat=True)
    )
    return obligatorios.issubset(adjuntados)


@transaction.atomic
def recalcular_estado_declaraciones(internado: Internship, usuario=None) -> Internship:
    """Recalcula ``estado_declaraciones`` tras un adjunto de anexo (RN-23, fuente única).

    - Si el checklist obligatorio está completo ⇒ ``COMPLETAS``.
    - Si no lo está y no está en revisión (``VALIDADAS``) ⇒ ``PENDIENTE``.
    No degrada un estado ``VALIDADAS`` (revisión humana ya conforme). Registra
    historial + auditoría solo si el estado cambia.
    """
    if internado.estado_declaraciones == "VALIDADAS":
        return internado
    nuevo = "COMPLETAS" if _declaraciones_completas(internado) else "PENDIENTE"
    if nuevo != internado.estado_declaraciones:
        _set_estado_declaraciones(internado, nuevo, usuario, observacion="Recálculo automático tras adjunto de anexo.")
    return internado


@transaction.atomic
def revisar_declaraciones(*, internado: Internship, resultado: str, usuario, observacion: str = "") -> Internship:
    """Revisión humana de las declaraciones juradas (RN-23).

    ``resultado`` ∈ {``VALIDADAS``, ``OBSERVADAS``}. Requiere que las DJ estén
    ``COMPLETAS`` (u ``OBSERVADAS`` re-revisadas). Registra historial + auditoría.
    """
    if resultado not in ("VALIDADAS", "OBSERVADAS"):
        raise ValidationError({"resultado": "El resultado debe ser VALIDADAS u OBSERVADAS."})
    if internado.estado_declaraciones not in ("COMPLETAS", "OBSERVADAS"):
        raise ValidationError(
            {"estado_declaraciones": "Solo se pueden revisar declaraciones juradas en estado COMPLETAS u OBSERVADAS."}
        )
    _set_estado_declaraciones(internado, resultado, usuario, observacion=observacion)
    return internado


def _set_estado_declaraciones(internado: Internship, nuevo: str, usuario, observacion: str = "") -> Internship:
    anterior = internado.estado_declaraciones
    internado.estado_declaraciones = nuevo
    internado.save(update_fields=["estado_declaraciones", "actualizado_en"])
    # Historial de estado del internado (traza la transición de las DJ).
    InternshipStatusHistory.objects.create(
        interno=internado,
        estado=internado.estado_actual,
        cambiado_por=usuario or internado.creado_por,
        observacion=f"Declaraciones juradas: {anterior} → {nuevo}. {observacion}".strip(),
    )
    registrar_auditoria(
        usuario, "CAMBIO_ESTADO", internado,
        nombre_campo="estado_declaraciones", valor_anterior=anterior, valor_nuevo=nuevo,
    )
    return internado


@transaction.atomic
def actualizar_internado(*, internado: Internship, datos: dict, usuario) -> Internship:
    """Actualiza campos editables (no el tutor: usar `cambiar_tutor`; ni el estado)."""
    if "fecha_inicio" in datos or "fecha_fin" in datos:
        inicio = datos.get("fecha_inicio", internado.fecha_inicio)
        fin = datos.get("fecha_fin", internado.fecha_fin)
        if fin > _sumar_anios(inicio, 1) or fin < inicio:
            raise ValidationError({"fecha_fin": "Periodo inválido (máximo un año)."})
        internado.fecha_inicio, internado.fecha_fin = inicio, fin
    if "ipress" in datos:
        nueva_ipress = datos["ipress"]
        if nueva_ipress.ambito_geografico_sanitario_id != internado.ambito_geografico_sanitario_id:
            raise ValidationError(
                {"ipress": "La sede debe pertenecer al ámbito geográfico del internado."}
            )
        internado.ipress = nueva_ipress
    if "observaciones" in datos:
        internado.observaciones = datos["observaciones"]
    internado.save()
    registrar_auditoria(usuario, "ACTUALIZAR", internado)
    return internado


@transaction.atomic
def cambiar_estado_internado(*, internado: Internship, nuevo_estado_codigo: str, usuario, observacion: str = "") -> Internship:
    # RN-23: no se puede activar el internado sin declaraciones juradas validadas.
    if nuevo_estado_codigo == "ACTIVO" and internado.estado_declaraciones != "VALIDADAS":
        raise ValidationError(
            {"estado_declaraciones": "El internado no puede pasar a ACTIVO hasta que sus declaraciones juradas estén VALIDADAS."}
        )
    return _set_estado_internado(internado, nuevo_estado_codigo, usuario, observacion)


@transaction.atomic
def cambiar_tutor(*, internado: Internship, datos: dict, usuario) -> Internship:
    """RN-14: registra el cambio de tutor con fecha, motivo y responsable."""
    TutorHistory.objects.create(
        interno=internado,
        tutor=datos["tutor"],
        fecha_cambio=datos["fecha_cambio"],
        motivo=datos["motivo"],
        responsable=usuario,
    )
    anterior = internado.tutor_id
    internado.tutor = datos["tutor"]
    internado.save(update_fields=["tutor", "actualizado_en"])
    registrar_auditoria(
        usuario, "ACTUALIZAR", internado,
        nombre_campo="tutor", valor_anterior=anterior, valor_nuevo=internado.tutor_id,
    )
    return internado


# ---------------------------------------------------------------------------
# Rotación
# ---------------------------------------------------------------------------
@transaction.atomic
def crear_rotacion(*, internado: Internship, datos: dict, usuario) -> Rotation:
    origen = datos["ipress_origen"]
    destino = datos["ipress_destino"]
    fecha_inicio = datos["fecha_inicio"]
    fecha_fin = datos["fecha_fin"]

    # RN-8: ambas sedes en el mismo ámbito geográfico sanitario del internado.
    ambito = internado.ambito_geografico_sanitario_id
    if origen.ambito_geografico_sanitario_id != ambito or destino.ambito_geografico_sanitario_id != ambito:
        raise ValidationError("Las sedes deben pertenecer al ámbito geográfico sanitario del internado.")
    # RN-12: fechas dentro del periodo del internado.
    if fecha_inicio < internado.fecha_inicio or fecha_fin > internado.fecha_fin or fecha_fin < fecha_inicio:
        raise ValidationError("Las fechas de la rotación deben estar dentro del periodo del internado.")
    # RN-9: máximo 4 rotaciones por estudiante.
    actuales = internado.rotaciones.count()
    if actuales >= MAX_ROTACIONES:
        raise ValidationError(f"El estudiante no puede exceder {MAX_ROTACIONES} rotaciones.")

    estado_inicial = _estado_rotacion("SOLICITADA")
    rotacion = Rotation.objects.create(
        interno=internado,
        numero_rotacion=actuales + 1,
        ipress_origen=origen,
        ipress_destino=destino,
        servicio_area=datos["servicio_area"],
        estado_actual=estado_inicial,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        observaciones=datos.get("observaciones", ""),
        creado_por=usuario,
    )
    RotationStatusHistory.objects.create(
        rotacion=rotacion, estado=estado_inicial, cambiado_por=usuario
    )
    registrar_auditoria(usuario, "CREAR", rotacion)
    return rotacion


@transaction.atomic
def autorizar_rotacion(*, rotacion: Rotation, datos: dict, usuario) -> RotationAuthorization:
    """RN-10: solo una autoridad suscrita (firmante) del Convenio Específico autoriza."""
    participante = datos["participante_convenio"]
    if participante.convenio_id != rotacion.interno.convenio_id or not participante.es_firmante:
        raise ValidationError(
            {"participante_convenio": "Debe ser una autoridad firmante del Convenio Específico del internado."}
        )
    autorizacion = RotationAuthorization.objects.create(
        rotacion=rotacion,
        participante_convenio=participante,
        resultado=datos["resultado"],
        fecha_autorizacion=datos["fecha_autorizacion"],
        observaciones=datos.get("observaciones", ""),
        autorizado_por=usuario,
    )
    registrar_auditoria(usuario, "CREAR", autorizacion)
    mapa = {"APROBADO": "AUTORIZADA", "OBSERVADO": "OBSERVADA", "RECHAZADO": "RECHAZADA"}
    _set_estado_rotacion(rotacion, mapa[autorizacion.resultado], usuario)
    return autorizacion


@transaction.atomic
def iniciar_rotacion(*, rotacion: Rotation, usuario) -> Rotation:
    """RN-11: no se puede iniciar una rotación sin autorización aprobada."""
    if not rotacion.autorizaciones.filter(resultado="APROBADO").exists():
        raise ValidationError("La rotación no puede iniciar sin una autorización aprobada.")
    return _set_estado_rotacion(rotacion, "EN_CURSO", usuario)


@transaction.atomic
def cambiar_estado_rotacion(*, rotacion: Rotation, nuevo_estado_codigo: str, usuario, observacion: str = "") -> Rotation:
    return _set_estado_rotacion(rotacion, nuevo_estado_codigo, usuario, observacion)


# ---------------------------------------------------------------------------
# Prelación (RN-18)
# ---------------------------------------------------------------------------
def estudiantes_por_prelacion(queryset):
    """Ordena estudiantes por orden de mérito: `nota_promedio_ponderado` desc (RN-18).

    Los estudiantes sin nota registrada quedan al final.
    """
    from django.db.models import F

    return queryset.order_by(F("nota_promedio_ponderado").desc(nulls_last=True))


# ---------------------------------------------------------------------------
# RN-19 — Periodo académico vs. especialidad según nivel académico
# ---------------------------------------------------------------------------
def validar_regla_periodo_especialidad(*, carrera, periodo_internado, especialidad):
    """RN-19: fuente única de verdad de la regla (compartida por serializer y bulk).

    Deriva ``nivel = carrera.nivel_academico.codigo``. Si es ``PREGRADO`` exige
    ``periodo_internado`` y prohíbe ``especialidad``; para cualquier otro nivel
    exige ``especialidad`` y prohíbe ``periodo_internado``. Lanza
    ``ValidationError`` con el campo faltante/sobrante y mensaje en español.
    """
    nivel = carrera.nivel_academico.codigo
    if nivel == "PREGRADO":
        if periodo_internado is None:
            raise ValidationError(
                {"periodo_internado": "El periodo de internado es obligatorio para estudiantes de Pregrado."}
            )
        if especialidad is not None:
            raise ValidationError(
                {"especialidad": "La especialidad no aplica a estudiantes de Pregrado."}
            )
    else:
        if especialidad is None:
            raise ValidationError(
                {"especialidad": "La especialidad es obligatoria para este nivel académico."}
            )
        if periodo_internado is not None:
            raise ValidationError(
                {"periodo_internado": "El periodo de internado solo aplica al nivel Pregrado."}
            )


# ---------------------------------------------------------------------------
# Carga masiva de estudiantes (RN-16) — Excel vía openpyxl
# ---------------------------------------------------------------------------
def _celda(valor):
    """Normaliza el valor de una celda: strip de strings, None si vacío."""
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


def _parse_fecha(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    texto = str(valor).strip()
    # Soporta dd/mm/yyyy (formato de la trama) e ISO yyyy-mm-dd.
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(texto[:10], fmt).date()
        except ValueError:
            continue
    raise ValidationError("Fecha inválida (use dd/mm/yyyy o YYYY-MM-DD).")


def _resolver_universidad(valor):
    if valor is None:
        raise ValidationError("`universidad` es requerida.")
    texto = str(valor).strip()
    try:
        if texto.isdigit():
            return University.objects.get(id=int(texto))
        return University.objects.get(codigo_inei=texto)
    except University.DoesNotExist as exc:
        raise ValidationError(f"Universidad no encontrada: {texto}.") from exc


def _resolver_carrera(valor):
    if valor is None:
        raise ValidationError("`carrera_profesional` es requerida.")
    texto = str(valor).strip()
    qs = ProfessionalCareer.objects.all()
    try:
        carrera = qs.get(id=int(texto)) if texto.isdigit() else qs.get(nombre__iexact=texto)
    except ProfessionalCareer.DoesNotExist as exc:
        raise ValidationError(f"Carrera no encontrada: {texto}.") from exc
    except ProfessionalCareer.MultipleObjectsReturned as exc:
        raise ValidationError(f"Carrera ambigua (use el id): {texto}.") from exc
    return carrera


# Semestre numérico → romano, para tolerar el formato `YYYY-NN` de la trama
# (`2025-01`) además del código canónico sembrado (`2025-I`).
_SEMESTRE_ROMANO = {1: "I", 2: "II", 3: "III", 4: "IV"}


def _normalizar_codigo_periodo(texto: str) -> str:
    """Normaliza `YYYY-NN` (semestre numérico) al código canónico `YYYY-<romano>`.

    Devuelve el texto original si no coincide con ese patrón (p. ej. ya viene como
    `2025-I`), para que el resolver intente el código tal cual.
    """
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", texto)
    if not match:
        return texto
    anio, semestre = match.group(1), int(match.group(2))
    romano = _SEMESTRE_ROMANO.get(semestre)
    return f"{anio}-{romano}" if romano else texto


def _resolver_periodo_internado(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    # La columna `periodo_internado_id` de la trama admite id, el código canónico
    # (`2025-I`) o el formato numérico de semestre (`2025-01`).
    if texto.isdigit():
        try:
            return InternshipPeriod.objects.get(id=int(texto))
        except InternshipPeriod.DoesNotExist:
            pass
    codigo = _normalizar_codigo_periodo(texto)
    try:
        return InternshipPeriod.objects.get(codigo=codigo)
    except InternshipPeriod.DoesNotExist as exc:
        raise ValidationError(f"Periodo de internado no encontrado: {texto}.") from exc


def _resolver_especialidad(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    # Acepta id numérico, código o nombre (iexact) de la especialidad.
    if texto.isdigit():
        try:
            return Specialty.objects.get(id=int(texto))
        except Specialty.DoesNotExist:
            pass
    try:
        return Specialty.objects.get(codigo=texto)
    except Specialty.DoesNotExist:
        pass
    try:
        return Specialty.objects.get(nombre__iexact=texto)
    except Specialty.DoesNotExist as exc:
        raise ValidationError(f"Especialidad no encontrada: {texto}.") from exc
    except Specialty.MultipleObjectsReturned as exc:
        raise ValidationError(f"Especialidad ambigua (use el código): {texto}.") from exc


def _resolver_parentesco(valor):
    if valor is None:
        return None
    texto = str(valor).strip().upper()
    if texto.isdigit():
        try:
            return RelationshipType.objects.get(id=int(texto))
        except RelationshipType.DoesNotExist:
            pass
    try:
        return RelationshipType.objects.get(codigo=texto)
    except RelationshipType.DoesNotExist as exc:
        raise ValidationError(f"Parentesco no encontrado: {valor}. Valores válidos: PADRE, MADRE, HERMANO, CONYUGE, HIJO, ABUELO, TIO, OTRO.") from exc


def _resolver_ubigeo_por_partes(departamento, provincia, distrito):
    """Resuelve el Ubigeo desde los tres campos de la trama (departamento/provincia/distrito)."""
    valores = (departamento, provincia, distrito)
    if all(v is None for v in valores):
        return None
    if any(v is None for v in valores):
        raise ValidationError(
            "Para registrar la ubicación se requieren los tres campos: departamento, provincia y distrito."
        )
    try:
        return Ubigeo.objects.get(
            departamento__iexact=str(departamento).strip(),
            provincia__iexact=str(provincia).strip(),
            distrito__iexact=str(distrito).strip(),
        )
    except Ubigeo.DoesNotExist as exc:
        raise ValidationError(
            f"Ubigeo no encontrado: {departamento} / {provincia} / {distrito}. "
            "Verifique los nombres exactos de departamento, provincia y distrito."
        ) from exc
    except Ubigeo.MultipleObjectsReturned as exc:
        raise ValidationError(
            f"Ubigeo ambiguo: {departamento} / {provincia} / {distrito}. "
            "Ingrese el nombre de distrito más específico."
        ) from exc


def _resolver_carrera_no_pregrado(especialidad_texto: str) -> "ProfessionalCareer":
    """Resuelve la carrera profesional de un estudiante no-PREGRADO por el nombre de su especialidad.

    Para nivel no-PREGRADO (segunda especialidad, maestría, doctorado) la trama solo
    pide `especialidad`; la carrera profesional se deriva por nombre coincidente en el
    catálogo de carreras excluyendo el nivel PREGRADO.
    """
    qs = ProfessionalCareer.objects.exclude(nivel_academico__codigo="PREGRADO")
    try:
        return qs.get(nombre__iexact=especialidad_texto)
    except ProfessionalCareer.DoesNotExist as exc:
        raise ValidationError(
            f"No se encontró carrera profesional para la especialidad '{especialidad_texto}'. "
            "Verifique que exista una carrera del nivel correspondiente con ese nombre exacto."
        ) from exc
    except ProfessionalCareer.MultipleObjectsReturned as exc:
        raise ValidationError(
            f"Carrera ambigua para la especialidad '{especialidad_texto}'. "
            "Contacte al administrador para definir la carrera correcta."
        ) from exc


def _crear_estudiante_desde_fila(
    *, obtener, usuario, universidad, periodo_internado, ct_uni, es_admin, es_pregrado_trama: bool
) -> Student:
    tipo_doc_codigo = obtener("tipo_documento")
    numero_documento = obtener("numero_documento")
    nombres = obtener("nombres")
    apellido_paterno = obtener("apellido_paterno")
    if not (tipo_doc_codigo and numero_documento and nombres and apellido_paterno):
        raise ValidationError(
            "Campos requeridos: tipo_documento, numero_documento, nombres, apellido_paterno."
        )

    try:
        tipo_doc = IdentityDocumentType.objects.get(codigo=str(tipo_doc_codigo).strip().upper())
    except IdentityDocumentType.DoesNotExist as exc:
        raise ValidationError(f"Tipo de documento inválido: {tipo_doc_codigo}.") from exc

    numero_documento = str(numero_documento).strip()
    if Student.objects.filter(tipo_documento_identidad=tipo_doc, numero_documento=numero_documento).exists():
        raise ValidationError(f"Ya existe un estudiante con {tipo_doc.codigo} {numero_documento}.")

    if not es_admin and not usuario_pertenece_a_entidad(usuario, ct_uni, universidad.id):
        raise ValidationError(
            f"La universidad {universidad.codigo_inei or universidad.id} está fuera de tu ámbito."
        )

    # RN-19: la trama tiene SOLO carrera_profesional (PREGRADO) o SOLO especialidad (no-PREGRADO).
    if es_pregrado_trama:
        carrera = _resolver_carrera(obtener("carrera_profesional"))
        especialidad = None
        periodo_internado_fila = periodo_internado
    else:
        especialidad_texto = obtener("especialidad")
        if not especialidad_texto:
            raise ValidationError("`especialidad` es requerida para estudiantes de nivel no PREGRADO.")
        especialidad_texto = str(especialidad_texto).strip()
        especialidad = _resolver_especialidad(especialidad_texto)
        carrera = _resolver_carrera_no_pregrado(especialidad_texto)
        periodo_internado_fila = None

    # RN-19: coherencia entre nivel académico, periodo de internado y especialidad.
    validar_regla_periodo_especialidad(
        carrera=carrera, periodo_internado=periodo_internado_fila, especialidad=especialidad
    )

    # Ubigeo: se resuelve desde los tres campos separados departamento / provincia / distrito.
    ubigeo = _resolver_ubigeo_por_partes(
        obtener("departamento"), obtener("provincia"), obtener("distrito")
    )

    sexo_raw = obtener("sexo")
    sexo = str(sexo_raw).strip().upper() if sexo_raw is not None else None
    if sexo is not None and sexo not in ("M", "F"):
        raise ValidationError("`sexo` debe ser M o F.")

    nota = obtener("nota_promedio_ponderado")
    if nota is not None:
        try:
            nota = decimal.Decimal(str(nota).replace(",", "."))
        except (decimal.InvalidOperation, ValueError) as exc:
            raise ValidationError("`nota_promedio_ponderado` inválida.") from exc

    parentesco = _resolver_parentesco(obtener("contacto_emergencia_parentesco"))

    estudiante = Student.objects.create(
        tipo_documento_identidad=tipo_doc,
        numero_documento=numero_documento,
        nombres=str(nombres).strip(),
        apellido_paterno=str(apellido_paterno).strip(),
        apellido_materno=(str(obtener("apellido_materno")).strip() if obtener("apellido_materno") else ""),
        fecha_nacimiento=_parse_fecha(obtener("fecha_nacimiento")),
        sexo=sexo or "",
        correo=(str(obtener("correo")).strip() if obtener("correo") else ""),
        telefono=(str(obtener("telefono")).strip() if obtener("telefono") else ""),
        direccion=(str(obtener("direccion")).strip() if obtener("direccion") else ""),
        ubigeo=ubigeo,
        universidad=universidad,
        carrera_profesional=carrera,
        periodo_internado=periodo_internado_fila,
        especialidad=especialidad,
        nota_promedio_ponderado=nota,
        contacto_emergencia_nombre=(str(obtener("contacto_emergencia_nombre")).strip() if obtener("contacto_emergencia_nombre") else ""),
        contacto_emergencia_telefono=(str(obtener("contacto_emergencia_telefono")).strip() if obtener("contacto_emergencia_telefono") else ""),
        contacto_emergencia_parentesco=parentesco,
        creado_por=usuario,
    )
    registrar_auditoria(usuario, "CREAR", estudiante)
    return estudiante


@transaction.atomic
def registrar_estudiantes_masivo(*, archivo, usuario, universidad, periodo_internado=None) -> dict:
    """Carga masiva de estudiantes desde un Excel (.xlsx) — RN-16.

    `universidad` y `periodo_internado` son parámetros fijos tomados de los filtros
    de la UI (no vienen en el Excel). Para carreras no-PREGRADO `periodo_internado`
    se ignora por fila y se espera la columna `especialidad` en el Excel.
    Valida por fila; las filas inválidas se reportan sin abortar el lote.
    Devuelve un resumen: ``{creados, omitidos, errores:[{fila, motivo}]}``.
    """
    try:
        wb = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    except Exception as exc:  # archivo corrupto o no .xlsx
        raise ValidationError("No se pudo leer el archivo Excel (.xlsx).") from exc

    ws = wb.active
    filas = ws.iter_rows(values_only=True)
    try:
        cabecera = next(filas)
    except StopIteration as exc:
        raise ValidationError("El archivo está vacío.") from exc

    # Normaliza los encabezados y aplica los alias de la trama oficial (`_id`) a la
    # clave canónica interna; así la carga acepta tanto la estructura nueva como la
    # histórica sin tocar los resolvers ni el mapeo de columnas.
    # Normaliza encabezados: extrae la primera línea (las celdas multi-línea de la trama oficial
    # usan \n para añadir instrucciones bajo el nombre de columna, p. ej. "tipo_documento\n(DNI…)").
    def _norm_header(c) -> str:
        if c is None:
            return ""
        return str(c).strip().split("\n")[0].strip().lower()

    encabezados = [
        CARGA_ALIAS_COLUMNAS.get(h, h)
        for h in (_norm_header(c) for c in cabecera)
    ]
    faltantes = CARGA_COLUMNAS_REQUERIDAS - set(encabezados)
    if faltantes:
        raise ValidationError(f"Faltan columnas requeridas: {', '.join(sorted(faltantes))}.")

    # Detecta el modo por la presencia de la columna de nivel académico.
    tiene_carrera = "carrera_profesional" in set(encabezados)
    tiene_especialidad = "especialidad" in set(encabezados)
    if not tiene_carrera and not tiene_especialidad:
        raise ValidationError(
            "El archivo debe incluir la columna 'carrera_profesional' (trama PREGRADO) "
            "o 'especialidad' (trama no-PREGRADO)."
        )
    es_pregrado_trama = tiene_carrera

    indice = {h: i for i, h in enumerate(encabezados)}

    ct_uni = ContentType.objects.get_for_model(University).id
    es_admin = usuario.is_superuser or usuario.groups.filter(name="Administrador RENADS").exists()

    creados = 0
    errores: list[dict] = []
    for numero_fila, fila in enumerate(filas, start=2):
        if fila is None or all(_celda(v) is None for v in fila):
            continue  # fila vacía

        def obtener(col, _fila=fila):
            i = indice.get(col)
            if i is None or i >= len(_fila):
                return None
            return _celda(_fila[i])

        try:
            with transaction.atomic():  # savepoint por fila
                _crear_estudiante_desde_fila(
                    obtener=obtener, usuario=usuario,
                    universidad=universidad, periodo_internado=periodo_internado,
                    ct_uni=ct_uni, es_admin=es_admin,
                    es_pregrado_trama=es_pregrado_trama,
                )
            creados += 1
        except ValidationError as exc:
            errores.append({"fila": numero_fila, "motivo": _mensaje_error(exc)})
        except Exception as exc:  # noqa: BLE001 — reportar sin abortar el lote
            errores.append({"fila": numero_fila, "motivo": str(exc)})

    wb.close()
    return {"creados": creados, "omitidos": len(errores), "errores": errores}


def _mensaje_error(exc: ValidationError) -> str:
    detalle = exc.detail
    if isinstance(detalle, dict):
        return "; ".join(f"{k}: {' '.join(map(str, v)) if isinstance(v, list) else v}" for k, v in detalle.items())
    if isinstance(detalle, list):
        return " ".join(map(str, detalle))
    return str(detalle)


# ---------------------------------------------------------------------------
# Generador de trama Excel para carga masiva de estudiantes
# ---------------------------------------------------------------------------
def generar_trama_excel(*, es_pregrado: bool = True) -> bytes:
    """Genera la plantilla Excel de carga masiva de estudiantes según nivel académico.

    - ``es_pregrado=True``  → columna ``carrera_profesional`` (NO ``especialidad``)
    - ``es_pregrado=False`` → columna ``especialidad`` (NO ``carrera_profesional``)

    El ubigeo se divide en tres columnas: ``departamento``, ``provincia``, ``distrito``.
    Retorna el contenido del .xlsx como bytes.
    """
    import io

    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    # ---------- paleta ----------
    fill_req = PatternFill("solid", fgColor="1F3864")   # azul oscuro — requerido
    fill_opt = PatternFill("solid", fgColor="2E75B6")   # azul medio — opcional
    fill_niv = PatternFill("solid", fgColor="9DC3E6")   # azul claro — nivel (requerido)
    font_blanco = Font(color="FFFFFF", bold=True, size=10)
    font_oscuro = Font(color="1F3864", bold=True, size=10)
    font_celda = Font(size=10)
    borde = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"),  bottom=Side(style="thin"),
    )
    alineacion = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # ---------- definición de columnas ----------
    columnas = [
        # (clave_interna, etiqueta_encabezado, tipo)
        ("tipo_documento",           "tipo_documento\n(DNI / CE / PASAPORTE)",          "req"),
        ("numero_documento",         "numero_documento",                                "req"),
        ("apellido_paterno",         "apellido_paterno",                                "req"),
        ("apellido_materno",         "apellido_materno",                                "opt"),
        ("nombres",                  "nombres",                                         "req"),
        ("fecha_nacimiento",         "fecha_nacimiento\n(dd/mm/yyyy)",                  "opt"),
        ("sexo",                     "sexo\n(M / F)",                                   "opt"),
        ("correo",                   "correo",                                          "opt"),
        ("telefono",                 "telefono",                                        "opt"),
        ("direccion",                "direccion",                                       "opt"),
        ("departamento",             "departamento",                                    "opt"),
        ("provincia",                "provincia",                                       "opt"),
        ("distrito",                 "distrito",                                        "opt"),
    ]
    if es_pregrado:
        columnas.append(("carrera_profesional", "carrera_profesional\n(nombre exacto)", "niv"))
    else:
        columnas.append(("especialidad", "especialidad\n(nombre exacto)", "niv"))
    columnas += [
        ("nota_promedio_ponderado",       "nota_promedio_ponderado\n(0–20, hasta 4 decimales)", "opt"),
        ("contacto_emergencia_nombre",    "contacto_emergencia_nombre",                         "opt"),
        ("contacto_emergencia_telefono",  "contacto_emergencia_telefono",                       "opt"),
        ("contacto_emergencia_parentesco","contacto_emergencia_parentesco\n(PADRE/MADRE/HERMANO/CONYUGE/HIJO/ABUELO/TIO/OTRO)", "opt"),
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Estudiantes"
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 42

    for col_idx, (clave, etiqueta, tipo) in enumerate(columnas, start=1):
        celda = ws.cell(row=1, column=col_idx, value=etiqueta)
        celda.border = borde
        celda.alignment = alineacion
        if tipo == "req":
            celda.fill = fill_req
            celda.font = font_blanco
        elif tipo == "opt":
            celda.fill = fill_opt
            celda.font = font_blanco
        else:  # "niv"
            celda.fill = fill_niv
            celda.font = font_oscuro
        ws.column_dimensions[get_column_letter(col_idx)].width = 22

    # Leyenda en hoja adicional
    ws2 = wb.create_sheet("Instrucciones")
    nivel_txt = "PREGRADO" if es_pregrado else "no-PREGRADO (segunda especialidad / maestría / doctorado)"
    leyenda = [
        ("INSTRUCCIONES DE CARGA MASIVA DE ESTUDIANTES", None),
        ("", None),
        (f"Esta trama corresponde al nivel académico: {nivel_txt}", None),
        ("", None),
        ("CONVENCIÓN DE COLORES:", None),
        ("Azul oscuro", "Campo REQUERIDO — la fila se rechaza si falta."),
        ("Azul medio",  "Campo OPCIONAL — puede dejarse en blanco."),
        ("Azul claro",  f"Campo de NIVEL — requerido según el nivel seleccionado ({nivel_txt})."),
        ("", None),
        ("NOTAS:", None),
        ("fecha_nacimiento",             "Formato dd/mm/yyyy  (ej. 15/04/1998)"),
        ("departamento / provincia / distrito", "Nombre completo tal como aparece en el padrón de ubigeos del RENIEC."),
        ("tipo_documento",               "DNI, CE o PASAPORTE"),
        ("sexo",                         "M (masculino) o F (femenino)"),
        ("nota_promedio_ponderado",      "Escala 0 a 20 con hasta 4 decimales"),
    ]
    ws2.column_dimensions["A"].width = 40
    ws2.column_dimensions["B"].width = 60
    for fila_idx, (col_a, col_b) in enumerate(leyenda, start=1):
        ws2.cell(row=fila_idx, column=1, value=col_a)
        if col_b:
            ws2.cell(row=fila_idx, column=2, value=col_b)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
