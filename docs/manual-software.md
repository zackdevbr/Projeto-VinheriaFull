# Manual de software — Smart Solutions

Ordem de subida do sistema: **EC2 (FIWARE) → Postman → backend → front-end → Wokwi/ESP32 → cadastro no painel**.

## 1. Visão geral e pré-requisitos

O FIWARE roda em Docker numa instância AWS EC2. O backend (FastAPI) e o painel (React) rodam na máquina de quem opera e se conectam à EC2. Cada vinheria é um ESP32 (físico ou no Wokwi) que publica por MQTT no Mosquitto da EC2.

Pré-requisitos:

- Conta AWS (free tier basta).
- Python 3.11 ou superior.
- Node.js 20 ou superior.
- Postman.
- Git.

## 2. EC2 com FIWARE

1. No console da AWS, crie uma instância EC2 (Ubuntu, `t2.micro` ou `t3.small`) com um par de chaves.
2. Conecte por SSH e instale o Docker e o Docker Compose.
3. Baixe e suba a stack:

   ```bash
   git clone https://github.com/fabiocabrini/fiware
   cd fiware
   docker-compose up -d
   ```

4. Confira que os cinco containers estão de pé:

   ```bash
   docker ps
   ```

   Devem aparecer orion, iot-agent, sth-comet, mosquitto e mongo.

## 3. Security Group

No Security Group da instância, libere a entrada (TCP) nas portas:

| Porta | Componente |
|---|---|
| 1026 | Orion Context Broker |
| 4041 | IoT Agent MQTT |
| 8666 | STH-Comet |
| 1883 | Mosquitto (MQTT) |

Estas portas ficam abertas sem autenticação; use a EC2 só para a demonstração e desligue-a depois.

## 4. IP elástico

1. No console da EC2, em **Elastic IPs**, aloque um endereço e associe à instância. O IP passa a ser fixo entre liga e desliga.
2. Anote o IP. Se ele mudar (nova instância ou novo IP), troque nestes quatro lugares:

| Onde | O que trocar |
|---|---|
| `backend/.env` | `FIWARE_HOST` |
| `firmware/vinheria_full.ino` | `BROKER_MQTT` (bloco `CONFIGURAÇÃO DESTA INSTÂNCIA`) |
| Postman | variável `url` da collection |
| Painel (página Avançado) | campo de IP do FIWARE; vale na hora, sem reiniciar o backend |

## 5. Postman

1. Importe `postman/CP5-Vinheria.postman_collection.json`.
2. Em **Variables** da collection, ajuste `url` para o IP elástico. `device_id` e `entity_id` começam em `vinheria001` e `urn:ngsi-ld:Vinheria:001`.
3. Execute nesta ordem:
   1. Health check do IoT Agent e do STH-Comet, e "Versao" do Orion;
   2. "Criar service group" (uma vez; o corpo tem `timestamp: true`, necessário para detectar offline);
   3. "Provisionar device";
   4. as três subscriptions: "Subscribe temperature (STH)", "Subscribe humidity (STH)" e "Subscribe luminosity (STH)";
   5. um comando de teste (por exemplo "Comando blink_temp") e depois "Comando alert_off".
4. Para provisionar outra vinheria, troque `device_id` e `entity_id` (ex.: `vinheria002` e `urn:ngsi-ld:Vinheria:002`) e rode de novo "Provisionar device" e as três subscriptions. Não crie registration à mão: o IoT Agent registra os comandos sozinho, e uma registration duplicada quebra o encaminhamento.

O painel faz esse provisionamento sozinho ao cadastrar uma vinheria. O Postman serve para conferir o estado do FIWARE e para a demonstração.

## 6. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Swagger em `http://localhost:8000/docs`. Testes: `pytest tests -v`.

Chaves do `backend/.env`:

