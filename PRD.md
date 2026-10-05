# PRD — Smart Solutions: Monitoramento de Vinherias

Documento de requisitos de produto do Check Point 5 de Edge Computing & Computer Systems (FIAP, Prof. Dr. Fábio H. Cabrini). Entrega em **26/10/2026**.

O plano de implementação detalhado, com contratos e passos, está em `PLANO-CP5-VINHERIA.md`. Este documento descreve **o que** o produto faz e **por quê**; o plano descreve **como** ele é construído.

---

## 1. Visão e problema

Vinho é um produto vivo. Temperatura alta acelera o envelhecimento e pode "cozinhar" a bebida; umidade baixa resseca a rolha e deixa o oxigênio entrar; luz em excesso degrada compostos aromáticos. Uma rede de vinherias espalhada por várias cidades não tem como colocar uma pessoa olhando cada adega o tempo todo.

A **Smart Solutions** (empresa fictícia da equipe) oferece um sistema de monitoramento contínuo para redes de vinherias. Em cada loja, um ESP32 mede temperatura, umidade e luminosidade, envia as leituras para a nuvem e, quando algo sai da faixa, avisa no local com luz e som. Um painel web único mostra todas as vinherias da rede, guarda o histórico, permite ajustar os limites de alerta e responde perguntas em linguagem natural por meio de um chatbot.

O projeto evolui o Smart Lamp (LDR + LED integrados ao FIWARE por MQTT), feito pela mesma equipe em check points anteriores.

## 2. Objetivos e critérios de aceite

Os objetivos seguem os critérios de avaliação do CP5. Cada critério tem um aceite verificável.

| Critério | Peso | Aceite |
|---|---|---|
| Hands-on (demo ao vivo) | 40% | Com 5 vinherias ligadas (1 ESP32 físico + 4 Wokwi), alterar um limite pelo painel faz só a vinheria escolhida piscar e apitar; parar um Wokwi faz a vinheria aparecer como offline em até ~35 s; o chatbot responde com números que conferem com os gráficos. |
| Front-end | 20% | Painel com visão geral da frota, detalhe por vinheria com gráficos históricos, ajuste de triggers, linha do tempo de alertas, cadastro de dispositivos e chat. Tudo funciona sem recarregar a página. |
| Encapsulamento | 10% | Rotas não chamam HTTP direto; só `services/fiware_client.py` fala com o FIWARE. Componentes React só usam `src/api/client.js`. Nenhum IP, porta ou chave hardcoded em módulo de lógica. |
| Diferencial | 10% | Chatbot Gemini multi-vinheria, score de qualidade do ambiente, histórico de alertas e exportação de relatório CSV/PDF. |
| Manual de software e hardware | 10% | `docs/manual-hardware.md` e `docs/manual-software.md` permitem a um terceiro montar o circuito, subir o FIWARE e rodar o painel do zero. |
| GitHub, README e arquitetura | 10% | README com integrantes, descrição, links e sumário dos manuais; `docs/arquitetura.md` com diagrama em camadas e fluxos de dados; histórico de commits pequenos e descritivos. |

## 3. Personas

**Operador da vinheria / enólogo.** Trabalha na loja ou é responsável técnico por várias delas. Quer saber de imediato se alguma adega saiu da faixa ideal e qual grandeza causou o problema, sem precisar abrir gráficos. Percebe o alerta pelo som e pela luz no local, ou pelo aviso no painel. Ajusta os limites de acordo com o tipo de vinho armazenado.

**Gestor da rede.** Acompanha todas as unidades de uma vez. Quer uma visão geral com o status de cada vinheria, comparar unidades ("qual está mais úmida agora?") e exportar relatórios do período.

**Professor-avaliador.** Avalia a solução no hands-on e no repositório. Precisa ver a arquitetura FIWARE funcionando de ponta a ponta, o código comentado e organizado em camadas, e a documentação suficiente para reproduzir o projeto.

## 4. Escopo

### Dentro do escopo

- Firmware ESP32 com DHT-11 (DHT-22 no Wokwi), LDR, buzzer, LED azul e LCD 16x2 I2C.
- Publicação de telemetria em UltraLight 2.0 via MQTT e recepção de comandos de alerta.
- FIWARE em AWS EC2 com IP elástico: Mosquitto, IoT Agent MQTT, Orion, STH-Comet e MongoDB.
- Backend FastAPI com cadastro e provisionamento de dispositivos, leitura de estado e histórico, motor de triggers, detecção de offline, log de alertas, score de qualidade, chatbot e relatórios.
- Painel React com visão geral da frota, detalhe por vinheria, triggers, alertas, cadastro e chat.
- Múltiplas vinherias, cada uma com `device_id`, nome e cidade.
- Collection do Postman, manuais de hardware e software, README e vídeo.

