# Task 8 — Manuais, Postman e fechamento da entrega

> **Para quem executa (Sonnet):** siga as subtarefas na ordem, um passo por vez, com commit ao fim de cada subtarefa verificada. Esta tarefa não muda comportamento do código: a 8.0 só acrescenta comentários, e o resto verifica conteúdo, links e a collection. Se algum dado abaixo não bater com o código (pino, rota, nome de comando), pare e reporte; o código manda e o plano volta para Opus.

**Planejada em 25/10/2026**, assumindo a Task 7 (7A e 7B) concluída. Fonte: seção "Task 8" do `PLANO-CP5-VINHERIA.md`, mais o que foi encontrado no repositório nesta data.

---

## 1. Contexto

- Firmware, backend, painel e chatbot estão prontos. Os relatórios CSV/PDF (7B) são tratados como prontos; se não tiverem entrado, o executor remove as menções a relatório indicadas no passo 8.5.4.
- Já existe `postman/CP5-Vinheria.postman_collection.json` (commit `d2a0016`), feito a partir da collection do professor. Faltam nele o comando `set_limits` e o atributo de estado `c` (`configured`) que o backend provisiona.
- `README.md`, `PRD.md` e `docs/arquitetura.md` ainda descrevem o hardware antigo (LCD 16x2 e LED azul no GPIO 2). O hardware atual é OLED SSD1306 e LED RGB. O README também lista rotas que não batem com o backend.
- `docs/manual-hardware.md` e `docs/manual-software.md` não existem.
- Pedido do usuário em 25/10: **todo arquivo de código leva no topo um comentário com o nome do grupo e os integrantes**. Hoje nenhum tem. São 166 arquivos rastreados: firmware 4 (`.ino`, `.h`), backend 85 (`app/` e `tests/`, `.py`), front 77 (`src/` mais `vite.config.js`; `.js`, `.jsx`, `.css`).
- A entrega é em 26/10/2026. Esta é a última tarefa do plano; depois dela vem só o ensaio end-to-end e a gravação.

## 2. Objetivo

Um terceiro consegue, só com o repositório, montar o circuito, subir o FIWARE na EC2, provisionar uma vinheria pelo Postman, rodar backend e painel e apresentar o pitch. README, PRD e arquitetura descrevem o sistema que foi de fato construído, sem nenhuma menção a LCD, LED azul ou "a definir". Todo arquivo de código do firmware, do backend e do front começa com o cabeçalho do grupo e seus integrantes.

## 3. Detalhes técnicos

### Arquivos

| Ação | Caminho |
|---|---|
| Modificar (cabeçalho) | todo `.ino`/`.h` de `firmware/`, todo `.py` de `backend/app/` e `backend/tests/`, todo `.js`/`.jsx`/`.css` de `frontend/src/` e `frontend/vite.config.js` |
| Criar (fora do repo) | script de uma vez no scratchpad, `adiciona_cabecalho.py` |
| Modificar | `CLAUDE.md` §6 (regra do cabeçalho para arquivos novos) |
| Modificar | `postman/CP5-Vinheria.postman_collection.json` |
| Criar | `docs/manual-hardware.md` |
| Criar | `docs/manual-software.md` |
| Criar | `docs/roteiro-pitch.md` |
| Criar | `docs/img/` (prints do painel, enviados pelo usuário) |
| Modificar | `docs/arquitetura.md` |
| Modificar | `README.md` |
| Modificar | `PRD.md` |
| Modificar | `PLANO-CP5-VINHERIA.md` (marcar a Task 8) |

### Cabeçalho do grupo (texto fixo)

Nomes e RMs copiados da tabela "Equipe" do `README.md`. Vai na **primeira linha** do arquivo, seguido de uma linha em branco, antes de qualquer docstring, comentário ou import já existente. Em Python é comentário `#`, não docstring, para não tirar o lugar da docstring do módulo (que continua sendo a primeira instrução).

