"""
Modelos de dados (Pydantic) compartilhados pelo backend.

Aqui ficam os contratos de entrada e saída da API e dos services. Esta task
cria os modelos de configuração, de saúde do FIWARE e o Device; as próximas
tasks acrescentam os seus (triggers, leituras, alertas, chat).
"""
from pydantic import BaseModel, Field, field_validator

_PORTA = {"ge": 1, "le": 65535}
_POLL = {"ge": 1, "le": 300}
_OFFLINE = {"ge": 5, "le": 3600}


def normalize_host(value: str) -> str:
    """Limpa um endereço digitado pelo usuário e devolve só o host.

    Tira espaços, o esquema (http:// ou https://), qualquer caminho e a porta.
    Ex.: " http://3.3.3.3:1026/ " -> "3.3.3.3". IPv6 não é suportado.
    """
    host = value.strip()
    for prefixo in ("http://", "https://"):
        if host.lower().startswith(prefixo):
            host = host[len(prefixo):]
    host = host.split("/")[0]
    host = host.split(":")[0]
    return host.strip()


class RuntimeConfig(BaseModel):
    """Configuração em uso agora (o .env com o que o usuário mudou por cima)."""
    ec2_ip: str
    orion_port: int = Field(**_PORTA)
    iota_port: int = Field(**_PORTA)
    sth_port: int = Field(**_PORTA)
    poll_seconds: int = Field(**_POLL)
    offline_seconds: int = Field(**_OFFLINE)


class ConfigUpdate(BaseModel):
    """Alteração parcial da configuração: só os campos enviados mudam."""
    ec2_ip: str | None = None
    orion_port: int | None = Field(default=None, **_PORTA)
    iota_port: int | None = Field(default=None, **_PORTA)
    sth_port: int | None = Field(default=None, **_PORTA)
    poll_seconds: int | None = Field(default=None, **_POLL)
    offline_seconds: int | None = Field(default=None, **_OFFLINE)

    @field_validator("ec2_ip")
    @classmethod
    def _limpa_ip(cls, valor: str | None) -> str | None:
        """Normaliza o IP e recusa endereço vazio."""
        if valor is None:
            return None
        host = normalize_host(valor)
        if not host:
            raise ValueError("ec2_ip não pode ser vazio")
        return host


class Device(BaseModel):
    """Uma vinheria cadastrada: device no IoT Agent e entidade no Orion."""
    device_id: str = Field(pattern=r"^vinheria\d{3}$")
    entity_id: str
    name: str
    city: str


class ServiceHealth(BaseModel):
    """Resultado do teste de um componente do FIWARE."""
    ok: bool
    status_code: int | None = None
    latency_ms: int | None = None
    error: str | None = None


class HealthReport(BaseModel):
    """Saúde dos três componentes do FIWARE no IP configurado."""
    ok: bool
    ec2_ip: str
    orion: ServiceHealth
    iota: ServiceHealth
    sth: ServiceHealth
