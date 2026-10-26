# Correção: página máxima do STH-Comet (100 pontos)

Plano de correção de um bug encontrado no ensaio manual da Task 7A em 25/10/2026. Escrito no Opus; a execução é no Sonnet, um passo por vez, com commit a cada passo verificado.

Decisões do usuário (25/10/2026):

- O chat consulta no máximo **2 horas** de histórico.
- O chat usa um **cache em memória** das leituras já buscadas. Uma pergunta repetida não busca a janela inteira de novo, só os pontos novos.

## 1. Contexto

No cenário 1 do ensaio da 7A, a pergunta "Como está a vinheria de São Paulo?" respondeu que o STH-Comet estava indisponível. A investigação mostrou a causa:

- O STH-Comet da EC2 recusa qualquer página com mais de **100 pontos**. Com `lastN=101` ou `hLimit=101` ele devolve `400 Bad Request` com a mensagem `hLimit <= lastN <= config.maxPageSize`. Com 100 responde 200. O valor 100 é o `maxPageSize` padrão do STH-Comet.
- O backend pede 500 em dois lugares:
  - `backend/app/services/chat_tools.py:30` (`PONTOS_HISTORICO = 500`, usado como `lastN` pelas tools `estatisticas` e `comparar`);
  - `backend/app/services/fiware_constants.py:27` (`HISTORY_PAGE_LIMIT = 500`, usado como `hLimit` na consulta por datas).
- O 400 vira `FiwareError`, e `ChatTools.executar` o traduz como "FIWARE indisponível", que o Gemini repete ao usuário.
- **Também quebrado:** o modo "Por período" do gráfico do detalhe, que consulta por datas com `hLimit=500`. Os modos "Últimas 20/50/100" funcionam, porque o front nunca pede mais de 100.
- Os testes não pegaram o bug porque usam respx, que aceita qualquer `hLimit`.

O que já existe e será reaproveitado: `SthOperations.query_history` (fala com o STH), `ReadingsService.history` (normaliza os pontos), `HistoryQuery` (valida a janela), `filtrar_janela` e `para_datetime` de `chat_stats.py`, `horas_validas` e o tratamento de erro de `ChatTools.executar`.

Sondas feitas em 25/10/2026 contra a EC2 e o que elas descartam:

- `count=true` funciona: o header `fiware-total-count` traz o total de pontos da janela (53 na última hora no momento do teste).
- A agregação do STH (`aggrMethod`/`aggrPeriod`) responde, mas devolve somas inteiras e mínimos/máximos que não batem com os valores brutos (mínimo 5 quando a série bruta mostrava 11,1). Não é confiável e **não será usada**.
- O SQLite do backend não guarda leituras (tabelas `config`, `devices`, `triggers`, `alerts`). O cache é só em memória, sem tabela nova.

Depende desta correção: o ensaio manual da 7A (cenários 1 a 5), e depois a Task 7B (relatórios), que vai consultar histórico por datas.

## 2. Objetivo

A pergunta "Como está a vinheria de São Paulo?" no chat traz média, mínimo e máximo da última hora, sem "FIWARE indisponível". A segunda pergunta sobre a mesma vinheria busca no STH só os pontos novos. `GET /api/devices/vinheria001/history` por datas devolve mais de 100 pontos sem erro.

## 3. Detalhes técnicos

### 3.1 Estratégia

**Consulta por datas paginada (`ReadingsService.history`, vale para o gráfico e para o chat):**

1. Uma chamada de contagem (`hLimit=1&hOffset=0&count=true`) lê o total da janela no header `fiware-total-count`.
2. Se o total cabe em até 15 páginas (1.500 pontos), busca todas (`hOffset` = 0, 100, 200…). Com uma leitura a cada 6 a 8 s, 2 h dão de 900 a 1.200 pontos, então **a janela do chat sempre vem completa**.
3. Acima de 1.500 pontos, o que só acontece no "Por período" do gráfico com intervalos longos, busca 15 páginas espaçadas igualmente ao longo da janela, como amostra. É uma proteção para o gráfico não disparar centenas de requisições.
4. As páginas são buscadas em paralelo (`asyncio.gather`) e concatenadas em ordem de `hOffset`, o que mantém a ordem cronológica.