Python:

```python
# Smart Solutions — Monitoramento de Vinherias
# CP5 · Edge Computing & Computer Systems · FIAP · Prof. Dr. Fábio H. Cabrini
# Integrantes:
#   Eduarda Soares Moraes — RM569369
#   Isac Nilton Fernandes de Oliveira — RM573282
#   João Benedito de Oliveira Simplício — RM570206
#   Julia Souza Matarazzo — RM571340
#   Mariana Malagutti Gomes Peixoto — RM570290
```

C++, JS, JSX e CSS: o mesmo texto num bloco `/* ... */`, uma linha por item, com ` * ` no início de cada linha.

Regras do script `adiciona_cabecalho.py` (roda uma vez, não vai para o repo):
- Lista os arquivos com `git ls-files` e os filtros da tabela de arquivos acima.
- Idempotente: pula o arquivo que já contém `RM573282`.
- Lê e grava em UTF-8, preservando BOM se houver e o fim de linha do arquivo (CRLF ou LF).
- Arquivo vazio (ex.: `__init__.py`) recebe só o cabeçalho.
- Imprime quantos arquivos alterou e quantos pulou.

### Fatos do hardware (conferidos no firmware em 25/10)

| Componente | Pino / dado | Fonte |
|---|---|---|
| DHT-11 (DHT-22 no Wokwi) | GPIO 4, `DHTTYPE` no bloco de configuração | `vinheria_full.ino:44-48` |
| LDR (divisor de tensão) | GPIO 34 (ADC), mapeado 0–100 % | `vinheria_full.ino:53` |
| Buzzer | GPIO 5, tom de 2 kHz | `vinheria_full.ino:56`, `:558` |
| LED RGB | R 25, G 26, B 27, um resistor por cor | `led_rgb.h:15-17` |
| OLED SSD1306 128x64 I2C | SDA 21, SCL 22, endereço `0x3C`; sem display o firmware segue rodando | `vinheria_full.ino:58`, `:606-608` |
| Peças do Wokwi | esp32-devkit-v1, breadboard-half, dht22 + resistor, photoresistor-sensor, rgb-led + 3 resistores, buzzer, ssd1306 | `firmware/diagram.json` |
| Bibliotecas | PubSubClient, DHT sensor library, Adafruit Unified Sensor, Adafruit GFX Library, Adafruit SSD1306 | `firmware/libraries.txt` |

Semântica do LED RGB (de `led_rgb.h`): **verde** = conectado e configurado; **amarelo** = conectando, sem Wi-Fi/MQTT ou aguardando o primeiro `set_limits`; **vermelho piscando** = alerta, no ritmo do sensor (temperatura 500 ms, umidade 250 ms, luminosidade 125 ms). Buzzer: temperatura 2 bipes curtos a cada 2 s, umidade 1 bipe longo a cada 3 s, luminosidade 3 bipes rápidos a cada 2 s (`vinheria_full.ino:493-495`).

### Rotas reais do backend (conferidas em 25/10)

```
GET/PUT  /api/config
GET      /api/config/health
GET      /api/fleet
GET/POST /api/devices
GET      /api/devices/{id}
DELETE   /api/devices/{id}
GET      /api/devices/{id}/current
GET      /api/devices/{id}/history
GET      /api/devices/{id}/score
GET/PUT  /api/devices/{id}/triggers
POST     /api/devices/{id}/commands
GET      /api/alerts
POST     /api/chat
```

Mais as rotas de relatório da 7B: o executor copia caminho e método do decorador em `backend/app/api/routes_report.py`, sem inventar.

### Mudanças na collection do Postman

1. Request "Provisionar device": o corpo passa a espelhar `fiware_iota.provision_device`:
   - `commands`: `blink_temp`, `blink_hum`, `blink_lux`, `alert_off`, `set_limits`.
   - `attributes`: os três de sensor mais `{"object_id": "c", "name": "configured", "type": "Integer"}`.
