"""Abstracción de almacenamiento documental (RNF-DOC-01/02/03).

Define la interfaz `DocumentStorage` (Protocol) y un stub de almacenamiento por
referencia externa. El stub NO contacta ningún backend real (S3/MinIO/etc.): el
cliente envía la clave/URL externa del archivo y aquí solo se gestiona esa
referencia. Sirve como punto de integración hasta conectar el repositorio real.
Ver `docs/arquitectura_desarrollo.md` §9.
"""

from typing import Protocol


class DocumentStorage(Protocol):
    """Interfaz estructural de un backend de almacenamiento de documentos."""

    def subir(self, archivo, ruta: str) -> str:
        """Sube un archivo y devuelve la `referencia_externa` resultante."""
        ...

    def url_firmada(self, referencia: str) -> str:
        """Devuelve una URL de descarga (firmada) para la referencia indicada."""
        ...

    def eliminar(self, referencia: str) -> None:
        """Elimina el archivo asociado a la referencia indicada."""
        ...


class ReferenciaExternaStorage:
    """Stub de almacenamiento por referencia externa (sin backend real).

    Cumple estructuralmente el `Protocol` `DocumentStorage`. En este stub el
    cliente ya envía la `referencia_externa` (clave/URL del archivo en el
    repositorio externo), de modo que no se manejan binarios ni hay I/O de red.
    """

    def subir(self, archivo, ruta: str) -> str:
        """Devuelve la `ruta`/referencia recibida sin contactar ningún backend.

        En el stub el cliente ya gestiona la subida del binario al repositorio
        externo y nos envía la referencia; este método solo la propaga.
        """
        return ruta

    def url_firmada(self, referencia: str) -> str:
        """Devuelve la `referencia` tal cual (ya es una clave/URL externa).

        Es un stub: no firma criptográficamente la URL. Se reemplazará cuando se
        integre el repositorio documental real.
        """
        return referencia

    def eliminar(self, referencia: str) -> None:
        """No-op: no hay backend que contactar (stub hasta integrar el repositorio real)."""
        return None


# Instancia por defecto reutilizable para inyectar en services y ViewSets.
storage_por_defecto: DocumentStorage = ReferenciaExternaStorage()