### Fora do escopo

- Autenticação de usuários e controle de acesso no painel.
- TLS/HTTPS e autenticação no MQTT e nas portas do FIWARE.
- Hospedagem do painel na nuvem (na apresentação ele roda local, apontando para a EC2).
- Aplicativo mobile e notificações por e-mail, SMS ou push.
- Notificação em tempo real por WebSocket (o painel usa polling).
- Controle ativo do ambiente (acionar climatização ou umidificador); o sistema só alerta.

## 5. Requisitos funcionais

| ID | Requisito |
|---|---|
| RF01 | O sistema cadastra uma vinheria com `device_id` no formato `vinheria00N`, nome e cidade, e a provisiona no FIWARE (service group, device com atributos e comandos, subscriptions para o STH-Comet). |
| RF02 | O sistema lista e remove vinherias cadastradas; a remoção desfaz o cadastro local. |
| RF03 | O ESP32 publica temperatura, umidade e luminosidade a cada 2 s; leituras inválidas do DHT não são publicadas. |
| RF04 | O painel mostra o estado atual de cada vinheria (valores e horário da última leitura). |
| RF05 | O painel mostra gráficos históricos por atributo, vindos do STH-Comet, com janela por quantidade de pontos (20/50/100) ou por intervalo de datas, atualizando sozinhos. |
| RF06 | O usuário ajusta, por vinheria, os limites mínimo e máximo de temperatura, umidade e luminosidade; o painel valida que o mínimo é menor que o máximo. |
| RF07 | O backend compara cada leitura com os limites e, quando um atributo sai da faixa, envia à vinheria o comando de alerta correspondente uma única vez; quando todos os atributos voltam, envia `alert_off`. |
| RF08 | O ESP32 executa um padrão distinto de luz e som para cada anomalia (tabela na seção 9), sem bloquear a leitura dos sensores. |
| RF09 | O usuário pode disparar e desligar alertas remotamente pelo painel. |
| RF10 | Cada alerta é registrado com vinheria, atributo, valor, início, fim e duração; o painel mostra a linha do tempo geral e por vinheria. |
| RF11 | O sistema calcula um score de qualidade do ambiente de 0 a 100 por vinheria (100 na faixa ideal: 12–18 °C, 50–70 % de umidade, luz ≤ 30 %). |
| RF12 | O painel tem uma visão geral da frota: um card por vinheria com nome, cidade, status (ok, alerta, offline), valores atuais, score e tempo desde a última leitura. |
| RF13 | Uma vinheria sem atualização há mais de `offline_seconds` (padrão 30 s, configurável) é marcada como offline, gera alerta `offline` e não recebe comandos; ao voltar, o alerta é fechado. |
| RF14 | O painel exibe um aviso global (faixa fixa e toasts) sempre que uma vinheria entra em alerta, fica offline ou volta ao normal, com link para o detalhe dela. |
| RF15 | O chatbot responde em português sobre qualquer vinheria, identificada por id, nome ou cidade em texto livre ("como está a temperatura da vinheria de São Paulo?"), usando os dados reais do STH-Comet, e pede esclarecimento quando a referência é ambígua. |
| RF16 | O chatbot avisa por conta própria quando há vinherias em alerta ou offline, e compara vinherias entre si ("qual está mais quente?"). |
| RF17 | O usuário exporta um relatório CSV ou PDF por vinheria, com dados, estatísticas, gráfico e alertas do período. |
| RF18 | O LCD do ESP32 mostra a marca Smart Solutions com animação no boot e, em seguida, um carrossel com data/hora, temperatura, umidade e luminosidade. |