2. Request "Criar service group": conferir que o corpo tem `"timestamp": true` (a detecção de offline depende de `TimeInstant`). Se não tiver, acrescentar.
3. Novo request "Comando set_limits" na pasta "3. Comandos de alerta", igual aos outros comandos:
   `PATCH http://{{url}}:1026/v2/entities/{{entity_id}}/attrs` com corpo `{"set_limits": {"type": "command", "value": "12,18,50,70,0,30"}}` (faixa padrão do backend).
4. `info.description` da collection: um parágrafo dizendo que, para provisionar outra vinheria, basta trocar `device_id` e `entity_id` (ex.: `vinheria002` e `urn:ngsi-ld:Vinheria:002`) e rodar "Provisionar device" e as três subscriptions; e que a registration dos comandos é criada pelo próprio IoT Agent, nunca à mão.
5. Variável `url` continua com o IP elástico atual (`3.215.3.216`).

### Conteúdo obrigatório dos manuais

**`docs/manual-hardware.md`**, nesta ordem: lista de materiais (com quantidade); tabela de pinagem (a de cima); esquema de montagem em texto, ligação por ligação, mais um print do circuito no Wokwi (`docs/img/wokwi-circuito.png`, enviado pelo usuário); cuidados (resistor de pull-up de 10 kΩ no dado do DHT, divisor de tensão do LDR com resistor de 10 kΩ, um resistor de 220 Ω por cor do LED RGB, OLED em 3,3 V); significado das cores do LED e dos padrões do buzzer; DHT-11 vs DHT-22 (faixa, precisão, intervalo mínimo de leitura e a troca de `DHTTYPE` no bloco de configuração); como gravar no ESP32 físico pela Arduino IDE (placa, bibliotecas de `libraries.txt`).

**`docs/manual-software.md`**, nesta ordem:
1. Visão geral e pré-requisitos (conta AWS, Python 3.11+, Node 20+, Postman, Git).
2. EC2: criar a instância, instalar Docker, `git clone https://github.com/fabiocabrini/fiware`, `docker-compose up -d`, `docker ps` mostrando orion, iot-agent, sth-comet, mosquitto e mongo.
3. Security Group: portas 1026, 4041, 8666 e 1883 abertas.
4. IP elástico: alocar, associar à EC2 e o que trocar se o IP mudar (`backend/.env` `FIWARE_HOST`, `BROKER_MQTT` no bloco do firmware, variável `{{url}}` do Postman, painel Avançado do site).
5. Postman: importar a collection, ajustar `{{url}}`, ordem de execução (health checks, service group, provisionar device, três subscriptions, comando de teste) e como provisionar outra vinheria. Dizer que o painel faz esse provisionamento sozinho no cadastro; o Postman serve para conferir e para a demonstração.
6. Backend: `pip install -r requirements.txt`, copiar `.env.example` para `.env` e explicar cada chave (tabela com chave, para que serve, valor padrão, copiada do `.env.example`), `uvicorn app.main:app --reload`, Swagger em `http://localhost:8000/docs`, `pytest tests -v`.
7. Front-end: `npm install`, `npm run dev`, `http://localhost:5173`, `BACKEND_URL` do `frontend/.env.example`.
8. Primeiro uso: cadastrar a vinheria no painel com o mesmo `device_id` do firmware, nome e cidade; LED do ESP32 passa de amarelo a verde quando o `set_limits` chega.
9. **Rodar uma vinheria Wokwi em outro computador:** abrir o link do Wokwi, editar o bloco `CONFIGURAÇÃO DESTA INSTÂNCIA` (`ID_DEVICE`, `BROKER_MQTT`), Start, cadastrar no site (`device_id`, nome, cidade).
10. Chatbot: obter a chave no Google AI Studio, `GEMINI_API_KEY` e `GEMINI_MODEL` no `.env`, limite do plano gratuito (20 requisições por dia por modelo) e o que o chat responde sem chave.
11. Troubleshooting, em tabela sintoma → causa → ação, no mínimo: painel mostra FIWARE fora (EC2 desligada ou IP errado no painel Avançado); vinheria sempre offline (ID do firmware diferente do cadastro, broker errado, service group sem `timestamp`); comando fica `PENDING` (Wokwi lento; o backend não depende do ack); LED amarelo parado (`set_limits` não chegou: recadastrar ou salvar a faixa de novo); gráfico vazio (subscriptions do STH ausentes: recadastrar a vinheria recria); chat 429 (cota do Gemini) e 503 (alta demanda, tentar de novo ou trocar `GEMINI_MODEL`); OLED apagado (endereço diferente de `0x3C`).

