from rest_framework.filters import SearchFilter


class UnaccentSearchFilter(SearchFilter):
    """SearchFilter que ignora tildes/acentos usando la extensión ``unaccent`` de PostgreSQL.

    Reemplaza el lookup ``icontains`` por ``unaccent__icontains`` en todos los
    ``search_fields``, permitiendo buscar "cientifica" y encontrar "CIENTÍFICA".
    """

    def construct_search(self, field_name, queryset):
        lookup = self.lookup_prefixes.get(field_name[0])
        if lookup:
            field_name = field_name[1:]
        else:
            lookup = "unaccent__icontains"
        return f"{field_name}__{lookup}"
