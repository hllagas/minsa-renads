"""Pruebas del filtro de búsqueda sin tildes ``UnaccentSearchFilter``.

Se prueba ``construct_search`` (construcción del lookup) sin ejecutar consulta,
por lo que no depende de la extensión ``unaccent`` de PostgreSQL.
"""

from django.test import SimpleTestCase

from apps.common.filters import UnaccentSearchFilter


class UnaccentSearchFilterTests(SimpleTestCase):
    """Construcción del lookup del filtro."""

    def setUp(self):
        self.filtro = UnaccentSearchFilter()

    def test_lookup_por_defecto_unaccent_icontains(self):
        # Happy: campo simple → unaccent__icontains.
        self.assertEqual(
            self.filtro.construct_search("nombre", None), "nombre__unaccent__icontains"
        )

    def test_prefijo_igual_exacto(self):
        # Edge: prefijo "=" fuerza el lookup iexact (prefijo estándar de DRF).
        self.assertEqual(
            self.filtro.construct_search("=nombre", None), "nombre__iexact"
        )

    def test_prefijo_startswith(self):
        # Edge: prefijo "^" fuerza istartswith.
        self.assertEqual(
            self.filtro.construct_search("^nombre", None), "nombre__istartswith"
        )