**`docs/roteiro-pitch.md`**: 5 a 7 minutos, em blocos com tempo e quem fala (deixar o nome em branco para o grupo preencher): problema (0:45) → arquitetura em camadas (1:00) → demo ao vivo com as 5 vinherias: visão geral, baixar o limite de temperatura só da `vinheria002`, LED e buzzer reagem, banner e toast, subir o limite, parar um Wokwi e mostrar o offline (2:30) → chatbot com as três perguntas das sugestões (1:00) → diferenciais: score, histórico de alertas, relatórios, troca de IP em runtime (0:45) → encerramento (0:15). Fecha com um checklist de preparação (EC2 ligada, 4 abas do Wokwi abertas, ESP32 físico ligado, chat ensaiado minutos antes por causa da cota).

## 4. Ferramentas e requisitos

- Nenhuma dependência nova.
- Python do backend para validar o JSON da collection.
- Para o passo opcional 8.1.6: EC2 ligada e containers de pé.
- **Entradas do usuário** (o executor pede e espera; não inventa): link público do Wokwi, link do vídeo (pode entrar depois, no último commit), prints do painel (visão geral, detalhe com gráficos, chat) e do circuito no Wokwi, salvos em `docs/img/`.

## 5. Passos

### 8.0 Cabeçalho do grupo em todo código

Fica primeiro porque é a única subtarefa que toca código; as suítes de teste provam que nada quebrou.

- [ ] **8.0.1** Rodar as suítes antes, para ter a linha de base: `cd backend; pytest tests -q` e `cd frontend; npx vitest run; npm run build`. Anotar as contagens.
- [ ] **8.0.2** Escrever `adiciona_cabecalho.py` no scratchpad, seguindo as regras da seção 3. Rodar primeiro com `--dry-run` (só lista). Esperado: 166 arquivos, nenhum fora das pastas previstas.
- [ ] **8.0.3** Rodar de verdade. Esperado: 166 alterados, 0 pulados. Rodar de novo: 0 alterados, 166 pulados.
- [ ] **8.0.4** Conferir à mão o diff de 4 arquivos: `firmware/vinheria_full.ino`, `backend/app/main.py`, um `__init__.py` vazio e `frontend/src/main.jsx`. Cabeçalho no topo, docstring ou comentário original intacto logo abaixo, sem mudança de fim de linha (`git diff --stat` sem arquivo com todas as linhas alteradas).
- [ ] **8.0.5** Conferir que ninguém ficou sem cabeçalho:
  ```powershell
  git ls-files firmware backend/app backend/tests frontend/src frontend/vite.config.js | ? { $_ -match '\.(ino|h|py|jsx?|css)$' } | ? { -not (Select-String -Path $_ -Pattern 'RM573282' -Quiet) }
  ```
  Esperado: nenhuma saída.
