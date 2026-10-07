"""
Modelos de dados (Pydantic) compartilhados pelo backend.

Aqui ficam os contratos de entrada e saída da API e dos services:
configuração e saúde do FIWARE (Task 2), cadastro, faixa ideal, leituras,
histórico e score (Task 3). As próximas tasks acrescentam os seus.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_PORTA = {"ge": 1, "le": 65535}
_POLL = {"ge": 1, "le": 300}
_OFFLINE = {"ge": 5, "le": 3600}

# Atributos de sensor aceitos no histórico e no score (nomes longos do Orion/STH)
SensorAttr = Literal["temperature", "humidity", "luminosity"]


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
    # Opcional para manter compatível o uso da Task 2 (provision_device)
    created_at: str | None = None


class DeviceCreate(BaseModel):
    """Entrada do cadastro de uma vinheria (o id precisa bater com o ID_DEVICE do firmware)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    device_id: str = Field(pattern=r"^vinheria\d{3}$")
    name: str = Field(min_length=1, max_length=60)
    city: str = Field(min_length=1, max_length=60)


class AttrLimits(BaseModel):
    """Faixa ideal de um atributo: serve de limite de alerta e de referência do score."""
    min: float
    max: float

    @model_validator(mode="after")
    def _min_menor_que_max(self) -> "AttrLimits":
        """Recusa faixa vazia ou invertida."""
        if self.min >= self.max:
            raise ValueError("min deve ser menor que max")
        return self


class Limits(BaseModel):
    """Faixa ideal dos três atributos de uma vinheria."""
    temperature: AttrLimits
    humidity: AttrLimits
    luminosity: AttrLimits


class DeviceDetail(Device):
    """Vinheria com a faixa ideal configurada."""
    limits: Limits


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


class CurrentReading(BaseModel):
    """Estado atual de uma vinheria; None quando ainda não há leitura válida."""
    device_id: str
    temperature: float | None = None
    humidity: float | None = None
    luminosity: float | None = None
    time_instant: str | None = None


class AttrScores(BaseModel):
    """Nota de 0 a 100 de cada atributo; None quando falta a leitura."""
    temperature: float | None = None
    humidity: float | None = None
    luminosity: float | None = None


class HistoryPoint(BaseModel):
    """Um ponto do histórico, já normalizado a partir do STH-Comet."""
    ts: str
    value: float


class HistoryQuery(BaseModel):
    """Janela de consulta do histórico: OU last_n OU intervalo de datas (ISO 8601)."""
    attr: SensorAttr
    last_n: int | None = Field(default=None, ge=1, le=500)
    date_from: str | None = None
    date_to: str | None = None

    @field_validator("date_from", "date_to")
    @classmethod
    def _data_iso(cls, valor: str | None) -> str | None:
        """Aceita só datas ISO 8601 (ex.: 2026-10-07T00:00:00)."""
        if valor is None:
            return None
        try:
            datetime.fromisoformat(valor)
        except ValueError as exc:
            raise ValueError("data deve estar em ISO 8601, ex.: 2026-10-07T00:00:00") from exc
        return valor

    @model_validator(mode="after")
    def _um_modo(self) -> "HistoryQuery":
        """Exige exatamente um modo de janela."""
        por_datas = self.date_from is not None or self.date_to is not None
        if self.last_n is None and not por_datas:
            raise ValueError("informe last_n ou date_from/date_to")
        if self.last_n is not None and por_datas:
            raise ValueError("use last_n ou date_from/date_to, não os dois")
        return self


class ScoreReport(BaseModel):
    """Score de qualidade de uma vinheria; com score None, `message` explica o motivo."""
    device_id: str
    score: float | None
    available: bool
    message: str | None = None
    attrs: AttrScores
    limits: Limits