O modo `last_n` continua como está, com teto de 100 validado no schema.

**Chat com janela de 2 h e cache em memória (`HistoryCache`, só para o chat):**

- `HORAS_MAX` das tools passa de 24 para **2**. `horas_validas` já corta o valor pedido para a faixa, então "últimas 6 horas" vira 2 h. A declaração da tool para o Gemini passa a dizer "máximo 2".
- O cache guarda, por `(device_id, atributo)`, os pontos das últimas 2 h, em ordem cronológica.
- Primeira consulta (cache vazio): busca no STH a janela inteira de 2 h, mesmo que a pergunta seja de 1 h, para que a próxima pergunta, de 2 h, já esteja coberta.
- Próximas consultas: busca só de `ts do último ponto guardado` até `agora` (em geral 1 página), descarta os pontos com `ts` menor ou igual ao último guardado (o `dateFrom` do STH é inclusivo) e acrescenta o resto.
- Depois de cada atualização, corta os pontos mais velhos que 2 h.
- A tool recebe só os pontos da janela pedida (`filtrar_janela`).
- `FiwareNotFound` (sem dados no STH) devolve `[]` e não estraga o cache. Outro `FiwareError` sobe como hoje e vira "FIWARE indisponível" em `executar`. O cache fica como estava.
- Sem TTL: a atualização incremental mantém o cache em dia. O cache é por processo e some ao reiniciar o backend, o que é aceitável.

### 3.2 Arquivos e assinaturas

**`backend/app/services/fiware_constants.py`** (modificar)

```python
# Página máxima aceita pelo STH-Comet (config.maxPageSize padrão é 100;
# acima disso ele responde 400)
HISTORY_PAGE_LIMIT = 100
# Teto de páginas por consulta por datas (1.500 pontos, cobre 2 h de leituras);
# acima disso, as páginas são espaçadas ao longo da janela (amostra)
HISTORY_MAX_PAGES = 15
```

**`backend/app/services/fiware_sth.py`** (modificar)

- `query_history(..., h_offset: int = 0)`: no modo por datas, envia `hOffset=h_offset` em vez de 0 fixo. O modo `last_n` ignora o parâmetro.
- Método novo:

```python
async def count_history(self, entity_type: str, entity_id: str, attr: str,
                        date_from: str | None = None,
                        date_to: str | None = None) -> int:
    """Total de pontos do atributo na janela, pelo header fiware-total-count.

    Pede uma página de 1 ponto com count=true; sem o header, devolve 0.
    """
```

Parâmetros enviados: `hLimit=1`, `hOffset=0`, `count="true"`, mais `dateFrom`/`dateTo` quando informados. Lê `int(resposta.headers.get("fiware-total-count", 0))`.

**`backend/app/services/readings.py`** (modificar)

- Função pura nova, no topo do módulo:

```python
def deslocamentos_paginas(total: int, pagina: int, max_paginas: int) -> list[int]:
    """hOffsets das páginas a buscar para cobrir `total` pontos.

    Até `max_paginas` páginas cobrem tudo (0, pagina, 2*pagina...); acima disso,
    `max_paginas` páginas espaçadas igualmente do início ao fim da janela.
    """
```

Contrato (com `pagina=100`, `max_paginas=15`):

| total | resultado |
|---|---|
| 0 | `[]` |
| 53 | `[0]` |
| 250 | `[0, 100, 200]` |
| 1500 | `[0, 100, ..., 1400]` (15 itens) |
| 2900 | 15 itens, `round(i * (total - pagina) / (max_paginas - 1))`: `[0, 200, 400, ..., 2800]` |