## 6. Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF01 | O endereço do FIWARE vem do `.env` (`FIWARE_HOST`, IP elástico) e pode ser trocado em runtime pelo painel, no painel Avançado, sem reiniciar o backend. |
| RNF02 | Todo o código é comentado em português, explicando o propósito de cada módulo e de cada função não óbvia. |
| RNF03 | Encapsulamento em camadas: rota → service → cliente FIWARE; componente React → `api/client.js`. Camadas não se cruzam. |
| RNF04 | Nenhum IP, porta ou chave hardcoded em módulo de lógica. Segredos ficam só no `.env`, que não é versionado. |
| RNF05 | Backend e painel rodam localmente no notebook da apresentação (`uvicorn` e `npm run dev`). |
| RNF06 | O painel reflete mudanças de status em até ~5 s (polling de `/api/fleet`) e detecta offline em até ~35 s. |
| RNF07 | O backend consulta o estado da frota inteira com uma única chamada ao Orion por ciclo do poller. |
| RNF08 | O firmware não usa `delay()` nos padrões de alerta; usa máquina de estado com `millis()`. |
| RNF09 | A lógica do backend é coberta por testes automatizados (`pytest` + `respx`, com o FIWARE simulado). |
| RNF10 | O mesmo firmware roda em várias instâncias; cada computador edita só o bloco `CONFIGURAÇÃO DESTA INSTÂNCIA`. |

## 7. Stack

- **Firmware:** C++ (`.ino`) no ESP32, `PubSubClient`, `DHT sensor library`, `Adafruit Unified Sensor`, `LiquidCrystal I2C`. Simulação no Wokwi.
- **Middleware:** stack `fabiocabrini/fiware` em Docker na AWS EC2.
- **Backend:** Python 3.11+, FastAPI, Uvicorn, httpx, Pydantic, SQLite, pandas, matplotlib, reportlab, `google-genai`.
- **Front-end:** React com JavaScript puro, Vite, Chart.js (`react-chartjs-2`), `react-router-dom`.
- **Chatbot:** Google Gemini, modelo `gemini-2.5-flash`, com function calling.

## 8. Arquitetura em camadas

```
[1] Camada de Dispositivo (Edge)
    ESP32 + DHT-11 (DHT-22 no Wokwi) + LDR + Buzzer + LED azul
    Firmware .ino — leitura de sensores, publish UltraLight 2.0, execução de comandos de alerta

[2] Camada de Comunicação
    Wi-Fi -> Mosquitto MQTT (1883)
    Tópicos: /TEF/<device_id>/attrs (telemetria) · /TEF/<device_id>/cmd (comandos) · /TEF/<device_id>/cmdexe (ack)

[3] Camada de Middleware IoT
    IoT Agent MQTT (4041) — tradução UltraLight 2.0 <-> NGSI-v2, provisionamento de service group e devices

[4] Camada de Contexto
    Orion Context Broker (1026) — estado atual das entidades + subscriptions
    MongoDB (27017) — persistência interna

[5] Camada de Persistência Histórica
    STH-Comet (8666) — séries temporais consultadas por lastN / dateFrom-dateTo

[6] Camada de Aplicação (backend Python — FastAPI)
    fiware_client · device_registry · trigger_engine · alert_log · quality_score · report · chatbot (Gemini)
    SQLite local: devices, triggers, alertas, config

[7] Camada de Apresentação (React + Vite)
    Dashboard: Devices · Gráficos dinâmicos · Triggers · Alertas · Chat IA · Relatórios
```

Diagramas e fluxos detalhados: `docs/arquitetura.md`.

## 9. Contratos FIWARE

**Nomes canônicos**

| Item | Valor |
|---|---|
| Device | `vinheria00N` (regex `^vinheria\d{3}$`; `vinheria001` é o exemplo) |
| Entidade | `urn:ngsi-ld:Vinheria:00N`, type `Vinheria` |
| Headers | `fiware-service: smart` · `fiware-servicepath: /` |
| API key | `TEF` |
| Protocolo | `PDI-IoTA-UltraLight` sobre MQTT |
| Atributos (UltraLight → Orion/STH) | `t` → `temperature` · `h` → `humidity` · `l` → `luminosity` |
| Comandos | `blink_temp`, `blink_hum`, `blink_lux`, `alert_off` |

**Tópicos MQTT**

| Tópico | Direção | Exemplo |
|---|---|---|
| `/TEF/<device_id>/attrs` | ESP32 → IoT Agent | `t\|24.3\|h\|58\|l\|42` |
| `/TEF/<device_id>/cmd` | IoT Agent → ESP32 | `vinheria001@blink_temp\|` |
| `/TEF/<device_id>/cmdexe` | ESP32 → IoT Agent | `vinheria001@blink_temp\|ok` |

**Comando enviado pelo backend**

