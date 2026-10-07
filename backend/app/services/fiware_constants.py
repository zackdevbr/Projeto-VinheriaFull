"""
Constantes canônicas do FIWARE usadas pelo cliente.

Ficam num módulo só para os componentes (IoT Agent, Orion, STH-Comet)
compartilharem os mesmos nomes sem se importarem uns aos outros.
"""

# Atributos de sensor: (nome curto no UltraLight, nome longo no Orion/STH, tipo)
SENSOR_ATTRS = (
    ("t", "temperature", "Float"),
    ("h", "humidity", "Float"),
    ("l", "luminosity", "Integer"),
)
# Comandos que o firmware entende
COMMANDS = ("blink_temp", "blink_hum", "blink_lux", "alert_off", "set_limits")
ENTITY_TYPE = "Vinheria"
# Máximo de itens por listagem no Orion (frota e subscriptions)
ORION_LIST_LIMIT = 1000
# Nomes longos aceitos em subscriptions e no histórico
ATRIBUTOS_LONGOS = tuple(longo for _, longo, _ in SENSOR_ATTRS)
# Página máxima pedida ao STH quando a consulta é por intervalo de datas
HISTORY_PAGE_LIMIT = 500