- `ReadingsService.history`: se `query.last_n` estiver definido, segue igual. No modo por datas, chama `count_history`, calcula `deslocamentos_paginas(total, HISTORY_PAGE_LIMIT, HISTORY_MAX_PAGES)`, busca as páginas com `asyncio.gather(*[query_history(..., h_offset=o) for o in offsets])`, concatena e normaliza com o mesmo laço de hoje. Extrair o laço de normalização para um helper privado `_normalizar(brutos)`, para não duplicá-lo.

**`backend/app/services/history_cache.py`** (criar, cerca de 60 linhas)

```python
"""
Cache em memória do histórico usado pelo chatbot.

Guarda, por vinheria e atributo, os pontos das últimas `horas_max` horas e,
a cada consulta, busca no STH-Comet só o que chegou depois do último ponto
guardado. Evita repetir a paginação inteira a cada pergunta.
"""

class HistoryCache:
    def __init__(self, readings: ReadingsService, horas_max: float,
                 agora: Callable[[], datetime]): ...

    async def pontos(self, device_id: str, atributo: str, horas: float) -> list[HistoryPoint]:
        """Pontos das últimas `horas` (<= horas_max), atualizando o cache antes."""
```

Internos:

- `self._series: dict[tuple[str, str], list[HistoryPoint]]`.
- `_buscar(device_id, atributo, desde: datetime, ate: datetime)` monta `HistoryQuery(attr=..., date_from=_iso_utc(desde), date_to=_iso_utc(ate))` e chama `readings.history`. `FiwareNotFound` vira `[]`.
- Usa `para_datetime` e `filtrar_janela` de `chat_stats.py` e não reimplementa nenhum dos dois.
- `_iso_utc(instante) -> str` no formato `%Y-%m-%dT%H:%M:%S.000Z`, o mesmo que o front envia (`toISOString`) e que `HistoryQuery` aceita. Se já existir helper equivalente em `chat_stats.py`, reaproveitar esse.

**`backend/app/services/chat_tools.py`** (modificar)

- Remover `PONTOS_HISTORICO`.
- `HORAS_MIN, HORAS_MAX = 0.25, 2.0`.
- `ChatTools` recebe um `HistoryCache`, montado com `horas_max=HORAS_MAX` e o mesmo relógio `self._agora`. `_pontos(device_id, atributo, horas)` vira uma chamada a `self._cache.pontos(device_id, atributo, horas)`. Não remover o `except FiwareError` de `comparar`, que continua valendo.
- O executor confere onde `ChatTools` é construído (`deps.py` ou `main.py`) e nos testes (`tools` fixture). Se for mais simples, `ChatTools.__init__` cria o cache internamente a partir do `readings` que já recebe, e aí nada muda fora do arquivo. **Preferir esta opção.**

**`backend/app/services/` (declarações das tools para o Gemini)** (modificar)

- Onde estão as declarações de `estatisticas` e `comparar`, trocar a descrição do parâmetro `horas` para dizer "de 0,25 a 2 (padrão 1)". O executor localiza o arquivo com `grep -rn "horas" app/services/chat_*`. Se a instrução do sistema citar 24 h, ajustar também.

**`backend/app/models/schemas.py`** (modificar)

- `HistoryQuery.last_n`: `Field(default=None, ge=1, le=HISTORY_PAGE_LIMIT)`, importando a constante de `fiware_constants`.

**`backend/app/api/routes_data.py`** (modificar)

- Só a docstring de `read_history`: "last_n (1–100) ou date_from/date_to".

O front não muda: o contrato de `GET /history` (lista de `{ts, value}`) continua o mesmo.

### 3.3 Testes afetados