```
PATCH http://<EC2>:1026/v2/entities/urn:ngsi-ld:Vinheria:001/attrs
{ "blink_temp": { "type": "command", "value": "" } }
```

**Padrões de alerta no ESP32**

| Anomalia | Comando | LED azul | Buzzer |
|---|---|---|---|
| Temperatura | `blink_temp` | pisca a cada 500 ms | 2 bipes curtos (100 ms) a cada 2 s |
| Umidade | `blink_hum` | pisca a cada 250 ms | 1 bipe longo (700 ms) a cada 3 s |
| Luminosidade | `blink_lux` | pisca a cada 125 ms | 3 bipes rápidos (60 ms) a cada 2 s |
| — | `alert_off` | apagado | silêncio |

A sequência completa de provisionamento (service group, device, subscriptions) e as armadilhas encontradas em teste estão na seção "Contratos-chave" do plano.

## 10. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| **Custo do IP elástico.** A AWS cobra por IPv4 público, inclusive com a EC2 desligada, fora do free tier. | Cobrança inesperada na conta. | Acompanhar o billing; liberar o IP elástico depois da entrega. |
| **IP exposto no firmware público.** O IP da EC2 fica no `.ino` versionado, e as portas do FIWARE estão abertas sem autenticação. | Qualquer pessoa pode ler ou escrever entidades e publicar no MQTT. | Projeto acadêmico, sem dados sensíveis; restringir o Security Group quando possível; desligar a EC2 fora das sessões; documentar o risco. |
| **DHT-11 (físico) vs DHT-22 (Wokwi).** Precisão e faixa diferentes. | Leituras divergentes entre instâncias. | `DHTTYPE` no bloco de configuração, com comentário de como trocar; manual de hardware explica a diferença. |
| **Limites do free tier da EC2.** Instância pequena rodando 5 containers. | Lentidão ou queda durante a demo. | Subir e revalidar o ambiente antes da apresentação; ensaiar com a carga real. |
| **Chave do Gemini.** Cota gratuita limitada e chave pessoal. | Chatbot indisponível na demo; vazamento da chave. | Chave só no `.env` local; testar a cota antes; o restante do painel funciona sem o chatbot. |
| **5 instâncias simultâneas na demo.** Quatro Wokwi em computadores diferentes. | Device com ID duplicado ou rede instável. | Um `device_id` por computador, definido antes; ensaio com as 5 instâncias. |
| **`TimeInstant` ausente.** A detecção de offline depende dele. | Vinherias nunca marcadas como offline. | Service group com `timestamp: true`; validado no Passo 6 da Task 1 e conferido no smoke da Task 3. |
| **Simulação lenta no Wokwi.** O ack dos comandos chega atrasado. | Status de comando fica `PENDING` no Orion. | O backend não depende do ack para o estado do alerta. |

## 11. Cronograma

| Período | Entrega |
|---|---|
| até 05/10/2026 | Task 1 (firmware) e Task 1B (marca Smart Solutions, boot animado, IP elástico) — concluídas |
| 05/10 | Task 0 — PRD, README e arquitetura |
| 06/10 a 08/10 | Task 2 (config e cliente FIWARE) e Task 3 (cadastro de devices, histórico, score) |
| 09/10 a 11/10 | Task 4 — motor de triggers, offline e log de alertas |
| 12/10 a 15/10 | Task 5 — base do painel e cadastro (depois do envio das referências de design) |
| 16/10 a 18/10 | Task 6 — visão geral, gráficos, triggers, alertas e score |
| 19/10 a 21/10 | Task 7A — chatbot Gemini multi-vinheria |
| 22/10 | Task 7B — relatórios CSV/PDF (primeiro corte se o prazo apertar) |
| 23/10 a 25/10 | Task 8 — manuais, Postman, README final, vídeo e ensaio com 5 instâncias |
| 26/10/2026 | Entrega |

## 12. Entregáveis

- Repositório no GitHub com o código completo, README e documentação.
- Firmware `firmware/vinheria_full.ino` (com `boot_animacao.h`, `diagram.json` e `libraries.txt`).
- Painel web (backend com `requirements.txt` e front-end com `package.json`).
- Link do projeto no Wokwi.
- Collection do Postman (`postman/CP5-Vinheria.postman_collection.json`).
- Manuais de hardware e software em `docs/`.
- Vídeo de apresentação da solução.
- Envio do formulário (Forms) de entrega.
