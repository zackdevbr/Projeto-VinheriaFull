# CLAUDE.md — Projeto Vinheria Full (CP5)

Instruções de trabalho para agentes neste repositório. Leia antes de qualquer ação.

## 1. O que é o projeto

Check Point 5 de Edge Computing & Computer Systems (FIAP, Prof. Dr. Fábio H. Cabrini) — entrega em 26/10/2026.

Solução de monitoramento de vinherias: ESP32 com DHT-11 (DHT-22 no Wokwi), LDR, buzzer e LED azul, integrado ao FIWARE rodando em AWS EC2, com dashboard web para cadastro de múltiplas vinherias (IoT Devices), visão geral com status e alertas de cada uma, chatbot que responde por vinheria, gráficos históricos do STH-Comet, ajuste de triggers e disparo remoto de alertas sonoros e visuais.

Plano completo e autoritativo: `PLANO-CP5-VINHERIA.md`. Em caso de divergência entre este arquivo e o plano, o plano manda nos detalhes de implementação; este arquivo manda no processo de trabalho.

## 2. Divisão de papéis entre modelos

Este é o contrato mais importante do repositório.

**Opus — planejamento (plan mode).** Toda tarefa nasce aqui. Opus explora, pergunta, decide e escreve o passo a passo. Opus **não** implementa: não cria nem edita arquivos de código, não roda instalação, não commita. A única escrita permitida é no arquivo de plano.

**Sonnet — execução.** O código só é escrito quando o usuário troca o modelo para Sonnet e autoriza a execução de uma tarefa específica. Sonnet segue o plano escrito, passo a passo, sem improvisar escopo novo.

Regras derivadas:

- Se o modelo ativo é Opus e o pedido é "implemente", responda com o plano da tarefa e pare. Não comece.
- Sonnet executa uma tarefa por vez. Terminada a tarefa, para e espera revisão do usuário antes da próxima.
- Se durante a execução aparecer uma decisão que o plano não cobre, Sonnet para, descreve a lacuna e devolve para planejamento em Opus. Não decide sozinho.

## 3. Formato obrigatório de todo planejamento

Cada tarefa planejada segue esta ordem de seções, sempre nesta sequência:

1. **Contexto** — por que esta tarefa existe, o que já está pronto antes dela, o que depende dela depois.
2. **Objetivo** — uma frase do resultado observável. Deve ser verificável ("o endpoint `/api/devices` cadastra e provisiona um device no FIWARE"), nunca vago ("melhorar o backend").
3. **Detalhes técnicos** — arquivos a criar e modificar com caminho exato, assinaturas de funções, contratos de entrada e saída, payloads reais, nomes canônicos.
4. **Ferramentas e requisitos** — dependências novas, versões, variáveis de ambiente, serviços que precisam estar de pé (EC2 ligada, containers rodando, Wokwi aberto), chaves necessárias.
5. **Passos** — a lista de passos pequenos (seção 4).
6. **Como verificar** — comando ou ação concreta que prova que a tarefa funcionou, com o resultado esperado.

## 4. Passos pequenos, revisáveis e corrigíveis

O objetivo é reduzir erro ao máximo: errar pequeno, perceber rápido, corrigir barato.

- Um passo = uma ação de 2 a 5 minutos. "Escrever o teste que falha" é um passo. "Rodar o teste e confirmar que falha" é outro passo. "Implementar o mínimo para passar" é outro.
- Todo passo tem resultado observável: um arquivo criado, um teste vermelho, um teste verde, um comando com saída esperada.
- Nenhum passo altera mais de um arquivo de produção por vez, salvo quando a mudança é mecânica e idêntica em vários arquivos.
- Ao final de cada passo, informe o que mudou e o resultado da verificação. Não encadeie vários passos silenciosamente.
- Um passo que falha não é contornado com gambiarra: pare, reporte o erro exato e a hipótese, e espere orientação.
- Commit a cada passo concluído e verificado. Commits pequenos são o mecanismo de reversão.
- Nunca declare algo pronto sem ter rodado a verificação e visto a saída. Evidência antes de afirmação.

## 5. Stack fixada

Não trocar sem decisão explícita do usuário.

- **Firmware:** C++ (`.ino`), ESP32, `PubSubClient`, `DHT sensor library`, `Adafruit Unified Sensor`. Simulação no Wokwi.
- **Middleware:** FIWARE (stack `fabiocabrini/fiware` em Docker na AWS EC2) — Orion 1026, IoT Agent MQTT 4041, STH-Comet 8666, Mosquitto 1883, MongoDB 27017.
- **Back-end:** Python 3.11+, FastAPI, Uvicorn, httpx, Pydantic, SQLite, pandas, matplotlib, reportlab. Testes com pytest e respx.
- **Front-end:** React com JavaScript puro (`.jsx`), Vite, Chart.js via react-chartjs-2, react-router-dom. **Sem TypeScript.** A empresa fictícia é **Smart Solutions** (o nome "Vinheria Agnello" não é mais usado). **Gate de design:** nenhuma decisão visual do front é tomada antes de o usuário enviar anexos e exemplos de referência; o design é planejado em Opus e só depois implementado.
- **Chatbot (fase posterior):** Google Gemini via `google-genai`, modelo `gemini-2.5-flash`, com function calling.