- [ ] **8.0.6** Rodar de novo as suítes do 8.0.1. Esperado: mesmas contagens, tudo verde, build ok.
- [ ] **8.0.7** (usuário) Abrir o sketch no Wokwi com os 4 arquivos novos e confirmar que compila e o boot aparece no OLED.
- [ ] **8.0.8** Em `CLAUDE.md` §6, acrescentar a regra: "Todo arquivo de código novo começa com o cabeçalho do grupo (Smart Solutions e os cinco integrantes com RM), no formato de `docs/specs/task-8-entrega/plan.md` §3." Isso cobre os arquivos que ainda forem criados (ex.: relatórios da 7B, se entrarem depois).
- [ ] **8.0.9** Commit: `docs: adiciona o cabecalho com o grupo e os integrantes em todo o codigo`.

### 8.1 Collection do Postman

- [ ] **8.1.1** Em "Provisionar device", acrescentar `set_limits` aos comandos e o atributo `c`/`configured`/`Integer`. Resultado: diff só nesse corpo.
- [ ] **8.1.2** Conferir `"timestamp": true` em "Criar service group"; acrescentar se faltar.
- [ ] **8.1.3** Criar o request "Comando set_limits" na pasta 3, copiando a estrutura (headers incluídos) de "Comando alert_off".
- [ ] **8.1.4** Escrever o `info.description` (item 4 das mudanças).
- [ ] **8.1.5** Validar:
  ```bash
  python -c "import json;c=json.load(open('postman/CP5-Vinheria.postman_collection.json',encoding='utf-8'));s=json.dumps(c);print([k for k in ['blink_temp','blink_hum','blink_lux','alert_off','set_limits','configured','\"timestamp\": true'] if k not in s])"
  ```
  Esperado: `[]`.
- [ ] **8.1.6** (opcional, se a EC2 estiver ligada) Importar no Postman, rodar "Comando set_limits" contra uma vinheria ligada e ver o OLED mostrar a faixa nova. Reportar o resultado.
- [ ] **8.1.7** Commit: `docs: completa a collection do postman com set_limits e configured`.

### 8.2 Manual de hardware

- [ ] **8.2.1** Pedir ao usuário o print do circuito no Wokwi e salvar em `docs/img/wokwi-circuito.png`.
- [ ] **8.2.2** Escrever `docs/manual-hardware.md` com as seções da seção 3, na ordem.
- [ ] **8.2.3** Conferir cada pino do manual contra a tabela de fatos da seção 3. Reportar a conferência.
- [ ] **8.2.4** Commit: `docs: adiciona o manual de hardware`.

### 8.3 Manual de software

- [ ] **8.3.1** Escrever as seções 1 a 5 (EC2, Security Group, IP elástico, Postman).
- [ ] **8.3.2** Escrever as seções 6 a 8 (backend, front-end, primeiro uso). A tabela do `.env` sai do `backend/.env.example` atual, chave por chave.
- [ ] **8.3.3** Escrever as seções 9 a 11 (Wokwi em outro computador, chatbot, troubleshooting).
- [ ] **8.3.4** Conferir que todo comando do manual existe (rodar `pip install -r requirements.txt --dry-run` não é necessário; basta conferir nomes de arquivo, scripts do `frontend/package.json` e chaves do `.env.example`). Reportar.
- [ ] **8.3.5** Commit: `docs: adiciona o manual de software`.

### 8.4 Arquitetura atualizada

- [ ] **8.4.1** Em `docs/arquitetura.md`, trocar todas as menções a LCD 16x2 e LED azul pelo OLED SSD1306 e pelo LED RGB (linhas 15, 132, 142-146 e 190 em 25/10). Onde houver padrão de alerta, usar a semântica de cores da seção 3.
- [ ] **8.4.2** Verificar: `rg -n "LCD|LED azul|GPIO 2\b" docs/arquitetura.md` sem resultado.
- [ ] **8.4.3** Commit: `docs: atualiza a arquitetura para o oled e o led rgb`.

### 8.5 README final

