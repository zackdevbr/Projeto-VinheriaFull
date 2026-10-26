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
# Atributos de estado do dispositivo, fora do STH: c = 1 quando o ESP32 já
# recebeu a faixa por set_limits, 0 enquanto mostra "Configure o dispositivo"
STATUS_ATTRS = (
    ("c", "configured", "Integer"),
)
ENTITY_TYPE = "Vinheria"
# Máximo de itens por listagem no Orion (frota e subscriptions)
ORION_LIST_LIMIT = 1000
# Nomes longos aceitos em subscriptions e no histórico
ATRIBUTOS_LONGOS = tuple(longo for _, longo, _ in SENSOR_ATTRS)
# Página máxima aceita pelo STH-Comet (config.maxPageSize padrão é 100;
# acima disso ele responde 400)
HISTORY_PAGE_LIMIT = 100
# Teto de páginas por consulta por datas (1.500 pontos, cobre 2 h de leituras);
# acima disso, as páginas são espaçadas ao longo da janela (amostra)
HISTORY_MAX_PAGES = 15
