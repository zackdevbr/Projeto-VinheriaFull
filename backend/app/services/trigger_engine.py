"""
Motor de alertas da frota (o poller do "backend decide, ESP32 obedece").

A cada ciclo faz UMA chamada list_entities ao Orion e, para cada vinheria
cadastrada, decide entre:
- offline: sem leitura há mais de offline_seconds;
- configurando: ESP32 ligado que ainda não recebeu a faixa (configured != 1).
  O motor manda o set_limits na hora e não avalia alertas até ele confirmar;
- alerta ou ok: compara cada atributo com a faixa, com folga (histerese)
  para fechar.

Se a EC2 não responde por mais de offline_seconds, a frota inteira aparece
offline (motivo "fiware") e um único alerta da EC2 vai para o histórico.

O motor só manda o padrão de alerta quando o conjunto de atributos em
alerta muda ou quando precisa ressincronizar o ESP32, então um comando
manual do painel (RF09) não é desfeito no ciclo seguinte.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import ConfigStore
from app.models.schemas import AttrLimits, CurrentReading, Device, Limits
from app.models.schemas_fleet import FIWARE_ALERT_ID, SensorValues, VinheriaStatus
from app.services.alert_log import AlertLog
from app.services.alert_tracker import OFFLINE, AlertTracker
from app.services.device_registry import DeviceRegistry
from app.services.fiware_client import FiwareClient
from app.services.fiware_errors import FiwareError
from app.services.fleet_state import FleetState
from app.services.limits import LimitsStore, limits_to_command_value
from app.services.quality_score import quality_score
from app.services.readings import reading_from_entity
from app.services.trigger_rules import (
    DEFAULT_HYSTERESIS,
    SENSOR_ORDER,
    can_close,
    command_plan,
    direction,
    hysteresis_margin,
    is_offline,
    parse_instant,
    seconds_since,
)

log = logging.getLogger(__name__)


def _agora_utc() -> datetime:
    """Relógio padrão do motor (os testes injetam outro)."""
    return datetime.now(timezone.utc)


def _iso(instante: datetime) -> str:
    """Instante no formato gravado no SQLite (ISO 8601, segundos)."""
    return instante.isoformat(timespec="seconds")


class TriggerEngine:
    """Avalia a frota a cada ciclo, abre e fecha alertas e comanda os ESP32."""

    def __init__(self, registry: DeviceRegistry, limits: LimitsStore, alerts: AlertLog,
                 fiware: FiwareClient, config: ConfigStore, fleet: FleetState,
                 clock=_agora_utc, sleep=asyncio.sleep,
                 hysteresis: dict[str, float] | None = None):
        self._registry = registry
        self._limits = limits
        self._fiware = fiware
        self._config = config
        self._fleet = fleet
        self._clock = clock
        self._sleep = sleep
        self._hysteresis = hysteresis or DEFAULT_HYSTERESIS
        self._tracker = AlertTracker(alerts)
        # device_id -> último conjunto de atributos em alerta entregue ao ESP32;
        # ausente significa "precisa ressincronizar o padrão de alerta"
        self._synced: dict[str, frozenset[str]] = {}
        # ESP32 que já têm a faixa atual (set_limits entregue)
        self._faixa_ok: set[str] = set()
        self._loaded = False
        # Estado da EC2: instante da primeira falha, se está fora e quando voltou
        self._fiware_falha_desde: datetime | None = None
        self._fiware_offline = False
        self._fiware_voltou: datetime | None = None

    def mark_limits_pending(self, device_id: str) -> None:
        """A faixa mudou e não chegou ao ESP32: o próximo ciclo envia set_limits."""
        self._faixa_ok.discard(device_id)

    async def run(self) -> None:
        """Laço em fundo: um tick a cada poll_seconds (lido a cada volta)."""
        while True:
            try:
                await self.tick()
            except Exception:  # o poller não pode morrer por causa de um ciclo ruim
                log.exception("falha inesperada no ciclo do poller; sigo no próximo")
            await self._sleep(self._config.get().poll_seconds)

    async def tick(self) -> None:
        """Uma passada pela frota inteira (testável sem o laço)."""
        if not self._loaded:
            self._retomar()
        agora = self._clock()
        offline_seconds = self._config.get().offline_seconds
        devices = self._registry.list()
        registrados = {device.device_id for device in devices}
        self._tracker.close_except(registrados | {FIWARE_ALERT_ID}, _iso(agora))
        self._esquecer_removidos(registrados)
        if not devices and not self._fiware_offline:
            self._publicar([], agora)
            return
        try:
            entidades = await self._fiware.list_entities()
        except FiwareError as exc:
            log.warning("poller sem resposta do FIWARE (%s)", exc.message)
            self._fiware_fora(devices, agora, offline_seconds)
            return
        self._fiware_de_volta(agora)
        por_id = {entidade.get("id"): entidade for entidade in entidades}
        statuses = []
        for device in devices:
            statuses.append(await self._avaliar(
                device, por_id.get(device.entity_id, {}), agora, offline_seconds))
        self._publicar(statuses, agora)

    # ----- uma vinheria -----------------------------------------------------------

    async def _avaliar(self, device: Device, entidade: dict, agora: datetime,
                       offline_seconds: int) -> VinheriaStatus:
        """Decide offline, configurando, alerta ou ok, e sincroniza o ESP32."""
        device_id = device.device_id
        leitura = reading_from_entity(device_id, entidade)
        visto = parse_instant(leitura.time_instant)
        limites = self._limits.get(device_id)
        if is_offline(visto, parse_instant(device.created_at), agora, offline_seconds):
            if not self._em_carencia(agora, offline_seconds):
                self._tracker.open(device_id, OFFLINE, None, None, _iso(agora))
            self._esquecer_esp32(device_id)
            return self._retrato(device, leitura, visto, limites, "offline", agora)
        self._tracker.close(device_id, OFFLINE, _iso(agora))
        if leitura.configured is not True:
            # ESP32 ligado sem faixa: manda agora e não avalia alertas até ele confirmar
            self._synced.pop(device_id, None)
            await self._enviar_faixa(device, limites)
            return self._retrato(device, leitura, visto, limites, "configurando", agora)
        for attr in SENSOR_ORDER:
            self._avaliar_atributo(device_id, attr, getattr(leitura, attr),
                                   getattr(limites, attr), agora)
        await self._sincronizar(device, limites)
        status = "alerta" if self._tracker.active_sensors(device_id) else "ok"
        return self._retrato(device, leitura, visto, limites, status, agora)

    def _avaliar_atributo(self, device_id: str, attr: str, value: float | None,
                          faixa: AttrLimits, agora: datetime) -> None:
        """Abre o alerta ao sair da faixa; fecha ao voltar com folga (histerese)."""
        if value is None:
            return
        aberto = self._tracker.get(device_id, attr)
        if aberto is None:
            lado = direction(value, faixa.min, faixa.max)
            if lado is not None:
                self._tracker.open(device_id, attr, value, lado, _iso(agora))
            return
        margem = hysteresis_margin(attr, faixa.min, faixa.max, self._hysteresis)
        if can_close(value, faixa.min, faixa.max, aberto.side, margem):
            self._tracker.close(device_id, attr, _iso(agora))

    async def _enviar_faixa(self, device: Device, limites: Limits) -> None:
        """Manda o set_limits; se falhar, o próximo ciclo tenta de novo."""
        try:
            await self._fiware.send_command(device.entity_id, "set_limits",
                                            limits_to_command_value(limites))
            self._faixa_ok.add(device.device_id)
        except FiwareError as exc:
            log.warning("set_limits para %s falhou (%s); tento de novo no próximo ciclo",
                        device.device_id, exc.message)

    async def _sincronizar(self, device: Device, limites: Limits) -> None:
        """Leva ao ESP32 a faixa (se não chegou) e o padrão de alerta (se mudou)."""
        device_id = device.device_id
        if device_id not in self._faixa_ok:
            await self._enviar_faixa(device, limites)
            if device_id not in self._faixa_ok:
                return
        ativos = self._tracker.active_sensors(device_id)
        if self._synced.get(device_id) == ativos:
            return
        try:
            for comando in command_plan(ativos):
                await self._fiware.send_command(device.entity_id, comando)
            self._synced[device_id] = ativos
        except FiwareError as exc:
            log.warning("comando para %s falhou (%s); tento de novo no próximo ciclo",
                        device_id, exc.message)

    def _retrato(self, device: Device, leitura: CurrentReading, visto: datetime | None,
                 limites: Limits, status: str, agora: datetime) -> VinheriaStatus:
        """Monta o VinheriaStatus da vinheria neste ciclo."""
        nota, _ = quality_score(leitura, limites)
        return VinheriaStatus(
            device_id=device.device_id, name=device.name, city=device.city, status=status,
            offline_reason="sem_leitura" if status == "offline" else None,
            last_seen=leitura.time_instant, seconds_since=seconds_since(visto, agora),
            current=SensorValues(temperature=leitura.temperature, humidity=leitura.humidity,
                                 luminosity=leitura.luminosity),
            # Valor antigo de vinheria offline não gera nota
            score=None if status == "offline" else nota,
            active_alerts=self._tracker.active(device.device_id),
        )

    # ----- EC2 / FIWARE -------------------------------------------------------------

    def _fiware_fora(self, devices: list[Device], agora: datetime, offline_seconds: int) -> None:
        """FIWARE sem resposta: falha curta não muda nada; longa marca a frota offline."""
        if self._fiware_falha_desde is None:
            self._fiware_falha_desde = agora
        if not self._fiware_offline:
            if (agora - self._fiware_falha_desde).total_seconds() <= offline_seconds:
                return
            self._fiware_offline = True
            self._tracker.open(FIWARE_ALERT_ID, OFFLINE, None, None,
                               _iso(self._fiware_falha_desde))
            # Na volta, todos os ESP32 recebem faixa e padrão de alerta de novo
            self._synced.clear()
            self._faixa_ok.clear()
        self._publicar([self._retrato_sem_fiware(device, agora) for device in devices], agora)

    def _fiware_de_volta(self, agora: datetime) -> None:
        """FIWARE respondeu: fecha o alerta da EC2 e abre a carência dos offline."""
        self._fiware_falha_desde = None
        if self._fiware_offline:
            self._fiware_offline = False
            self._tracker.close(FIWARE_ALERT_ID, OFFLINE, _iso(agora))
            self._fiware_voltou = agora

    def _em_carencia(self, agora: datetime, offline_seconds: int) -> bool:
        """Logo após a EC2 voltar, os ESP32 ainda reconectam: não abre alerta offline."""
        return (self._fiware_voltou is not None
                and (agora - self._fiware_voltou).total_seconds() <= offline_seconds)

    def _retrato_sem_fiware(self, device: Device, agora: datetime) -> VinheriaStatus:
        """Vinheria offline por causa da EC2, com os últimos valores conhecidos."""
        anterior = self._fleet.get(device.device_id)
        last_seen = anterior.last_seen if anterior else None
        return VinheriaStatus(
            device_id=device.device_id, name=device.name, city=device.city,
            status="offline", offline_reason="fiware", last_seen=last_seen,
            seconds_since=seconds_since(parse_instant(last_seen), agora),
            current=anterior.current if anterior else SensorValues(),
            score=None, active_alerts=self._tracker.active(device.device_id),
        )

    # ----- estado ---------------------------------------------------------------------

    def _retomar(self) -> None:
        """Primeira passada: retoma os alertas abertos no SQLite.

        Se o backend reiniciou com a EC2 fora, o alerta dela volta aberto e o
        motor segue considerando a EC2 fora até o FIWARE responder.
        """
        for alerta in self._tracker.load():
            if alerta.device_id == FIWARE_ALERT_ID:
                self._fiware_offline = True
                self._fiware_falha_desde = parse_instant(alerta.opened_at)
        self._loaded = True

    def _publicar(self, statuses: list[VinheriaStatus], agora: datetime) -> None:
        """Entrega o retrato do ciclo ao FleetState, com o estado da EC2."""
        desde = (_iso(self._fiware_falha_desde)
                 if self._fiware_offline and self._fiware_falha_desde else None)
        self._fleet.replace(statuses, _iso(agora), fiware_online=not self._fiware_offline,
                            fiware_offline_since=desde)

    def _esquecer_esp32(self, device_id: str) -> None:
        """O ESP32 pode ter reiniciado: na volta, faixa e padrão de alerta vão de novo."""
        self._synced.pop(device_id, None)
        self._faixa_ok.discard(device_id)

    def _esquecer_removidos(self, registrados: set[str]) -> None:
        """Descarta o estado de vinherias removidas do cadastro."""
        for device_id in [d for d in self._synced if d not in registrados]:
            del self._synced[device_id]
        self._faixa_ok &= registrados
