"""
Exceções do cadastro de vinherias.

Como as do FIWARE, não dependem do FastAPI; a tradução para resposta HTTP
fica em app/api/errors.py (404 para "não encontrada", 409 para conflito).
"""


class RegistryError(Exception):
    """Falha de regra do cadastro de vinherias."""
    service = "registry"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DeviceNotFound(RegistryError):
    """O device_id não está cadastrado."""


class DeviceAlreadyExists(RegistryError):
    """O device_id já está cadastrado."""


class VinheriaNotFound(RegistryError):
    """Nenhuma vinheria corresponde ao texto informado (resolver)."""


class AmbiguousVinheria(RegistryError):
    """O texto corresponde a mais de uma vinheria; `options` lista as candidatas."""

    def __init__(self, message: str, options: list):
        super().__init__(message)
        self.options = options
