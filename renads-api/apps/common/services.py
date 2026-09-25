"""Services transversales: auditoría en bitácora, gestión documental y 2FA."""

import hashlib
import hmac
import secrets
import string
from datetime import timedelta

import jwt
import pyotp
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from apps.common.models import UserProfile, UserSecurity
from apps.convenios.models import AuditLog, Document


def registrar_auditoria(
    usuario,
    accion: str,
    objeto,
    *,
    nombre_campo: str = "",
    valor_anterior="",
    valor_nuevo="",
    direccion_ip: str | None = None,
) -> AuditLog:
    """Registra una operación crítica en `bitacora_auditoria` (RNF-AUD-01/02)."""
    usuario_valido = usuario if (usuario and getattr(usuario, "is_authenticated", False)) else None
    return AuditLog.objects.create(
        usuario=usuario_valido,
        accion=accion,
        tipo_contenido=ContentType.objects.get_for_model(type(objeto)),
        id_objeto=objeto.pk,
        nombre_campo=nombre_campo,
        valor_anterior="" if valor_anterior is None else str(valor_anterior),
        valor_nuevo="" if valor_nuevo is None else str(valor_nuevo),
        direccion_ip=direccion_ip or "",
    )


@transaction.atomic
def adjuntar_documento(
    objeto,
    *,
    referencia_externa,
    usuario,
    documento_anexo,
) -> Document:
    """Adjunta un documento versionado a `objeto` (relación genérica, RNF-DOC-04).

    Versionado: si ya existe un documento `ACTIVO` para el mismo objeto y
    `documento_anexo`, el nuevo documento toma la versión siguiente, enlaza al
    anterior en `version_anterior` y marca al anterior como `REEMPLAZADO`. El
    **único discriminador** de la cadena de versiones es `documento_anexo`
    (obligatorio): cada anexo/tipo mantiene su propia cadena de versiones
    independiente. El nombre de archivo se usa solo como ruta de storage en la
    vista/mixin que sube el binario; no se persiste en `Document`.

    Todo dentro de `transaction.atomic()` y con registro de auditoría. Devuelve la
    nueva instancia `Document` creada.
    """
    tipo_contenido = ContentType.objects.get_for_model(type(objeto))

    # Documento activo previo del mismo objeto y anexo. A lo sumo uno; si hubiera
    # varios, se toma el de mayor versión. select_for_update evita carreras.
    anterior = (
        Document.objects.select_for_update()
        .filter(
            tipo_contenido=tipo_contenido,
            id_objeto=objeto.pk,
            estado="ACTIVO",
            documento_anexo=documento_anexo,
        )
        .order_by("-version")
        .first()
    )

    documento = Document.objects.create(
        tipo_contenido=tipo_contenido,
        id_objeto=objeto.pk,
        referencia_externa=referencia_externa,
        version=(anterior.version + 1) if anterior else 1,
        estado="ACTIVO",
        version_anterior=anterior,
        documento_anexo=documento_anexo,
        cargado_por=usuario,
    )

    registrar_auditoria(usuario, "CREAR", documento)

    if anterior is not None:
        anterior.estado = "REEMPLAZADO"
        anterior.save(update_fields=["estado"])
        registrar_auditoria(
            usuario,
            "CAMBIO_ESTADO",
            anterior,
            nombre_campo="estado",
            valor_anterior="ACTIVO",
            valor_nuevo="REEMPLAZADO",
        )

    return documento


# ---------------------------------------------------------------------------
# Autenticación de dos factores (2FA)
# ---------------------------------------------------------------------------