- [ ] **8.5.1** Pedir os prints do painel e salvar em `docs/img/` (`visao-geral.png`, `detalhe.png`, `chat.png`). Pedir o link do Wokwi.
- [ ] **8.5.2** Atualizar: status (concluído), tabela de links (Wokwi; vídeo fica "a definir" só até 8.7), seção "A solução" e funcionalidades (OLED, LED RGB, boot animado no OLED), diagrama em camadas (linha `[1]` com OLED e LED RGB), linha Firmware da stack (Adafruit GFX e SSD1306 no lugar de LiquidCrystal I2C), tabela de hardware (seção 3), tabela de padrões de alerta (coluna "LED RGB": vermelho piscando a 500/250/125 ms; `alert_off` volta ao verde).
- [ ] **8.5.3** Trocar o bloco "API do backend" pela lista de rotas reais da seção 3, mais a rota de relatório lida de `routes_report.py`.
- [ ] **8.5.4** Se a 7B não tiver entrado: remover "Exportação de relatório CSV e PDF" das funcionalidades e a rota de relatório. Caso contrário, nada.
- [ ] **8.5.5** Acrescentar a seção "Telas" com os três prints; "Estrutura do repositório" sem "(em construção)"; tabela "Manuais" com os três manuais e o roteiro marcados como prontos; Roadmap todo marcado.
- [ ] **8.5.6** Verificar termos e links:
  ```powershell
  rg -n "LCD|LED azul|em construção|a fazer" README.md
  Select-String -Path README.md -Pattern '\]\((?!http|#)([^)]+)\)' -AllMatches | % { $_.Matches } | % { $_.Groups[1].Value } | ? { -not (Test-Path $_) }
  ```
  Esperado: nenhuma saída nos dois.
- [ ] **8.5.7** Commit: `docs: finaliza o readme`.

### 8.6 PRD revisado

- [ ] **8.6.1** Trocar LCD e LED azul por OLED e LED RGB (linhas 42, 80, 81, 110 e 176 em 25/10).
- [ ] **8.6.2** Percorrer os requisitos funcionais (seção 5) e os entregáveis (seção 12). Para cada item não entregue ou entregue diferente, anotar ao lado em uma frase o que foi feito. Não apagar requisito. Reportar a lista de divergências ao usuário.
- [ ] **8.6.3** Verificar: `rg -n "LCD|LED azul|Agnello" PRD.md` sem resultado.
- [ ] **8.6.4** Commit: `docs: revisa o prd contra o que foi construido`.

### 8.7 Roteiro do pitch e fechamento

- [ ] **8.7.1** Escrever `docs/roteiro-pitch.md` (seção 3) e linkar no README, na tabela "Manuais".
- [ ] **8.7.2** Commit: `docs: adiciona o roteiro do pitch`.
- [ ] **8.7.3** (usuário) Ensaiar com as 5 instâncias seguindo a "Verificação end-to-end" do plano e gravar o vídeo.
- [ ] **8.7.4** Pôr o link do vídeo no README; marcar a Task 8 como concluída no `PLANO-CP5-VINHERIA.md`.
- [ ] **8.7.5** Verificar: `rg -n "a definir" README.md` sem resultado.
- [ ] **8.7.6** Commit: `docs: adiciona o link do video e fecha a task 8`.

## 6. Como verificar

1. `python -c ...` do passo 8.1.5 imprime `[]`.
2. `rg -n "LCD|LED azul|Agnello|em construção|a definir" README.md PRD.md docs/arquitetura.md docs/manual-*.md` sem resultado.
3. Checagem de links do passo 8.5.6 sem saída.
4. `pytest backend/tests -q`, `npx vitest run` e `npm run build` com as mesmas contagens de antes da 8.0 (só comentários foram acrescentados ao código).
5. Comando do passo 8.0.5 sem saída: todo arquivo de código tem o cabeçalho do grupo.
6. Leitura de um integrante que não executou a tarefa: seguindo só o `manual-software.md`, consegue dizer a ordem de subida (EC2 → Postman → backend → front → Wokwi → cadastro) sem perguntar.
