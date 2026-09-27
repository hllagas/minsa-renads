"""Vistas transversales: login JWT con claims, datos del usuario actual,
administración de usuarios, grupos (roles) y permisos (solo superadministrador)
y autenticación de dos factores (2FA)."""

import pyotp
from datetime import timedelta

from django.contrib.auth import update_last_login
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.models import UserSecurity, debe_cambiar_password as _debe_cambiar_password
from apps.common.permissions import IsSuperUser
from apps.common.serializers import (
    ASSIGNABLE_PROFILE_MODELS,
    AssignableEntityTypeSerializer,
    ChangeOwnPasswordSerializer,
    ContentTypeSerializer,
    CustomTokenObtainPairSerializer,
    GroupSerializer,
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PermissionSerializer,
    SetPasswordSerializer,
    TotpSetupConfirmSerializer,
    TwoFactorDisableSerializer,
    TwoFactorResendSerializer,
    TwoFactorSetupEmailSerializer,
    TwoFactorVerifySerializer,
    UserCreateSerializer,
    UserEntityProfileWriteReadSerializer,
    UserEntityProfileWriteSerializer,
    UserReadSerializer,
    UserUpdateSerializer,
    _nombre_usuario,
)
from apps.common.services import (
    activar_2fa_email,
    activar_2fa_totp,
    confirmar_reset_password,
    desactivar_2fa,
    generar_otp_email,
    generar_session_token,
    puede_reenviar_otp,
    registrar_auditoria,
    solicitar_reset_password,
    validar_otp_email,
    validar_session_token,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Obtiene el par de tokens JWT incluyendo roles y nombre en los claims.

    Si el usuario tiene 2FA activo, en lugar de devolver el JWT completo devuelve
    un ``session_token`` de corta duración (5 min, scope ``2fa_pending``) para
    que el cliente lo intercambie por el JWT real en ``POST /api/v1/auth/2fa/verify/``
    tras ingresar el código OTP.
    """

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        from django.conf import settings as _settings

        # 1. Validar credenciales usando el flujo normal de SimpleJWT.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. Identificar el usuario autenticado.
        user = serializer.user

        # 3. Obtener o crear el registro de seguridad del usuario.
        user_security, _ = UserSecurity.objects.get_or_create(usuario=user)

        # 3b. Gate de caducidad de contraseña (R-4).
        # Superusuario exento; para el resto, si no ha cambiado nunca o han pasado
        # más de PASSWORD_EXPIRY_DAYS días desde el último cambio → bloquear login.
        if not user.is_superuser:
            password_expirada = (
                user_security.password_changed_at is None
                or (
                    timezone.now() - user_security.password_changed_at
                    > timedelta(days=_settings.PASSWORD_EXPIRY_DAYS)
                )
            )
            if password_expirada:
                from rest_framework.status import HTTP_401_UNAUTHORIZED
                return Response(
                    {
                        "detail": (
                            "Tu contraseña ha expirado. "
                            "Usa la opción 'Olvidé mi contraseña' para obtener una nueva."
                        ),
                        "code": "PASSWORD_EXPIRADO",
                    },
                    status=HTTP_401_UNAUTHORIZED,
                )

        # 4. 2FA por email obligatorio para todos (FORCE_EMAIL_2FA=True).
        if getattr(_settings, "FORCE_EMAIL_2FA", False):
            if not user.email:
                return Response(
                    {"detail": "Tu cuenta no tiene correo registrado. Contacta al administrador."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                generar_otp_email(user_security)
            except Exception:
                pass
            return Response(
                {
                    "requires_2fa": True,
                    "session_token": generar_session_token(user),
                    "method": "EMAIL",
                },
                status=status.HTTP_200_OK,
            )

        # 5. Sin 2FA activo → flujo habitual (devolver JWT completo sin modificar).
        if not user_security.two_factor_enabled:
            update_last_login(None, user)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)

        # 6. Con 2FA opt-in activo → generar session_token diferido.
        if user_security.two_factor_method == "EMAIL":
            try:
                generar_otp_email(user_security)
            except Exception:
                pass

        session_token = generar_session_token(user)
        return Response(
            {
                "requires_2fa": True,
                "session_token": session_token,
                "method": user_security.two_factor_method,
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """Devuelve la identidad, roles y perfiles institucionales del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user).data)


