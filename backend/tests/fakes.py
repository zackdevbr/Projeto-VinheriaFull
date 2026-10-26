"""Peças falsas compartilhadas pelos testes da Task 4 (FIWARE, relógio, frota)."""
from datetime import datetime, timedelta, timezone

from app.models.schemas import HistoryPoint
from app.models.schemas_fleet import SensorValues, VinheriaStatus


def status_vinheria(device_id: str = "vinheria001", status: str = "ok") -> VinheriaStatus:
    """Um VinheriaStatus mínimo, para testes de frota e de comandos."""
    return VinheriaStatus(device_id=device_id, name="Vinheria", city="Cidade", status=status,
                          current=SensorValues(), active_alerts=[])


class FiwareFalso:
    """Substitui o FiwareClient: guarda o que foi pedido e falha quando mandado."""

    def __init__(self):
        self.entidades: list[dict] = []
        self.comandos: list[tuple[str, str, str]] = []
        self.atualizacoes: list[tuple[str, dict]] = []
        self.chamadas_listar = 0
        self.erro_listar = None
        self.erro_comando = None
        self.erro_update = None

    async def list_entities(self, entity_type: str = "Vinheria") -> list[dict]:
        self.chamadas_listar += 1
        if self.erro_listar:
            raise self.erro_listar
        return list(self.entidades)

    async def send_command(self, entity_id: str, command: str, value: str = "") -> None:
        if self.erro_comando:
            raise self.erro_comando
        self.comandos.append((entity_id, command, value))

    async def update_attrs(self, entity_id: str, attrs: dict) -> None:
        if self.erro_update:
            raise self.erro_update
        self.atualizacoes.append((entity_id, attrs))


class Relogio:
    """Relógio controlado pelo teste (UTC)."""

    def __init__(self, inicio: datetime = datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc)):
        self.agora = inicio

    def __call__(self) -> datetime:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += timedelta(seconds=segundos)

    def iso(self, segundos_atras: float = 0) -> str:
        """Instante no formato do cadastro (ISO com +00:00)."""
        return (self.agora - timedelta(seconds=segundos_atras)).isoformat(timespec="seconds")


def instante_de(relogio: Relogio, segundos_atras: float = 2) -> str:
    """TimeInstant no formato do IoT Agent, `segundos_atras` antes do relógio."""
    instante = relogio.agora - timedelta(seconds=segundos_atras)
    return instante.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def entidade(numero: str = "001", t: float | None = 15.0, h: float | None = 60.0,
             l: float | None = 10.0, c: int | None = 1,
             instante: str = "2026-10-08T11:59:58.000Z") -> dict:
    """Entidade Vinheria como o Orion devolve em keyValues; None omite o atributo.

    c = 1 é um ESP32 já configurado (recebeu a faixa); c = 0, aguardando.
    """
    dados = {"id": f"urn:ngsi-ld:Vinheria:{numero}", "type": "Vinheria", "TimeInstant": instante}
    for nome, valor in (("temperature", t), ("humidity", h), ("luminosity", l),
                        ("configured", c)):
        if valor is not None:
            dados[nome] = valor
    return dados


class ReadingsFalso:
    """Substitui o ReadingsService: devolve séries por (device_id, atributo)."""

    def __init__(self):
        self.series = {}
        self.erro = None
        self.pedidos = []

    async def history(self, device_id, query):
        self.pedidos.append((device_id, query))
        if self.erro:
            raise self.erro
        return list(self.series.get((device_id, query.attr), []))


def serie(relogio, valores, passo_min=1.0):
    """Pontos do mais velho ao mais novo, o último no instante do relógio."""
    n = len(valores)
    return [HistoryPoint(ts=(relogio.agora - timedelta(minutes=passo_min * (n - 1 - i)))
                         .strftime("%Y-%m-%dT%H:%M:%S.000Z"), value=v)
            for i, v in enumerate(valores)]