def generar_session_token(user: User) -> str:
    """Genera un JWT de corta duración (5 min, scope ``2fa_pending``) para el
    flujo de login diferido cuando el usuario tiene 2FA activo (T-05).

    Firmado con ``settings.SECRET_KEY`` y algoritmo HS256. No escribe en BD
    ni envía correo. El token se devuelve al cliente y debe intercambiarse en
    ``POST /api/v1/auth/2fa/verify/``.
    """
    import datetime as _dt

    payload = {
        "sub": str(user.pk),
        "scope": "2fa_pending",
        "exp": _dt.datetime.utcnow() + _dt.timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def validar_session_token(token: str) -> User:
    """Decodifica y valida el ``session_token`` generado por ``generar_session_token``
    (T-06). Devuelve el ``User`` activo si la validación es exitosa; de lo contrario
    lanza ``AuthenticationFailed`` con el ``code`` semántico correspondiente.

    Condiciones de error:
    - Token malformado o firma inválida → ``SESSION_INVALIDA``.
    - Token expirado → ``SESSION_EXPIRADA``.
    - Scope distinto de ``2fa_pending`` → ``SESSION_INVALIDA``.
    - Usuario no encontrado o inactivo → ``SESSION_INVALIDA``.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed(
            "La sesión de verificación ha expirado. Inicia sesión nuevamente.",
            code="SESSION_EXPIRADA",
        )
    except jwt.PyJWTError:
        raise AuthenticationFailed(
            "El token de sesión no es válido.",
            code="SESSION_INVALIDA",
        )

    if payload.get("scope") != "2fa_pending":
        raise AuthenticationFailed(
            "El token de sesión no es válido.",
            code="SESSION_INVALIDA",
        )

    user_id = payload.get("sub")
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except (User.DoesNotExist, ValueError, TypeError):
        raise AuthenticationFailed(
            "El token de sesión no es válido.",
            code="SESSION_INVALIDA",
        )

    return user


def generar_otp_email(user_security: UserSecurity) -> None:
    """Genera un OTP de 6 dígitos, lo hashea, lo persiste y envía el correo
    al usuario (T-07). El código en texto claro nunca se almacena en BD.

    El envío del correo es best-effort (``fail_silently=True``): un fallo SMTP
    no bloquea la respuesta al cliente. La función no registra auditoría (el OTP
    es transitorio; las acciones auditables son activar/desactivar 2FA).
    """
    code = str(secrets.randbelow(10 ** 6)).zfill(6)
    code_hash = hashlib.sha256(code.encode()).hexdigest()

    user_security.otp_code = code_hash
    user_security.otp_expires_at = timezone.now() + timedelta(minutes=settings.OTP_TTL_MINUTES)
    user_security.save(update_fields=["otp_code", "otp_expires_at", "actualizado_en"])

    mensaje = (
        f"Tu código de verificación RENADS es: {code}\n\n"
        f"Este código es válido por {settings.OTP_TTL_MINUTES} minutos.\n"
        "No compartas este código con nadie."
    )
    send_mail(
        subject="Código de verificación RENADS",
        message=mensaje,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_security.usuario.email],
        fail_silently=True,
    )


def validar_otp_email(user_security: UserSecurity, code: str) -> bool:
    """Verifica el código OTP de email comparando hashes con resistencia a timing
    attacks (T-08). Limpia los campos OTP en caso de éxito.

    Retorna ``True`` si el código es válido y no ha expirado; ``False`` en caso
    contrario (expirado o hash incorrecto). No lanza excepciones.
    """
    if user_security.otp_expires_at is None:
        return False

    if timezone.now() > user_security.otp_expires_at:
        return False

    code_hash = hashlib.sha256(code.encode()).hexdigest()
    if not hmac.compare_digest(code_hash, user_security.otp_code):
        return False

    # Código válido: limpiar campos OTP.
    user_security.otp_code = ""
    user_security.otp_expires_at = None
    user_security.save(update_fields=["otp_code", "otp_expires_at", "actualizado_en"])
    return True


def puede_reenviar_otp(user_security: UserSecurity) -> bool:
    """Rate-limit de reenvío de OTP: permite un nuevo envío solo si han pasado
    más de 1 minuto desde el último envío (T-09). Sin efectos secundarios.

    Lógica:
    - Sin OTP en curso (``otp_expires_at`` nulo) → ``True``.
    - Si el tiempo restante del OTP es menor que ``(OTP_TTL_MINUTES - 1) * 60``
      segundos, ha pasado más de 1 minuto desde el envío → ``True``.
    - En otro caso → ``False``.
    """
    if user_security.otp_expires_at is None:
        return True

    tiempo_restante = (user_security.otp_expires_at - timezone.now()).total_seconds()
    return tiempo_restante < (settings.OTP_TTL_MINUTES - 1) * 60


@transaction.atomic
def activar_2fa_totp(user_security: UserSecurity, otp_code: str, usuario) -> None:
    """Activa el segundo factor TOTP para el usuario tras verificar el código con el
    secreto ya almacenado en ``user_security.totp_secret`` (T-10).

    Lanza ``ValidationError`` si el secreto no existe o si el código es inválido.
    La operación es atómica: un error en la auditoría revierte la actualización.
    """
    if not user_security.totp_secret:
        raise ValidationError("Debes iniciar la configuración TOTP antes de confirmarla.")

    totp = pyotp.TOTP(user_security.totp_secret)
    if not totp.verify(otp_code):
        raise ValidationError("El código TOTP no es válido.")

    user_security.two_factor_enabled = True
    user_security.two_factor_method = "TOTP"
    user_security.save(update_fields=["two_factor_enabled", "two_factor_method", "actualizado_en"])

    registrar_auditoria(usuario, "ACTIVAR_2FA_TOTP", user_security)


@transaction.atomic
def activar_2fa_email(user_security: UserSecurity, password: str, usuario) -> None:
    """Activa el segundo factor EMAIL para el usuario tras verificar la contraseña
    actual (T-11). Limpia el secreto TOTP previo si existía.

    Lanza ``ValidationError`` si la contraseña no es correcta.
    """
    if not user_security.usuario.check_password(password):
        raise ValidationError("La contraseña no es correcta.")

    user_security.two_factor_enabled = True
    user_security.two_factor_method = "EMAIL"
    user_security.totp_secret = ""
    user_security.save(
        update_fields=["two_factor_enabled", "two_factor_method", "totp_secret", "actualizado_en"]
    )

    registrar_auditoria(usuario, "ACTIVAR_2FA_EMAIL", user_security)


@transaction.atomic
def desactivar_2fa(
    user_security: UserSecurity, password: str, otp_code: str, usuario
) -> None:
    """Desactiva el segundo factor del usuario exigiendo contraseña + OTP vigente
    (doble verificación, RN-2FA-07, T-12). Limpia todos los campos 2FA.

    Lanza ``ValidationError`` si la contraseña es incorrecta o el OTP no es válido.
    """
    if not user_security.usuario.check_password(password):
        raise ValidationError("La contraseña no es correcta.")

    if user_security.two_factor_method == "TOTP":
        totp = pyotp.TOTP(user_security.totp_secret)
        if not totp.verify(otp_code):
            raise ValidationError("El código TOTP no es válido.")
    else:
        # Método EMAIL: validar_otp_email ya limpia los campos en caso de éxito;
        # dentro del atomic se incluye, si falla se hace rollback.
        if not validar_otp_email(user_security, otp_code):
            raise ValidationError("El código OTP no es válido o ha expirado.")

    # Limpiar todos los campos 2FA.
    user_security.two_factor_enabled = False
    user_security.two_factor_method = ""
    user_security.totp_secret = ""
    user_security.otp_code = ""
    user_security.otp_expires_at = None
    user_security.save(
        update_fields=[
            "two_factor_enabled",
            "two_factor_method",
            "totp_secret",
            "otp_code",
            "otp_expires_at",
            "actualizado_en",
        ]
    )

    registrar_auditoria(usuario, "DESACTIVAR_2FA", user_security)


# ---------------------------------------------------------------------------
# Gestión de contraseñas y perfil de usuario
# ---------------------------------------------------------------------------


def generar_password_segura() -> str:
    """Genera una contraseña segura de exactamente 12 caracteres (R-3).

    Composición garantizada: 1 minúscula, 1 mayúscula, 1 dígito, 2 especiales
    del conjunto ``!@#$%^&*``, más 7 caracteres adicionales del pool completo.
    Usa exclusivamente el módulo ``secrets`` (nunca ``random``).
    """
    pool_minusculas = string.ascii_lowercase
    pool_mayusculas = string.ascii_uppercase
    pool_digitos = string.digits
    pool_especiales = "!@#$%^&*"
    pool_completo = pool_minusculas + pool_mayusculas + pool_digitos + pool_especiales

    # Obligatorios: 1 de cada clase + 2 especiales = 5 caracteres.
    caracteres = [
        secrets.choice(pool_minusculas),
        secrets.choice(pool_mayusculas),
        secrets.choice(pool_digitos),
        secrets.choice(pool_especiales),
        secrets.choice(pool_especiales),
    ]
    # Relleno: 7 caracteres adicionales del pool completo.
    caracteres += [secrets.choice(pool_completo) for _ in range(7)]

    # Mezclar usando SystemRandom (respaldado por secrets) para evitar orden predecible.
    secrets.SystemRandom().shuffle(caracteres)
    return "".join(caracteres)


@transaction.atomic
def crear_usuario_con_perfil(
    validated_data: dict,
    groups: list,
    profile_data: dict,
) -> tuple:
    """Crea un ``User``, su ``UserSecurity`` y su ``UserProfile`` en una transacción (R-5).

    **Regla username = numero_documento (no-superusuario):** para los usuarios que
    **no** son superusuario, el ``username`` se deriva del ``numero_documento`` del
    perfil (que provee el serializer en ``profile_data``); cualquier ``username``
    enviado por el cliente se **ignora** (el serializer lo marca read-only). El
    ``numero_documento`` es único, por lo que el ``username`` resultante también lo es.

    **Exención total del superusuario:** si ``validated_data`` marca ``is_superuser``,
    se respeta el ``username`` explícito recibido, **no** se deriva del documento y
    **no** se crea ``UserProfile`` a menos que llegue ``profile_data``. Así el
    superusuario puede crearse sin apellidos/nombre ni perfil completo (sin violar el
    ``NOT NULL`` del perfil).

    Los apellidos van a ``user.last_name`` (combinado ``"Paterno Materno"``) y el
    nombre a ``user.first_name``; el serializer los deja en ``validated_data``. El
    perfil ya **no** almacena apellidos.

    Si ``validated_data`` no contiene ``password``, la genera automáticamente con
    ``generar_password_segura()``. Retorna ``(user, password_plain)`` donde
    ``password_plain`` es la contraseña en texto claro (para devolverla al admin
    en la respuesta del POST; nunca se persiste en BD).

    :param validated_data: campos del modelo ``User`` (sin ``password``/``groups``),
        incluidos ``first_name``/``last_name``.
    :param groups: lista de instancias ``Group`` a asignar al usuario.
    :param profile_data: campos del modelo ``UserProfile`` (todos obligatorios salvo
        ``tiene_ficha_usuario``, que tiene default ``False``) para no-superusuario;
        puede venir vacío para el superusuario (no se crea perfil). Si faltara algún
        campo obligatorio, la constraint ``NOT NULL`` dispararía ``IntegrityError``
        dentro de este ``transaction.atomic`` → rollback completo.
    """
    password_plain = validated_data.pop("password", None) or generar_password_segura()

    es_superusuario = bool(validated_data.get("is_superuser"))
    if not es_superusuario:
        # username = numero_documento (ignora cualquier username del cliente).
        numero_documento = (profile_data.get("numero_documento") or "").strip()
        validated_data["username"] = numero_documento

    user = User(**validated_data)
    user.set_password(password_plain)
    user.save()
    user.groups.set(groups)

    # Política (2026-09-25): la contraseña autogenerada en el alta por administrador es
    # **definitiva** — NO se fuerza el cambio en el primer login (`debe_cambiar_password=False`).
    # El usuario inicia sesión con la contraseña que el admin ve/copia al crear; el cambio solo
    # ocurre por la acción «Restablecer contraseña» (`set-password`) o por decisión del propio
    # usuario. (El onboarding del interno usa otro flujo y conserva su contraseña temporal.)
    user_security, _ = UserSecurity.objects.get_or_create(usuario=user)
    user_security.debe_cambiar_password = False
    user_security.password_changed_at = timezone.now()
    user_security.save(update_fields=["debe_cambiar_password", "password_changed_at", "actualizado_en"])

    # Superusuario exento: solo se crea perfil si el serializer envió datos de perfil.
    if profile_data:
        UserProfile.objects.create(usuario=user, **profile_data)

    return user, password_plain


def actualizar_perfil_usuario(user: User, profile_data: dict):
    """Actualiza el ``UserProfile`` del usuario con los datos proporcionados (R-8/R-9).

    Con el perfil endurecido (todos los campos ``NOT NULL``), un ``get_or_create``
    que cree un perfil vacío violaría la constraint. Por eso:

    - Si el usuario **ya tiene** perfil, aplica el update parcial sobre los campos
      recibidos (``update_fields``), sin exigir el conjunto completo.
    - Si el usuario **no tiene** perfil, este service exige que ``profile_data`` traiga
      los 5 campos obligatorios del perfil para poder crearlo sin violar ``NOT NULL``;
      en caso contrario lanza ``ValidationError`` (nunca se crea un perfil vacío). El
      alta normal del perfil ocurre en ``crear_usuario_con_perfil``.

    Los apellidos/nombre **no** se editan aquí: viven en ``auth_user``
    (``last_name``/``first_name``) y se aplican en el ``update()`` del
    ``UserUpdateSerializer`` sobre la instancia ``User``, no sobre el perfil.

    Permite actualizar ``tiene_ficha_usuario`` vía ``profile_data``. No usa
    ``transaction.atomic`` porque la transacción la gestiona el caller
    (``UserViewSet.perform_update``).

    :returns: la instancia ``UserProfile`` actualizada (o ``None`` si no había perfil
        y no se envió ningún dato).
    """
    profile = UserProfile.objects.filter(usuario=user).first()

    if profile is None:
        if not profile_data:
            # No hay perfil y no hay datos → no se crea nada (evita perfil vacío NOT NULL).
            return None
        campos_obligatorios = {
            "tipo_documento", "numero_documento",
            "telefono", "unidad_organica", "cargo",
        }
        faltantes = campos_obligatorios - set(profile_data.keys())
        if faltantes:
            raise ValidationError(
                "No se puede crear el perfil de usuario: faltan campos obligatorios "
                f"({', '.join(sorted(faltantes))})."
            )
        return UserProfile.objects.create(usuario=user, **profile_data)

    if not profile_data:
        return profile

    for campo, valor in profile_data.items():
        setattr(profile, campo, valor)
    profile.save(update_fields=list(profile_data.keys()))
    return profile


def solicitar_reset_password(username: str) -> None:
    """Inicia el flujo de recuperación de contraseña enviando un OTP por correo (R-6).

    Silencia los errores de usuario inexistente o sin correo para no revelar
    si el usuario existe (prevención de enumeración de usuarios). Lanza
    ``ValidationError`` si el rate-limit de reenvío no se ha cumplido aún.
    """
    user = User.objects.filter(username=username, is_active=True).first()
    if user is None:
        return
    if not user.email:
        return

    user_security, _ = UserSecurity.objects.get_or_create(usuario=user)
    if not puede_reenviar_otp(user_security):
        raise ValidationError(
            "Debes esperar al menos 1 minuto antes de solicitar un nuevo código."
        )

    generar_otp_email(user_security)


@transaction.atomic
def confirmar_reset_password(username: str, otp_code: str, password_nueva: str) -> None:
    """Confirma el restablecimiento de contraseña validando el OTP y la fortaleza de la nueva
    contraseña (R-6). Operación completamente atómica.

    Lanza ``ValidationError`` si el usuario no existe, el OTP es inválido o
    la contraseña no cumple los requisitos de seguridad de Django.
    """
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError as DjangoValidationError
    from rest_framework.exceptions import ValidationError as DRFValidationError

    user = User.objects.filter(username=username, is_active=True).first()
    if user is None:
        raise ValidationError("Credenciales no válidas.")

    try:
        user_security = UserSecurity.objects.get(usuario=user)
    except UserSecurity.DoesNotExist:
        raise ValidationError("Credenciales no válidas.")

    if not validar_otp_email(user_security, otp_code):
        raise ValidationError("El código OTP no es válido o ha expirado.")

    try:
        validate_password(password_nueva, user=user)
    except DjangoValidationError as exc:
        raise DRFValidationError(list(exc.messages)) from exc

    user.set_password(password_nueva)
    user.save(update_fields=["password"])

    user_security.password_changed_at = timezone.now()
    user_security.debe_cambiar_password = False
    user_security.save(update_fields=["password_changed_at", "debe_cambiar_password", "actualizado_en"])

    registrar_auditoria(user, "ACTUALIZAR", user, nombre_campo="password")
