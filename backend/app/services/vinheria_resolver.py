"""
Resolve uma referência em texto livre ("vinheria de São Paulo", "002") para
a vinheria cadastrada certa. Usado pelo chatbot (Task 7A).

A comparação ignora acentos, caixa e espaços repetidos. A busca vai do mais
preciso ao menos preciso: id exato, nome ou cidade exatos, e por fim trecho
contido no id, nome ou cidade. A primeira etapa com um único resultado
decide; uma etapa com vários resultados é ambígua e pede esclarecimento.
"""
import unicodedata

from app.models.schemas import Device
from app.services.registry_errors import AmbiguousVinheria, VinheriaNotFound


def normalize_text(texto: str) -> str:
    """Tira acentos, passa para minúsculas e colapsa os espaços."""
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def _decide(candidatos: list[Device], texto: str) -> Device | None:
    """Um candidato: devolve. Vários: AmbiguousVinheria. Nenhum: None."""
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        opcoes = sorted(candidatos, key=lambda d: d.device_id)
        nomes = ", ".join(f"{d.device_id} ({d.name}, {d.city})" for d in opcoes)
        raise AmbiguousVinheria(f"'{texto}' corresponde a mais de uma vinheria: {nomes}", opcoes)
    return None


def resolve_vinheria(texto: str, devices: list[Device]) -> Device:
    """Encontra a vinheria referida por `texto` entre as cadastradas."""
    alvo = normalize_text(texto)
    if not alvo:
        raise VinheriaNotFound("informe o id, o nome ou a cidade da vinheria")

    def _nome(d: Device) -> str:
        return normalize_text(d.name)

    def _cidade(d: Device) -> str:
        return normalize_text(d.city)

    etapas = (
        lambda d: d.device_id == alvo,
        lambda d: alvo in (_nome(d), _cidade(d)),
        lambda d: alvo in d.device_id or alvo in _nome(d) or alvo in _cidade(d),
    )
    for corresponde in etapas:
        escolhido = _decide([d for d in devices if corresponde(d)], texto)
        if escolhido is not None:
            return escolhido
    raise VinheriaNotFound(f"nenhuma vinheria corresponde a '{texto}'")
