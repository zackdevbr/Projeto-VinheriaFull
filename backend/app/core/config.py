"""
Configuração do backend em dois níveis.

- Settings: valores lidos do .env (ou do ambiente) na partida. São os defaults
  do projeto e incluem o IP elástico da EC2 (FIWARE_HOST).
- ConfigStore: configuração de runtime que o usuário troca pelo painel
  (IP, portas, intervalos). Fica salva no SQLite e prevalece sobre o .env,
  inclusive depois de reiniciar o backend.
"""
import json
import os
import sqlite3
from dataclasses import dataclass

from dotenv import load_dotenv

from app.models.schemas import ConfigUpdate, RuntimeConfig, normalize_host


@dataclass(frozen=True)
class Settings:
    """Configuração fixa da partida. Os defaults valem quando o .env não informa."""
    fiware_host: str = ""
    orion_port: int = 1026
    iota_port: int = 4041
    sth_port: int = 8666
    fiware_service: str = "smart"
    fiware_servicepath: str = "/"
    fiware_apikey: str = "TEF"
    sth_internal_url: str = "http://sth-comet:8666"
    poll_seconds: int = 5
    offline_seconds: int = 30
    http_timeout_seconds: float = 5.0
    database_path: str = "vinheria.db"
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)


def _env(nome: str, padrao):
    """Lê uma variável de ambiente; ausente ou em branco devolve o padrão."""
    valor = os.environ.get(nome, "").strip()
    return valor if valor else padrao


def load_settings(env_file: str | None = ".env") -> Settings:
    """Monta o Settings a partir do .env e do ambiente.

    Variáveis já definidas no ambiente têm prioridade sobre o arquivo.
    `env_file=None` ignora o arquivo (usado nos testes).
    """
    if env_file:
        load_dotenv(env_file, override=False)
    p = Settings()
    origens = _env("CORS_ORIGINS", ",".join(p.cors_origins))
    return Settings(
        fiware_host=normalize_host(_env("FIWARE_HOST", p.fiware_host)),
        orion_port=int(_env("ORION_PORT", p.orion_port)),
        iota_port=int(_env("IOTA_PORT", p.iota_port)),
        sth_port=int(_env("STH_PORT", p.sth_port)),
        fiware_service=_env("FIWARE_SERVICE", p.fiware_service),
        fiware_servicepath=_env("FIWARE_SERVICEPATH", p.fiware_servicepath),
        fiware_apikey=_env("FIWARE_APIKEY", p.fiware_apikey),
        sth_internal_url=_env("STH_INTERNAL_URL", p.sth_internal_url).rstrip("/"),
        poll_seconds=int(_env("POLL_SECONDS", p.poll_seconds)),
        offline_seconds=int(_env("OFFLINE_SECONDS", p.offline_seconds)),
        http_timeout_seconds=float(_env("HTTP_TIMEOUT_SECONDS", p.http_timeout_seconds)),
        database_path=_env("DATABASE_PATH", p.database_path),
        cors_origins=tuple(o.strip() for o in origens.split(",") if o.strip()),
    )


class ConfigStore:
    """Configuração de runtime: defaults do Settings + alterações salvas no SQLite."""

    def __init__(self, conn: sqlite3.Connection, settings: Settings):
        self._conn = conn
        self._settings = settings

    def _defaults(self) -> dict:
        """Valores de partida, vindos do .env."""
        s = self._settings
        return {
            "ec2_ip": s.fiware_host,
            "orion_port": s.orion_port,
            "iota_port": s.iota_port,
            "sth_port": s.sth_port,
            "poll_seconds": s.poll_seconds,
            "offline_seconds": s.offline_seconds,
        }

    def get(self) -> RuntimeConfig:
        """Devolve a configuração atual: defaults com os valores salvos por cima."""
        valores = self._defaults()
        for linha in self._conn.execute("SELECT key, value FROM config"):
            if linha["key"] in valores:
                valores[linha["key"]] = json.loads(linha["value"])
        return RuntimeConfig(**valores)

    def update(self, changes: ConfigUpdate) -> RuntimeConfig:
        """Grava só os campos enviados e devolve a configuração completa."""
        dados = changes.model_dump(exclude_none=True)
        with self._conn:
            for chave, valor in dados.items():
                self._conn.execute(
                    "INSERT INTO config (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (chave, json.dumps(valor)),
                )
        return self.get()
