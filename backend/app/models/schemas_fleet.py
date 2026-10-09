"""
Modelos de dados da Task 4: alertas, comandos manuais, faixa salva e
retrato da frota.

Ficam separados de schemas.py para nenhum arquivo passar de ~250 linhas.
"""
from typing import Literal

from pydantic import BaseModel

from app.models.schemas import Limits

# device_id do alerta que registra a EC2/FIWARE fora do ar (um só para a frota)
FIWARE_ALERT_ID = "fiware"

# Atributo de um alerta: um dos sensores ou o equipamento inteiro offline
AlertAttr = Literal["temperature", "humidity", "luminosity", "offline"]
# Status de uma vinheria na visão geral; "configurando" = ESP32 ligado
# aguardando a faixa (set_limits), sem avaliar alertas
FleetStatus = Literal["ok", "alerta", "offline", "configurando"]
# Por que a vinheria está offline: ela parou de mandar leituras, ou a EC2 caiu
OfflineReason = Literal["sem_leitura", "fiware"]
# Comandos que o painel pode disparar à mão (RF09); set_limits sai só pelo PUT da faixa
ManualCommand = Literal["blink_temp", "blink_hum", "blink_lux", "alert_off"]


class Alert(BaseModel):
    """Um alerta do histórico (RF10); duration_seconds é None enquanto aberto."""
    id: int
    device_id: str
    attr: AlertAttr
    value: float | None = None
    opened_at: str
    closed_at: str | None = None
    duration_seconds: int | None = None


class ActiveAlert(BaseModel):
    """Alerta em aberto, como aparece no retrato da frota."""
    attr: AlertAttr
    value: float | None = None
    since: str


class SensorValues(BaseModel):
    """Valores atuais dos sensores; None quando falta a leitura."""
    temperature: float | None = None
    humidity: float | None = None
    luminosity: float | None = None


class VinheriaStatus(BaseModel):
    """Retrato de uma vinheria no último ciclo do poller."""
    device_id: str
    name: str
    city: str
    status: FleetStatus
    offline_reason: OfflineReason | None = None
    last_seen: str | None = None
    seconds_since: int | None = None
    current: SensorValues
    score: float | None = None
    active_alerts: list[ActiveAlert]


class FleetReport(BaseModel):
    """Resposta de GET /api/fleet: estado da EC2 e de cada vinheria."""
    fiware_online: bool
    fiware_offline_since: str | None = None
    updated_at: str | None = None
    vinherias: list[VinheriaStatus]


class LimitsUpdate(BaseModel):
    """Resposta do PUT da faixa: o que foi gravado e se já chegou ao ESP32."""
    device_id: str
    limits: Limits
    device_sync: Literal["enviado", "pendente"]


class CommandRequest(BaseModel):
    """Pedido de comando manual vindo do painel."""
    command: ManualCommand


class CommandResult(BaseModel):
    """Confirmação de que o comando foi entregue ao Orion."""
    device_id: str
    command: ManualCommand
