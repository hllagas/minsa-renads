# Generated for the "username = numero_documento / apellidos a auth_user" refactor.
#
# Orden de operaciones (importa):
#   1. ``RunPython`` de DATOS primero, mientras las columnas ``apellido_paterno`` /
#      ``apellido_materno`` aún existen (las lee para poblar ``auth_user.last_name``)
#      y para renombrar el ``username`` de los usuarios no-superusuario a su
#      ``numero_documento``.
#   2. Solo después, los ``RemoveField`` de las columnas de apellido.
#
# El ``RunPython`` va ANTES de los ``RemoveField`` por dos motivos:
#   - Necesita leer las columnas de apellido antes de eliminarlas.
#   - PostgreSQL falla con "pending trigger events" si se mezcla RunPython (que
#     escribe filas) con un ALTER de la misma tabla en la misma transacción — el
#     mismo problema que motivó separar 0009/0010. Aquí el RunPython escribe sobre
#     ``auth_user`` (no sobre ``perfil_usuario``, la tabla que se ALTERa con los
#     RemoveField), por lo que el orden es seguro sin necesidad de separar en dos
#     migraciones. Si PostgreSQL igualmente se quejara, separar en 0011 (datos) y
#     0012 (RemoveField).

from django.db import migrations


def forwards(apps, schema_editor):
    """Combina apellidos → ``auth_user.last_name`` y renombra username = documento (no-super)."""
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("common", "UserProfile")

    for perfil in UserProfile.objects.select_related("usuario").all():
        user = perfil.usuario
        cambios = []

        # (a) Combinar apellidos → last_name (idempotente, no sobrescribe datos reales).
        combinado = f"{perfil.apellido_paterno or ''} {perfil.apellido_materno or ''}".strip()
        if combinado and not (user.last_name or "").strip():
            user.last_name = combinado[:150]
            cambios.append("last_name")

        # (b) first_name: no hay fuente en el perfil; no se inventa (queda como esté).

        # (c) username = numero_documento SOLO para NO superusuarios.
        if not user.is_superuser:
            ndoc = (perfil.numero_documento or "").strip()
            if ndoc and user.username != ndoc:
                if User.objects.exclude(pk=user.pk).filter(username=ndoc).exists():
                    raise RuntimeError(
                        f"Colisión de username al renombrar {user.username!r} -> {ndoc!r}"
                    )
                user.username = ndoc
                cambios.append("username")

        if cambios:
            user.save(update_fields=cambios)


def reverse(apps, schema_editor):
    """noop: no se revierten datos (los apellidos ya no existen en el perfil)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0010_userprofile_not_null"),
    ]

    operations = [
        # 1) DATOS primero (mientras las columnas de apellido aún existen).
        migrations.RunPython(forwards, reverse),
        # 2) Luego eliminar las columnas de apellido del perfil.
        migrations.RemoveField(
            model_name="userprofile",
            name="apellido_materno",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="apellido_paterno",
        ),
    ]
