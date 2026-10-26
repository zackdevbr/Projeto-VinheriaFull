# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290

"""Testes da ferramenta de restauração manual do banco (spec R2.5)."""
import sqlite3
from datetime import datetime

import pytest

from app.core.config import Settings
from app.core.db import connect
from app.tools.restore_backup import is_valid_backup, main, restore


def _banco_com(caminho, device_id):
    """Cria um banco com uma vinheria cadastrada."""
    banco = connect(str(caminho))
    with banco:
        banco.execute(
            "INSERT INTO devices (device_id, entity_id, name, city, created_at) "
            "VALUES (?, ?, 'Vinheria', 'Cidade', '2026-10-08T12:00:00+00:00')",
            (device_id, "urn:ngsi-ld:Vinheria:" + device_id[-3:]),
        )
    banco.close()


def _ids(caminho):
    conexao = sqlite3.connect(caminho)
    ids = [linha[0] for linha in conexao.execute("SELECT device_id FROM devices")]
    conexao.close()
    return ids


def test_is_valid_backup(tmp_path):
    bom = tmp_path / "bom.db"
    _banco_com(bom, "vinheria001")
    ruim = tmp_path / "ruim.db"
    ruim.write_text("não é sqlite", encoding="utf-8")
    vazio = tmp_path / "vazio.db"
    sqlite3.connect(vazio).close()
    assert is_valid_backup(bom) is True
    assert is_valid_backup(ruim) is False
    assert is_valid_backup(vazio) is False
    assert is_valid_backup(tmp_path / "nao-existe.db") is False


def test_restore_substitui_e_guarda_o_atual(tmp_path):
    atual = tmp_path / "vinheria.db"
    _banco_com(atual, "vinheria001")
    backup = tmp_path / "vinheria-20261008-120000.db"
    _banco_com(backup, "vinheria002")
    salvo = restore(backup, atual, clock=lambda: datetime(2026, 10, 8, 13, 0, 0))
    assert _ids(atual) == ["vinheria002"]
    assert salvo.name == "vinheria.db.antes-da-restauracao-20261008-130000"
    assert _ids(salvo) == ["vinheria001"]


def test_restore_recusa_arquivo_invalido(tmp_path):
    atual = tmp_path / "vinheria.db"
    _banco_com(atual, "vinheria001")
    falso = tmp_path / "falso.db"
    falso.write_text("não é sqlite", encoding="utf-8")
    with pytest.raises(ValueError):
        restore(falso, atual)
    assert _ids(atual) == ["vinheria001"]


def test_main_lista_backups(tmp_path, capsys):
    pasta = tmp_path / "bk"
    pasta.mkdir()
    _banco_com(pasta / "vinheria-20261008-120000.db", "vinheria001")
    settings = Settings(database_path=str(tmp_path / "vinheria.db"), backup_dir=str(pasta))
    assert main([], settings=settings) == 0
    assert "vinheria-20261008-120000.db" in capsys.readouterr().out


def test_main_restaura_pelo_nome_do_arquivo(tmp_path):
    pasta = tmp_path / "bk"
    pasta.mkdir()
    _banco_com(pasta / "vinheria-20261008-120000.db", "vinheria002")
    banco = tmp_path / "vinheria.db"
    settings = Settings(database_path=str(banco), backup_dir=str(pasta))
    assert main(["vinheria-20261008-120000.db"], settings=settings) == 0
    assert _ids(banco) == ["vinheria002"]


def test_main_arquivo_invalido_devolve_erro(tmp_path):
    settings = Settings(database_path=str(tmp_path / "vinheria.db"), backup_dir=str(tmp_path))
    assert main([str(tmp_path / "nao-existe.db")], settings=settings) == 1