| Chave | Para que serve | Valor padrão |
|---|---|---|
| `FIWARE_HOST` | IP elástico da EC2; pode ser trocado em runtime no painel Avançado | vazio (preencher) |
| `ORION_PORT` | Porta do Orion | `1026` |
| `IOTA_PORT` | Porta do IoT Agent | `4041` |
| `STH_PORT` | Porta do STH-Comet | `8666` |
| `FIWARE_SERVICE` | Header `fiware-service` | `smart` |
| `FIWARE_SERVICEPATH` | Header `fiware-servicepath` | `/` |
| `FIWARE_APIKEY` | API key do service group | `TEF` |
| `STH_INTERNAL_URL` | Endereço do STH-Comet visto de dentro da rede Docker (destino das subscriptions) | `http://sth-comet:8666` |
| `POLL_SECONDS` | Intervalo do poller | `5` |
| `OFFLINE_SECONDS` | Segundos sem leitura para considerar a vinheria offline | `30` |
| `HTTP_TIMEOUT_SECONDS` | Espera máxima de cada chamada ao FIWARE | `5` |
| `DATABASE_PATH` | Arquivo SQLite, relativo a `backend/` | `vinheria.db` |
| `CORS_ORIGINS` | Origens liberadas no CORS, separadas por vírgula | `http://localhost:5173` |
| `BACKUP_DIR` | Pasta dos backups do banco, sempre fora do repositório | vazio (`~/SmartSolutions/backups`) |
| `BACKUP_MINUTES` | Intervalo entre backups, em minutos | `10` |
| `BACKUP_KEEP` | Quantos backups manter | `20` |
| `GEMINI_API_KEY` | Chave do chatbot; nunca vai para o Git | vazio |
| `GEMINI_MODEL` | Modelo do Gemini | `gemini-3.5-flash-lite` |

## 7. Front-end

```bash
cd frontend
npm install
npm run dev
```

O painel abre em `http://localhost:5173` e chama o backend por proxy do Vite. O destino do proxy é `BACKEND_URL` em `frontend/.env` (copie de `frontend/.env.example`); vazio significa `http://localhost:8000`.

## 8. Primeiro uso

1. Abra o painel e vá à página de vinherias.
2. Cadastre a vinheria com o **mesmo `device_id` do firmware** (ex.: `vinheria001`), nome e cidade. O backend provisiona o device e as subscriptions no FIWARE.
3. Inicie o firmware (Wokwi ou ESP32). O LED começa **amarelo**; quando o `set_limits` chega, passa a **verde** e as leituras aparecem na visão geral.

## 9. Rodar uma vinheria Wokwi em outro computador

1. Abra o link público do projeto no Wokwi.
2. Edite o bloco `CONFIGURAÇÃO DESTA INSTÂNCIA` no `vinheria_full.ino`: `ID_DEVICE` (ex.: `vinheria002`) e `BROKER_MQTT` (IP elástico da EC2).
3. Clique em **Start**.
4. No site, cadastre a vinheria com o mesmo `device_id`, nome e cidade.

Cada instância precisa de um `ID_DEVICE` próprio.

## 10. Chatbot

1. Gere uma chave no Google AI Studio.
2. No `backend/.env`, preencha `GEMINI_API_KEY` e, se quiser, `GEMINI_MODEL`. Reinicie o backend.
3. O plano gratuito permite cerca de 20 requisições por dia por modelo; ensaie o chat com economia.
4. Sem chave, o painel funciona normalmente e o chat responde que não está configurado.

## 11. Troubleshooting

| Sintoma | Causa provável | Ação |
|---|---|---|
| Painel mostra FIWARE fora | EC2 desligada ou IP errado | Ligar a EC2; conferir o IP na página Avançado do painel |
| Vinheria sempre offline | `ID_DEVICE` diferente do cadastro; broker errado; service group sem `timestamp` | Igualar os IDs; conferir `BROKER_MQTT`; recriar o service group com `timestamp: true` |
| Comando fica `PENDING` | Wokwi lento | Aguardar; o backend não depende da confirmação |
| LED amarelo parado | `set_limits` não chegou | Recadastrar a vinheria ou salvar a faixa de novo |
| Gráfico vazio | Subscriptions do STH ausentes | Recadastrar a vinheria recria as subscriptions |
| Chat responde 429 | Cota do Gemini esgotada | Esperar a renovação ou trocar `GEMINI_MODEL` |
| Chat responde 503 | Alta demanda no Gemini | Tentar de novo ou trocar `GEMINI_MODEL` |
| OLED apagado | Endereço I2C diferente de `0x3C` ou fiação errada | Conferir SDA 21, SCL 22 e o endereço do módulo |
