"""Testes de Settings, ConfigStore e banco (spec R1, R2 e R3)."""
import pytest
from pydantic import ValidationError

from app.core.config import ConfigStore, Settings, load_settings
from app.core.db import connect
from app.models.schemas import ConfigUpdate

VARIAVEIS = (
    "FIWARE_HOST", "ORION_PORT", "IOTA_PORT", "STH_PORT",
    "FIWARE_SERVICE", "FIWARE_SERVICEPATH", "FIWARE_APIKEY", "STH_INTERNAL_URL",
    "POLL_SECONDS", "OFFLINE_SECONDS", "HTTP_TIMEOUT_SECONDS",
    "DATABASE_PATH", "CORS_ORIGINS",
)


@pytest.fixture
def ambiente_limpo(monkeypatch):
    """Remove do ambiente as variáveis do backend para o teste controlar tudo."""
    for nome in VARIAVEIS:
        monkeypatch.delenv(nome, raising=False)
    return monkeypatch


def test_load_settings_usa_defaults(ambiente_limpo):
    s = load_settings(env_file=None)
    assert s == Settings()
    assert s.fiware_host == ""
    assert (s.orion_port, s.iota_port, s.sth_port) == (1026, 4041, 8666)
    assert (s.fiware_service, s.fiware_servicepath, s.fiware_apikey) == ("smart", "/", "TEF")
    assert s.sth_internal_url == "http://sth-comet:8666"
    assert (s.poll_seconds, s.offline_seconds) == (5, 30)
    assert s.cors_origins == ("http://localhost:5173",)


def test_load_settings_le_variaveis_de_ambiente(ambiente_limpo):
    ambiente_limpo.setenv("FIWARE_HOST", "3.3.3.3")
    ambiente_limpo.setenv("ORION_PORT", "2026")
    ambiente_limpo.setenv("POLL_SECONDS", "10")
    ambiente_limpo.setenv("HTTP_TIMEOUT_SECONDS", "2.5")
    ambiente_limpo.setenv("CORS_ORIGINS", "http://a:1, http://b:2")
    s = load_settings(env_file=None)
    assert s.fiware_host == "3.3.3.3"
    assert s.orion_port == 2026
    assert s.poll_seconds == 10
    assert s.http_timeout_seconds == 2.5
    assert s.cors_origins == ("http://a:1", "http://b:2")


def test_load_settings_normaliza_host(ambiente_limpo):
    ambiente_limpo.setenv("FIWARE_HOST", " http://3.3.3.3:1026/ ")
    assert load_settings(env_file=None).fiware_host == "3.3.3.3"


def test_load_settings_ignora_variavel_vazia(ambiente_limpo):
    ambiente_limpo.setenv("ORION_PORT", "")
    assert load_settings(env_file=None).orion_port == 1026


def test_connect_cria_tabelas(tmp_path):
    conexao = connect(str(tmp_path / "t.db"))
    nomes = {linha["name"] for linha in conexao.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    conexao.close()
    assert {"config", "devices", "triggers", "alerts"} <= nomes


def test_config_store_usa_env_quando_banco_vazio(store):
    cfg = store.get()
    assert cfg.ec2_ip == "10.0.0.1"
    assert (cfg.orion_port, cfg.iota_port, cfg.sth_port) == (1026, 4041, 8666)
    assert (cfg.poll_seconds, cfg.offline_seconds) == (5, 30)


def test_config_store_update_parcial(store):
    cfg = store.update(ConfigUpdate(ec2_ip="20.0.0.2"))
    assert cfg.ec2_ip == "20.0.0.2"
    assert cfg.orion_port == 1026
    cfg = store.update(ConfigUpdate(poll_seconds=10))
    assert cfg.ec2_ip == "20.0.0.2"
    assert cfg.poll_seconds == 10


def test_config_store_persiste_entre_conexoes(settings):
    primeira = connect(settings.database_path)
    ConfigStore(primeira, settings).update(ConfigUpdate(ec2_ip="20.0.0.2"))
    primeira.close()
    segunda = connect(settings.database_path)
    assert ConfigStore(segunda, settings).get().ec2_ip == "20.0.0.2"
    segunda.close()


def test_config_update_rejeita_ip_vazio():
    with pytest.raises(ValidationError):
        ConfigUpdate(ec2_ip="   ")
    with pytest.raises(ValidationError):
        ConfigUpdate(ec2_ip="http://")


def test_config_update_normaliza_ip():
    assert ConfigUpdate(ec2_ip=" https://20.0.0.2:4041/iot ").ec2_ip == "20.0.0.2"


@pytest.mark.parametrize("campos", [
    {"orion_port": 0},
    {"iota_port": 70000},
    {"poll_seconds": 0},
    {"poll_seconds": 301},
    {"offline_seconds": 4},
    {"offline_seconds": 3601},
])
def test_config_update_rejeita_valores_fora_da_faixa(campos):
    with pytest.raises(ValidationError):
        ConfigUpdate(**campos)
