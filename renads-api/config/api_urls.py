"""Rutas del API v1: router de módulos, autenticación JWT y documentación OpenAPI."""

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.common.views import (
    CustomTokenObtainPairView,
    MeChangePasswordView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
)

router = DefaultRouter()
# Los routers de cada módulo se registran aquí en fases posteriores, p. ej.:
# router.registry.extend(convenios_router.registry)

urlpatterns = [
    # Autenticación JWT
    path("auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/me/cambiar-password/", MeChangePasswordView.as_view(), name="me-cambiar-password"),
    path(
        "auth/password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    # Documentación OpenAPI
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Módulos
    path("", include("apps.convenios.urls")),
    path("", include("apps.internados.urls")),
    path("", include("apps.actividades.urls")),
    path("", include("apps.calendario.urls")),
    # Administración transversal (usuarios, roles y permisos)
    path("", include("apps.common.urls")),
    # Autenticación de dos factores — endpoints bajo /api/v1/auth/2fa/
    path("auth/", include("apps.common.urls_2fa")),
]

urlpatterns += router.urls