class MeChangePasswordView(APIView):
    """Cambio de la propia contraseña (RN-22): limpia `debe_cambiar_password`."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangeOwnPasswordSerializer, responses=MeSerializer)
    def post(self, request):
        ser = ChangeOwnPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        usuario = request.user
        if not usuario.check_password(ser.validated_data["password_actual"]):
            return Response(
                {"password_actual": ["La contraseña actual no es correcta."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            usuario.set_password(ser.validated_data["password_nueva"])
            usuario.save(update_fields=["password"])
            seguridad, _ = UserSecurity.objects.get_or_create(usuario=usuario)
            seguridad.password_changed_at = timezone.now()
            seguridad.debe_cambiar_password = False
            seguridad.save(update_fields=["debe_cambiar_password", "password_changed_at", "actualizado_en"])
            registrar_auditoria(usuario, "ACTUALIZAR", usuario, nombre_campo="password")
        return Response(MeSerializer(usuario).data)


class UserViewSet(viewsets.ModelViewSet):
    """CRUD de usuarios (solo superadministrador). `DELETE` desactiva, no borra."""

    queryset = User.objects.prefetch_related("groups").all()
    permission_classes = [IsSuperUser]
    filterset_fields = ["is_active", "is_superuser", "is_staff", "groups"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["id", "username", "date_joined", "last_login"]
    ordering = ["id"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        if self.action == "set_password":
            return SetPasswordSerializer
        if self.action == "profiles":
            return UserEntityProfileWriteSerializer
        return UserReadSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Crea el usuario y devuelve la respuesta con `UserReadSerializer` incluyendo
        `password_generada` en texto claro (solo en la respuesta del POST). (T-21)
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        registrar_auditoria(request.user, "CREAR", user)
        return Response(UserReadSerializer(user).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def perform_update(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "ACTUALIZAR", objeto)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Desactiva el usuario (`is_active=False`) conservando su trazabilidad."""
        usuario = self.get_object()
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        registrar_auditoria(
            request.user,
            "DESACTIVAR",
            usuario,
            nombre_campo="is_active",
            valor_anterior=True,
            valor_nuevo=False,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="set-password")
    @transaction.atomic
    def set_password(self, request, pk=None):
        """Cambia la contraseña del usuario sin exponer su valor en la auditoría."""
        usuario = self.get_object()
        ser = SetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        usuario.set_password(ser.validated_data["password"])
        usuario.save(update_fields=["password"])
        seguridad, _ = UserSecurity.objects.get_or_create(usuario=usuario)
        seguridad.password_changed_at = timezone.now()
        seguridad.save(update_fields=["password_changed_at", "actualizado_en"])
        registrar_auditoria(request.user, "ACTUALIZAR", usuario, nombre_campo="password")
        return Response({"detalle": "Contraseña actualizada."})

    @extend_schema(
        request=UserEntityProfileWriteSerializer,
        responses=UserEntityProfileWriteReadSerializer(many=True),
    )
    @action(detail=True, methods=["get", "post", "delete"], url_path="profiles")
    def profiles(self, request, pk=None):
        """Gestiona el alcance por objeto (`UserEntityProfile`) del usuario objetivo.

        - GET: lista los perfiles del usuario; por defecto solo los activos,
          salvo ``?incluir_inactivos=true``.
        - POST: otorga/reactiva de forma idempotente el acceso a una o varias
          entidades bajo un rol (una fila por cada id de ``ids``).
        - DELETE: da de baja lógica (``activo=False``) un perfil concreto indicado
          por ``profile_id`` (query param o body).
        """
        from apps.convenios.models import UserEntityProfile

        usuario = self.get_object()

        if request.method == "GET":
            perfiles = UserEntityProfile.objects.filter(
                usuario=usuario
            ).select_related("tipo_contenido", "grupo")
            incluir_inactivos = (
                request.query_params.get("incluir_inactivos", "").lower() == "true"
            )
            if not incluir_inactivos:
                perfiles = perfiles.filter(activo=True)
            datos = UserEntityProfileWriteReadSerializer(perfiles, many=True).data
            return Response(datos)

        if request.method == "POST":
            ser = UserEntityProfileWriteSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            tipo_contenido = ser.validated_data["tipo_contenido"]
            grupo = ser.validated_data["rol"]
            ids = ser.validated_data["ids"]
            perfiles = []
            with transaction.atomic():
                for id_objeto in ids:
                    perfil, creado = UserEntityProfile.objects.get_or_create(
                        usuario=usuario,
                        tipo_contenido=tipo_contenido,
                        id_objeto=id_objeto,
                        grupo=grupo,
                        defaults={"activo": True},
                    )
                    if creado:
                        registrar_auditoria(request.user, "CREAR", perfil)
                    elif not perfil.activo:
                        perfil.activo = True
                        perfil.save(update_fields=["activo"])
                        registrar_auditoria(
                            request.user,
                            "ACTIVAR",
                            perfil,
                            nombre_campo="activo",
                            valor_anterior=False,
                            valor_nuevo=True,
                        )
                    perfiles.append(perfil)
            datos = UserEntityProfileWriteReadSerializer(perfiles, many=True).data
            return Response(datos, status=status.HTTP_201_CREATED)

        # DELETE: baja lógica de un perfil concreto.
        profile_id = request.query_params.get("profile_id") or request.data.get(
            "profile_id"
        )
        if profile_id is None:
            return Response(
                {"profile_id": ["Debe indicar el identificador del perfil a revocar."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            perfil = UserEntityProfile.objects.get(pk=profile_id, usuario=usuario)
        except (UserEntityProfile.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detalle": "El perfil indicado no pertenece al usuario."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if perfil.activo:
            with transaction.atomic():
                perfil.activo = False
                perfil.save(update_fields=["activo"])
                registrar_auditoria(
                    request.user,
                    "DESACTIVAR",
                    perfil,
                    nombre_campo="activo",
                    valor_anterior=True,
                    valor_nuevo=False,
                )
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupViewSet(viewsets.ModelViewSet):
    """CRUD de grupos (roles) con asignación de permisos (solo superadministrador)."""

    queryset = Group.objects.prefetch_related("permissions").all()
    serializer_class = GroupSerializer
    permission_classes = [IsSuperUser]
    search_fields = ["name"]
    ordering_fields = ["id", "name"]
    ordering = ["name"]

    @transaction.atomic
    def perform_create(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "CREAR", objeto)

    @transaction.atomic
    def perform_update(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "ACTUALIZAR", objeto)

    @transaction.atomic
    def perform_destroy(self, instance):
        registrar_auditoria(self.request.user, "ELIMINAR", instance)
        instance.delete()


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de permisos (solo lectura, solo superadministrador)."""

    queryset = Permission.objects.select_related("content_type").all()
    serializer_class = PermissionSerializer
    permission_classes = [IsSuperUser]
    filterset_fields = ["content_type", "content_type__app_label"]
    search_fields = ["name", "codename"]
    ordering_fields = ["id", "codename"]
    ordering = ["content_type", "codename"]


class ContentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de `ContentType` de Django (solo lectura) para selectores del frontend.

    Paginado y con `?search=` (por `app_label`/`model`), compatible con el combobox
    genérico. Alimenta el selector `content_types[]` del CRUD de `calendar-activities`
    e interpreta `modulos_habilitados`/`modulos_bloqueados` de `/auth/me/`. El
    `verbose_name` es el nombre legible del modelo (fallback a `ct.name` si es huérfano).
    """

    queryset = ContentType.objects.all().order_by("app_label", "model")
    serializer_class = ContentTypeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["app_label"]
    search_fields = ["app_label", "model"]
    ordering_fields = ["app_label", "model", "id"]
    ordering = ["app_label", "model"]


class AssignableEntityTypeView(APIView):
    """Lista los tipos de entidad elegibles para asignar un perfil de usuario (T11).

    Alimenta el selector «Tipo de entidad» del alta de perfiles institucionales
    (`GET/POST /api/v1/users/{id}/profiles/`). Cada item expone el `tipo_entidad`
    (nombre de modelo en minúscula) que el frontend reenvía tal cual en el POST de
    perfiles, junto con una etiqueta legible en español (`label`). Comparte la
    allowlist `ASSIGNABLE_PROFILE_MODELS` con la validación de escritura (T10), de
    modo que el catálogo ofrecido y el conjunto aceptado no pueden divergir.
    """

    permission_classes = [IsSuperUser]

    @extend_schema(
        responses=AssignableEntityTypeSerializer(many=True),
        summary="Tipos de entidad asignables a perfiles",
        description=(
            "Lista los tipos de entidad institucional sobre los que se puede otorgar "
            "un perfil (scope por objeto) a un usuario. El campo `tipo_entidad` es el "
            "valor que espera el POST de perfiles; `label` es la etiqueta legible en "
            "español (verbose_name del modelo). Restringido a superadministrador."
        ),
        tags=["common"],
    )
    def get(self, request):
        cts = ContentType.objects.get_for_models(*ASSIGNABLE_PROFILE_MODELS)
        data = [
            {
                "id": ct.id,
                "tipo_entidad": ct.model,
                "label": modelo._meta.verbose_name,
                "app_label": ct.app_label,
            }
            for modelo, ct in cts.items()
        ]
        data.sort(key=lambda item: item["label"])
        return Response(AssignableEntityTypeSerializer(data, many=True).data)


# ---------------------------------------------------------------------------
# Vistas de autenticación de dos factores (2FA)
# ---------------------------------------------------------------------------


class TwoFactorVerifyView(APIView):
    """Intercambia el ``session_token`` de login diferido por el JWT completo tras
    verificar el código OTP (TOTP o EMAIL) ingresado por el usuario (T-15).

    No requiere ningún header ``Authorization``: la autenticación se basa en
    el ``session_token`` de corta duración.
    """

    permission_classes = [AllowAny]
    serializer_class = TwoFactorVerifySerializer

    def post(self, request):
        ser = TwoFactorVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # Validar el session_token y obtener el usuario.
        user = validar_session_token(ser.validated_data["session_token"])

        # Obtener la configuración de seguridad del usuario.
        try:
            user_security = UserSecurity.objects.get(usuario=user)
        except UserSecurity.DoesNotExist:
            return Response(
                {"detalle": "Configuración de seguridad no encontrada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.conf import settings as _settings

        otp = ser.validated_data["otp_code"]

        # Con FORCE_EMAIL_2FA activo o método EMAIL → validar como OTP de correo.
        # Con método TOTP → validar con la app autenticadora.
        force_email = getattr(_settings, "FORCE_EMAIL_2FA", False)
        if not force_email and user_security.two_factor_method == "TOTP":
            totp = pyotp.TOTP(user_security.totp_secret)
            if not totp.verify(otp):
                return Response(
                    {"detalle": "El código OTP no es válido.", "code": "OTP_INVALIDO"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        else:
            if not validar_otp_email(user_security, otp):
                return Response(
                    {"detalle": "El código OTP no es válido o ha expirado.", "code": "OTP_INVALIDO"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        # Generar el par JWT completo con los mismos claims que el login normal.
        update_last_login(None, user)
        refresh = RefreshToken.for_user(user)
        # Agregar los claims personalizados del proyecto (igual que CustomTokenObtainPairSerializer).
        # Usamos _nombre_usuario para componer el nombre con apellidos cuando hay UserProfile (T-18).
        nombre = _nombre_usuario(user)
        refresh["nombre"] = nombre
        refresh["grupos"] = list(user.groups.values_list("name", flat=True))
        refresh["es_superusuario"] = user.is_superuser
        refresh["debe_cambiar_password"] = _debe_cambiar_password(user)

        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        datos = {
            "access": access_token,
            "refresh": refresh_token,
            "access_token": access_token,
            "token_type": "bearer",
            "nombre": nombre,
            "grupos": list(user.groups.values_list("name", flat=True)),
            "es_superusuario": user.is_superuser,
            "debe_cambiar_password": _debe_cambiar_password(user),
        }
        return Response(datos, status=status.HTTP_200_OK)


@extend_schema(
    request=None,
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="TotpSetupResponse",
                fields={
                    "otpauth_uri": drf_serializers.CharField(
                        help_text="URI otpauth:// para generar el código QR en la app autenticadora."
                    ),
                    "secret": drf_serializers.CharField(
                        help_text="Secreto base32 para ingresar manualmente en la app autenticadora."
                    ),
                },
            ),
            description="Secreto TOTP generado. Escanear el URI o ingresar el secret manualmente.",
        )
    },
)
class TotpSetupView(APIView):
    """Inicia la configuración TOTP: genera un nuevo secreto base32 y devuelve el
    URI de aprovisionamiento para que el frontend muestre el código QR (T-16).

    No activa el 2FA todavía; la activación ocurre tras la confirmación en
    ``POST /api/v1/auth/2fa/confirm-totp/``.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.conf import settings as _settings

        user_security, _ = UserSecurity.objects.get_or_create(usuario=request.user)
        secret = pyotp.random_base32()
        user_security.totp_secret = secret
        user_security.save(update_fields=["totp_secret", "actualizado_en"])

        uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=request.user.email,
            issuer_name=_settings.TOTP_ISSUER_NAME,
        )
        return Response({"otpauth_uri": uri, "secret": secret}, status=status.HTTP_200_OK)


class TotpConfirmView(APIView):
    """Confirma la configuración TOTP verificando que el usuario escaneó el QR
    correctamente y activa el segundo factor (T-17).

    Requiere que ``POST /api/v1/auth/2fa/setup/totp/`` haya sido llamado antes.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TotpSetupConfirmSerializer

    def post(self, request):
        ser = TotpSetupConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            user_security = UserSecurity.objects.get(usuario=request.user)
        except UserSecurity.DoesNotExist:
            return Response(
                {"detalle": "Inicia el setup TOTP antes de confirmar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        activar_2fa_totp(user_security, ser.validated_data["otp_code"], request.user)
        return Response(
            {"detalle": "Autenticación TOTP activada correctamente."},
            status=status.HTTP_200_OK,
        )


class TwoFactorSetupEmailView(APIView):
    """Activa el segundo factor por correo electrónico verificando la contraseña
    actual del usuario (T-18). Limpia el secreto TOTP previo si existía."""

    permission_classes = [IsAuthenticated]
    serializer_class = TwoFactorSetupEmailSerializer

    def post(self, request):
        ser = TwoFactorSetupEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user_security, _ = UserSecurity.objects.get_or_create(usuario=request.user)
        activar_2fa_email(user_security, ser.validated_data["password"], request.user)
        return Response(
            {"detalle": "Autenticación por correo electrónico activada correctamente."},
            status=status.HTTP_200_OK,
        )


class TwoFactorResendView(APIView):
    """Reenvía el código OTP por correo electrónico usando el ``session_token`` del
    login diferido. Aplica rate-limit: mínimo 1 minuto entre envíos (T-19).

    Solo aplica para el método EMAIL. No requiere JWT real.
    """

    permission_classes = [AllowAny]
    serializer_class = TwoFactorResendSerializer

    def post(self, request):
        ser = TwoFactorResendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = validar_session_token(ser.validated_data["session_token"])

        try:
            user_security = UserSecurity.objects.get(usuario=user)
        except UserSecurity.DoesNotExist:
            return Response(
                {"detalle": "Configuración de seguridad no encontrada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_security.two_factor_method != "EMAIL":
            return Response(
                {"detalle": "El reenvío de OTP solo aplica para el método EMAIL."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not puede_reenviar_otp(user_security):
            return Response(
                {"detalle": "Debes esperar al menos 1 minuto antes de solicitar un nuevo código."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        generar_otp_email(user_security)
        return Response(
            {"detalle": "Código reenviado al correo registrado."},
            status=status.HTTP_200_OK,
        )


class TwoFactorDisableView(APIView):
    """Desactiva el segundo factor exigiendo contraseña actual más OTP vigente
    (doble verificación — RN-2FA-07, T-20). Limpia todos los campos 2FA.

    Para el método EMAIL: si no hay OTP en curso, primero lo genera y envía
    por correo devolviendo instrucciones al cliente; si ya existe, verifica.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TwoFactorDisableSerializer

    def delete(self, request):
        ser = TwoFactorDisableSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            user_security = UserSecurity.objects.get(usuario=request.user)
        except UserSecurity.DoesNotExist:
            return Response(
                {"detalle": "El doble factor no está activo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user_security.two_factor_enabled:
            return Response(
                {"detalle": "El doble factor no está activo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Para EMAIL sin OTP en curso: generar y enviar, luego instruir al cliente.
        if user_security.two_factor_method == "EMAIL" and not user_security.otp_code:
            generar_otp_email(user_security)
            return Response(
                {
                    "detalle": (
                        "Se ha enviado un código de verificación a tu correo. "
                        "Reenvía esta petición incluyendo el código recibido."
                    )
                },
                status=status.HTTP_200_OK,
            )

        desactivar_2fa(
            user_security,
            ser.validated_data["password"],
            ser.validated_data["otp_code"],
            request.user,
        )
        return Response({"detalle": "Doble factor desactivado."}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Vistas de "olvidé mi contraseña" (T-22, T-23)
# ---------------------------------------------------------------------------


class PasswordResetRequestView(APIView):
    """Solicita el restablecimiento de contraseña enviando un OTP por correo (T-22).

    Siempre devuelve 200 para no revelar si el usuario existe (prevención de
    enumeración de usuarios). Devuelve 429 si el rate-limit de reenvío está activo.
    Accesible sin autenticación (``AllowAny``).
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        from rest_framework.exceptions import ValidationError as DRFValidationError

        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            solicitar_reset_password(ser.validated_data["username"])
        except DRFValidationError as exc:
            return Response(
                {"detalle": exc.detail[0] if exc.detail else "Error de validación."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return Response(
            {
                "detalle": (
                    "Si el usuario existe y tiene correo registrado, "
                    "recibirá un código de verificación."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Confirma el restablecimiento de contraseña validando el OTP y la nueva contraseña (T-23).

    Devuelve 400 si el OTP no es válido o la contraseña no cumple los requisitos.
    Devuelve 200 si el restablecimiento es exitoso.
    Accesible sin autenticación (``AllowAny``).
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        from rest_framework.exceptions import ValidationError as DRFValidationError

        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            confirmar_reset_password(
                ser.validated_data["username"],
                ser.validated_data["otp_code"],
                ser.validated_data["password_nueva"],
            )
        except DRFValidationError as exc:
            return Response(
                {"detalle": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detalle": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."},
            status=status.HTTP_200_OK,
        )