- `tests/test_fiware_sth.py`: `test_query_history_por_datas` passa a esperar `hLimit == "100"`. Testes novos para `h_offset` e para `count_history` (com o header e sem ele).
- `tests/test_readings.py`: testes puros de `deslocamentos_paginas` (a tabela acima). `test_history_repassa_janela_de_datas` precisa responder também à chamada de contagem. Use um `side_effect` no respx que olha `count` e `hOffset` nos params. Teste novo: 250 pontos viram 3 páginas concatenadas em ordem. Teste de schema: `last_n=101` é rejeitado.
- `tests/test_history_cache.py` (novo), com o `ReadingsFalso` de `test_chat_tools.py`. Se ele for usado nos dois arquivos, mover para `tests/fakes.py` em vez de copiar:
  - a primeira chamada pede a janela de 2 h que termina no relógio;
  - a segunda chamada, com o relógio 1 min à frente, pede `date_from` igual ao `ts` do último ponto e não duplica esse ponto;
  - pontos mais velhos que 2 h saem do cache;
  - pedir `horas=1` devolve só a última hora;
  - `FiwareNotFound` devolve `[]`.
- `tests/test_chat_tools.py`:
  - na linha 133, trocar `last_n == 500` por `last_n is None` e `date_from`/`date_to` com 2 h de diferença terminando no relógio;
  - os testes que pedem mais de 2 h esperam `horas_pedidas == 2.0`.
  - O `ReadingsFalso` devolve a série inteira sem olhar as datas, e o `filtrar_janela` do cache corta pela janela. Por isso as séries de 90 min continuam válidas.

## 4. Ferramentas e requisitos

- Nenhuma dependência nova (`asyncio` é da biblioteca padrão).
- Testes: `backend\.venv\Scripts\python.exe -m pytest tests -q` (venv Python 3.12).
- Para a verificação final: EC2 ligada (IP elástico `3.215.3.216`), containers FIWARE de pé, pelo menos o Wokwi da vinheria001 publicando, backend reiniciado.
- Cota do Gemini: a verificação no chat gasta de 1 a 2 requisições por pergunta. Faça só as duas perguntas do §6, item 4.

## 5. Passos

Cada passo termina com o resultado observado e, se verde, com um commit.

1. **Constantes.** Em `fiware_constants.py`, mudar `HISTORY_PAGE_LIMIT` para 100 e criar `HISTORY_MAX_PAGES = 15`, com os comentários do §3.2. Ajustar `test_query_history_por_datas` para `"100"`. Rodar `pytest tests/test_fiware_sth.py -q`: verde. Commit `fix: limita a pagina do sth-comet a 100 pontos`.
2. **Teste de `h_offset` (vermelho).** Em `test_fiware_sth.py`, teste que chama `query_history` por datas com `h_offset=200` e espera `hOffset == "200"`. Rodar: falha com `TypeError`.
3. **`h_offset` (verde).** Adicionar o parâmetro em `query_history`. Rodar `test_fiware_sth.py`: verde. Commit `feat: aceita hoffset na consulta de historico do sth`.
4. **Testes de `count_history` (vermelho).** Dois testes: com header `fiware-total-count: 253` devolve 253 e envia `count=true`, `hLimit=1`; sem o header devolve 0. Rodar: falha com `AttributeError`.
5. **`count_history` (verde).** Implementar em `fiware_sth.py`. Rodar `test_fiware_sth.py`: verde. Commit `feat: conta os pontos de uma janela no sth`.
6. **Testes de `deslocamentos_paginas` (vermelho).** Em `test_readings.py`, um teste parametrizado com as 5 linhas da tabela do §3.2. Rodar: falha com `ImportError`.
7. **`deslocamentos_paginas` (verde).** Implementar em `readings.py`. Rodar `test_readings.py -k deslocamentos`: verde. Commit `feat: calcula as paginas do historico por datas`.
8. **Testes de paginação (vermelho).** Em `test_readings.py`:
   - ajustar `test_history_repassa_janela_de_datas` para um `side_effect` que responde à contagem (header 0) e às páginas;
   - teste novo com total 250: 3 páginas de 100, 100 e 50 pontos, a lista final tem 250 pontos em ordem e os `hOffset` pedidos são `{0, 100, 200}`.
   Rodar: o teste novo falha.