## 6. Regras de código

- **Comentários em português** explicando o propósito de cada módulo e de cada função não óbvia. A entrega exige código comentado.
- **Encapsulamento em camadas.** Rota nunca chama `httpx` direto; rota chama `services`; só `services/fiware_client.py` fala HTTP com o FIWARE. Componente React nunca faz `fetch` direto; usa `src/api/client.js`.
- **Nada hardcoded** em módulo de lógica: IP, portas, API key e chaves saem de `ConfigStore` ou `.env`. A EC2 usa IP elástico (fixo entre liga e desliga): o default vem do `.env` (`FIWARE_HOST`) e pode ser trocado em runtime no painel Avançado do front, sem reiniciar o backend.
- Arquivos focados. Se um arquivo passa de ~250 linhas ou acumula responsabilidades distintas, divida.
- Nomes canônicos do FIWARE (não inventar variações):
  - device `vinheria00N`, entity `urn:ngsi-ld:Vinheria:00N`, type `Vinheria` (N = 1, 2, 3...; `vinheria001` é o exemplo). Cada vinheria tem também nome e cidade no cadastro.
  - headers `fiware-service: smart`, `fiware-servicepath: /`, apikey `TEF`
  - UltraLight curto: `t`, `h`, `l` · nomes longos no Orion/STH: `temperature`, `humidity`, `luminosity`
  - comandos: `blink_temp`, `blink_hum`, `blink_lux`, `alert_off`
- Sem `delay()` nos padrões de alerta do firmware — máquina de estado com `millis()`.
- Segredos nunca commitados. `.env` no `.gitignore`; `.env.example` commitado com as chaves vazias.

## 7. Comandos de desenvolvimento

```bash
# backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload          # docs em http://localhost:8000/docs
pytest tests -v

# front-end
cd frontend && npm install
npm run dev                            # http://localhost:5173
```

## 8. Convenção de commits

`feat:` nova funcionalidade · `fix:` correção · `docs:` documentação · `test:` testes · `chore:` build e configuração.

Mensagem no imperativo, em português, uma linha. Sem co-author do Claude — autor é só o usuário já logado no git.

## 9. Skills — autonomia concedida

O usuário autoriza, sem pedir permissão a cada vez:

- **Buscar e instalar skills** quando surgir uma necessidade que uma skill existente resolve melhor — via skill `find-skills`.
- **Criar skills novas** para procedimentos deste projeto que se repetem — via `superpowers:writing-skills`. Candidatos naturais: provisionar um device novo no FIWARE ponta a ponta, subir o ambiente FIWARE na EC2 e revalidar, ensaiar a demo do hands-on.
- **Ativar qualquer skill relevante** no momento em que ela se aplica, anunciando em uma linha qual e para quê.

Skills de processo vêm antes das de implementação: `superpowers:brainstorming` antes de criar feature nova, `superpowers:systematic-debugging` antes de propor conserto de bug, `superpowers:writing-plans` antes de encostar em código, `superpowers:test-driven-development` durante a implementação.

Skills criadas neste projeto ficam versionadas junto com o repositório quando fizer sentido para a equipe.

## 10. Estilo de resposta

O modo **caveman** fica sempre ativo nas respostas de chat: texto comprimido, sem floreio, substância técnica intacta, idioma do usuário (português) preservado. Nível padrão `full`; trocar só se o usuário pedir, via `caveman:caveman`.

Isso vale apenas para a conversa. Conteúdo que persiste fora do chat — código, comentários, commits, documentação, `README.md`, `PRD.md`, manuais, arquivos de memória — é escrito em prosa normal e completa.

Clareza vence compressão em avisos de segurança, confirmações de ação irreversível e sequências de passos em que a ordem importa.

## 11. Ordem de execução

Ordem do `PLANO-CP5-VINHERIA.md`: Task 1 (firmware) → Task 0 → Tasks 2 a 6 → Task 7A (chatbot Gemini multi-vinheria, `.gitignore`, `.env`) → Task 7B (relatórios CSV/PDF, primeiro corte se o prazo apertar) → Task 8 (manuais, Postman, README final), que fecha a entrega. O chatbot deixou de ser adiado na revisão de escopo de 05/10/2026 (múltiplas vinherias, decisão tomada após conversa com o professor).
