"""
Faixa ideal de cada vinheria (tabela triggers do SQLite).

A faixa é única por atributo e serve a dois usos: limite dos alertas
(Task 4) e referência do score de qualidade. Vinheria recém-cadastrada
recebe a faixa padrão; o painel pode editá-la depois (Task 4).
"""
from app.core.db import Database
from app.models.schemas import AttrLimits, Limits

# Faixa padrão do PRD (RF11): 12–18 °C, 50–70 % de umidade, luz de 0 a 30 %
DEFAULT_LIMITS = Limits(
    temperature=AttrLimits(min=12, max=18),
    humidity=AttrLimits(min=50, max=70),
    luminosity=AttrLimits(min=0, max=30),
)

# Nomes canônicos da faixa como atributos da entidade no Orion
ORION_LIMIT_NAMES = {
    "temperature": ("temp_min", "temp_max"),
    "humidity": ("hum_min", "hum_max"),
    "luminosity": ("lux_min", "lux_max"),
}


def limits_to_orion_attrs(limits: Limits) -> dict[str, float]:
    """Converte a faixa para os atributos temp_min…lux_max publicados no Orion."""
    attrs: dict[str, float] = {}
    for attr, (nome_min, nome_max) in ORION_LIMIT_NAMES.items():
        faixa = getattr(limits, attr)
        attrs[nome_min] = faixa.min
        attrs[nome_max] = faixa.max
    return attrs


def limits_to_command_value(limits: Limits) -> str:
    """Valor do comando set_limits: "tmin;tmax;hmin;hmax;lmin;lmax".

    O separador é ; para não colidir com o | do UltraLight. Inteiros saem
    sem ".0" (12) e decimais saem como estão (12.5).
    """
    return ";".join(f"{valor:g}" for valor in limits_to_orion_attrs(limits).values())


class LimitsStore:
    """Leitura e gravação da faixa ideal no SQLite."""

    def __init__(self, conn: Database):
        self._conn = conn

    def seed_defaults(self, device_id: str) -> None:
        """Grava a faixa padrão para uma vinheria nova.

        Não faz commit: quem chama controla a transação, para gravar o device
        e a faixa juntos (ou nada).
        """
        for attr in ORION_LIMIT_NAMES:
            faixa = getattr(DEFAULT_LIMITS, attr)
            self._conn.execute(
                "INSERT INTO triggers (device_id, attr, min_value, max_value) "
                "VALUES (?, ?, ?, ?)",
                (device_id, attr, faixa.min, faixa.max),
            )

    def update(self, device_id: str, limits: Limits) -> None:
        """Substitui a faixa da vinheria numa transação própria (edição pelo painel)."""
        with self._conn:
            for attr in ORION_LIMIT_NAMES:
                faixa = getattr(limits, attr)
                self._conn.execute(
                    "INSERT INTO triggers (device_id, attr, min_value, max_value) "
                    "VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(device_id, attr) DO UPDATE SET "
                    "min_value = excluded.min_value, max_value = excluded.max_value",
                    (device_id, attr, faixa.min, faixa.max),
                )

    def get(self, device_id: str) -> Limits:
        """Faixa da vinheria; atributo sem linha no banco usa o padrão."""
        valores = {attr: getattr(DEFAULT_LIMITS, attr) for attr in ORION_LIMIT_NAMES}
        for linha in self._conn.execute(
            "SELECT attr, min_value, max_value FROM triggers WHERE device_id = ?",
            (device_id,),
        ):
            if linha["attr"] in valores:
                valores[linha["attr"]] = AttrLimits(min=linha["min_value"],
                                                    max=linha["max_value"])
        return Limits(**valores)
