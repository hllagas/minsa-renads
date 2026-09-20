"""Habilita la extensión ``unaccent`` de PostgreSQL para búsqueda sin tildes."""

from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0006_userprofile"),
    ]

    operations = [
        UnaccentExtension(),
    ]