9. **Paginação em `ReadingsService.history` (verde).** Extrair `_normalizar`, chamar `count_history`, calcular os deslocamentos, `asyncio.gather` e concatenar. Rodar `test_readings.py`: verde. Commit `fix: pagina o historico por datas no sth-comet`.
10. **Schema.** Teste: `HistoryQuery(attr="temperature", last_n=101)` levanta `ValidationError`. Rodar: vermelho. Trocar `le=500` por `le=HISTORY_PAGE_LIMIT` e ajustar a docstring de `routes_data.py`. Rodar: verde. Commit `fix: limita last_n a 100 no historico`.
11. **Testes do cache (vermelho).** Se `ReadingsFalso` for reaproveitado, primeiro movê-lo para `tests/fakes.py` e confirmar que `test_chat_tools.py` continua verde (commit `test: move o readingsfalso para fakes`). Depois criar `tests/test_history_cache.py` com os 5 casos do §3.3. Rodar: falha com `ImportError`.
12. **`HistoryCache` (verde).** Criar `history_cache.py` como no §3.2. Rodar `test_history_cache.py`: verde. Commit `feat: cache em memoria do historico do chat`.
13. **Testes do chat (vermelho).** Em `test_chat_tools.py`, ajustar a asserção da linha 133 (janela de 2 h por datas) e acrescentar um teste: `horas=6` vira `horas_pedidas == 2.0`. Rodar `test_chat_tools.py`: vermelho.
14. **Chat usa o cache e limita a 2 h (verde).** Em `chat_tools.py`: remover `PONTOS_HISTORICO`, `HORAS_MAX = 2.0`, criar o cache no `__init__`, `_pontos` delega ao cache. Rodar `test_chat_tools.py`: verde. Commit `fix: chat consulta ate 2 h de historico com cache`.
15. **Declarações para o Gemini.** Ajustar a descrição de `horas` para "0,25 a 2". Rodar `pytest tests -q -k chat`: verde. Commit `docs: informa ao gemini o limite de 2 h`.
16. **Suíte completa.** `pytest tests -q`: todos verdes (eram 369; o número sobe com os testes novos). Reportar o total.
17. **Verificação real** (§6). Reportar a saída. Se algo precisar mudar, pare e reporte antes de mexer.

## 6. Como verificar

1. **API, consulta por datas com mais de 100 pontos** (EC2 e Wokwi de pé, backend reiniciado, Wokwi rodando há pelo menos 15 min):

   ```bash
   F=$(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S.000Z); T=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
   curl -s "http://localhost:8000/api/devices/vinheria001/history?attr=temperature&date_from=$F&date_to=$T" | python -c "import json,sys; d=json.load(sys.stdin); print(len(d), d[0]['ts'], d[-1]['ts'])"
   ```

   Esperado: o mesmo número que o `fiware-total-count` da janela, com o primeiro `ts` perto de `F` e o último perto de agora. Nenhum 502.
2. **API, `last_n` acima do teto:** `curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/devices/vinheria001/history?attr=temperature&last_n=101"` deve dar `422`.
3. **Front:** no detalhe da vinheria001, o modo "Por período" da última hora desenha o gráfico sem erro.
4. **Chat:**
   - "Como está a vinheria de São Paulo?" traz média, mínimo e máximo, e os valores batem com o gráfico "Por período" da última hora.
   - Repita a pergunta. No log do backend, a segunda chamada ao STH deve ter um `dateFrom` recente (segundos atrás) em vez de 2 h atrás. Para ver isso, o executor pode rodar o backend com log do httpx em `INFO`, ou conferir com um `print` temporário que **não** é commitado.

   Depois disso, o ensaio da 7A segue nos cenários 2 a 5.
