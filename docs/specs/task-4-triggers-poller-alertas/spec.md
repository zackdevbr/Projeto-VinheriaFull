# Spec — Task 4: Faixa editável, motor de alertas, frota, configuração do ESP32 e backup

> Método spec-driven: esta spec diz **o que** a Task 4 entrega e **como saber que está certo**. O passo a passo de execução fica em [`plan.md`](plan.md), que segue esta spec item por item. Se as duas divergirem, a spec manda e o executor para e devolve para planejamento.
>
> Fonte: Task 4 de [`PLANO-CP5-VINHERIA.md`](../../../PLANO-CP5-VINHERIA.md) (incluindo os dois avisos de 08/10/2026), PRD (RF06, RF07, RF09, RF10, RF12, RF13, RF19) e as decisões tomadas com o usuário em 08 e 09/10/2026. Formato do `CLAUDE.md` §3: Contexto → Objetivo → Detalhes técnicos → Ferramentas e requisitos → Passos (no plano) → Como verificar.
>
> **Revisão 2 (09/10/2026, pedido do usuário):** a EC2 fora do ar aparece como offline (no painel, com um único alerta no histórico); o ESP32 nasce sem faixa e mostra "Configure o dispositivo" até receber o `set_limits`, recusando alertas antes disso; a faixa é enviada na hora (no `PUT` e assim que o ESP32 avisa que reiniciou); o firmware entra nesta task (a antiga Task 4B foi absorvida).

---

## 1. Contexto

**Por que existe.** A Task 3 deixou as vinherias cadastradas, provisionadas e legíveis, mas nada observa os dados sozinho. Falta o coração do "backend decide, ESP32 obedece": um poller que compara as leituras com a faixa ideal de cada vinheria, aciona o alerta certo no ESP32, detecta vinheria offline e EC2 fora do ar, registra tudo e entrega um retrato da frota para o painel. Falta também editar a faixa (RF06), disparar alertas à mão (RF09) e garantir que o ESP32 nunca use uma faixa que não foi cadastrada.

**O que já está pronto.**
- Task 3 (162 testes passando): `DeviceRegistry`, `LimitsStore` (`seed_defaults`, `get`), `ReadingsService`, `quality_score`, `to_float`, `FiwareClient.list_entities/send_command/update_attrs/provision_device`, tabela `alerts` vazia, faixa padrão publicada no Orion no cadastro.
- `vinheria001` (Vinheria Paulista, São Paulo) e `vinheria002` (Vinheria Mineira, Minas Gerais) cadastradas no SQLite e no FIWARE.
- Firmware: entende `blink_temp`, `blink_hum`, `blink_lux`, `alert_off` e `set_limits`; um flag por atributo, `alert_off` limpa os três; o último `blink_*` define o padrão de LED e buzzer.

**Fatos verificados no código em 08/10/2026.**
- F1: o firmware atual separa os 6 valores do `set_limits` por `|`, só aceita inteiros e nasce com uma faixa fixa (10–16 °C, 60–80 %, 0–30 %) que não veio do cadastro. O contrato canônico (`CLAUDE.md` §6) usa `;` e a faixa é float.
- F2: o backend usa uma única conexão SQLite (`check_same_thread=False`) dividida entre o loop de eventos e as threads do FastAPI. O defeito do aviso 1 foi reproduzido: com duas threads, o `rollback` de uma apagou o alerta gravado pela outra (`alertas: 0`). O `Database` com lock da R1 resolveu num protótipo (`alertas: 1`).
- F3: o `backend/vinheria.db` é o único lugar com nome, cidade, faixa editada e histórico de alertas (aviso 2). Perdê-lo já aconteceu em 08/10/2026.
- F4: com duas anomalias ao mesmo tempo, mandar só `alert_off` quando todas normalizam deixa o ESP32 no padrão errado quando só uma normaliza, porque o firmware não tem "desligar um atributo".
- F5: o backend roda no notebook, atrás de NAT; a EC2 não consegue avisá-lo. O jeito de saber que um ESP32 reiniciou é o próprio ESP32 publicar isso na telemetria, e o backend ler no ciclo seguinte (até `poll_seconds`, 5 s).

**O que depende desta task.**
- Tasks 5 e 6 (front): `GET /api/fleet` (agora um objeto com o estado da EC2), `GET|PUT /api/devices/{id}/triggers`, `POST /api/devices/{id}/commands`, `GET /api/alerts`.
- Task 7A (chatbot): `FleetState`, `AlertLog.list()`.

## 2. Objetivo

Com o backend rodando, a EC2 ligada e os Wokwi da 001 e da 002 com o firmware novo:
- ao ligar, cada ESP32 mostra "Configure o dispositivo" e, em até ~5 s, recebe a faixa cadastrada e passa ao carrossel;
- baixar o máximo de temperatura da 002 por `PUT /api/devices/vinheria002/triggers` entrega a faixa na hora e, em até um ciclo, faz o ESP32 dela piscar e apitar no padrão de temperatura, com `GET /api/fleet` mostrando a 002 em `alerta` e a 001 em `ok`, e o alerta aparecendo em `GET /api/alerts`;
- voltar a faixa faz o ESP32 parar e fecha o alerta com duração;
- parar um Wokwi deixa a vinheria `offline` em até ~35 s, e comandos a ela são recusados (409);
- a EC2 sem resposta por mais de 30 s deixa o painel com a EC2 e todas as vinherias offline e um único alerta "EC2/FIWARE offline" no histórico.

O banco ganha backup automático fora do repositório e se restaura sozinho se sumir. `pytest` passa inteiro sem rede.

## 3. Requisitos e critérios de aceite

Formato: **QUANDO** <situação>, o sistema **DEVE** <comportamento>. Cada requisito aponta os testes que o provam (código no `plan.md`).

### R1 — Banco seguro entre threads (aviso 1)
- **R1.1** `connect(path)` DEVE devolver um `Database` que embrulha a conexão com um `RLock`. `with db:` DEVE segurar o lock durante toda a transação (commit no fim, rollback em exceção), e `db.execute(...)` DEVE rodar sob o lock e devolver as linhas já lidas (`fetchone`, `fetchall`, iteração, `rowcount`, `lastrowid`).
  Testes: `test_connect_devolve_database`, `test_execute_devolve_linhas_e_lastrowid`, `test_with_faz_commit_e_rollback`.
- **R1.2** QUANDO uma thread está no meio de uma transação e outra faz uma transação que falha, o `rollback` da segunda NÃO DEVE desfazer a primeira.
  Teste: `test_transacoes_de_threads_diferentes_nao_se_misturam`.
- **R1.3** O código existente DEVE continuar funcionando; só as anotações de tipo trocam `sqlite3.Connection` por `Database`.
  Teste: a suíte inteira da Task 3 verde.
- **R1.4** Nenhum código DEVE fazer `await` dentro de um `with db:` (o `RLock` é por thread, e as corrotinas dividem a mesma thread). Regra documentada na docstring do `Database`.

### R2 — Backup do SQLite (aviso 2)
- **R2.1** `Settings` DEVE ganhar `backup_dir` (padrão da classe `""`, que desliga o backup), `backup_minutes` (10), `backup_keep` (20) e `run_background` (padrão da classe `False`). `load_settings()` DEVE ler `BACKUP_DIR`, `BACKUP_MINUTES` e `BACKUP_KEEP`, usar `~/SmartSolutions/backups` quando `BACKUP_DIR` não vier e ligar `run_background`.
  Testes: `test_load_settings_usa_defaults` (atualizado), `test_load_settings_le_backup_do_ambiente`, `test_settings_direto_desliga_backup_e_fundo`.
- **R2.2** `BackupService.backup_now()` DEVE gravar uma cópia consistente (API de backup do `sqlite3`, sob o lock) em `backup_dir/vinheria-AAAAMMDD-HHMMSS.db` e manter só os `backup_keep` mais recentes. Com `backup_dir` vazio, DEVE devolver `None` sem gravar.
  Testes: `test_backup_now_grava_copia_legivel`, `test_backup_mantem_so_os_mais_recentes`, `test_backup_desligado_sem_pasta`, `test_list_backups_pasta_inexistente`.
- **R2.3** `BackupService.run()` DEVE gravar um backup a cada `backup_minutes`, sem parar por `OSError`. O lifespan DEVE gravar um backup também no desligamento.
  Testes: `test_run_grava_backup_a_cada_intervalo`, `test_run_sobrevive_a_falha_de_disco`, `test_lifespan_inicia_e_para_o_fundo_e_faz_backup_na_saida`.
- **R2.4** QUANDO o arquivo do banco não existe na partida e há backup, `create_app` DEVE restaurar o mais recente antes de abrir o banco e registrar um aviso no log. Banco existente NUNCA DEVE ser sobrescrito na partida.
  Testes: `test_restaura_quando_banco_nao_existe`, `test_nao_restaura_se_banco_existe`, `test_nao_restaura_sem_backup`, `test_create_app_restaura_banco_ausente`.
- **R2.5** `python -m app.tools.restore_backup` DEVE listar os backups; com um arquivo, DEVE validá-lo (SQLite com a tabela `devices`), guardar o banco atual como `vinheria.db.antes-da-restauracao-<data>` e copiar o backup no lugar. Arquivo inválido DEVE ser recusado sem tocar no banco.
  Testes: `test_is_valid_backup`, `test_restore_substitui_e_guarda_o_atual`, `test_restore_recusa_arquivo_invalido`, `test_main_lista_backups`, `test_main_restaura_pelo_nome_do_arquivo`, `test_main_arquivo_invalido_devolve_erro`.

### R3 — Log de alertas (RF10)
- **R3.1** `AlertLog.open(device_id, attr, value, opened_at)` DEVE gravar e devolver o `Alert` com `id`; `close(alert_id, closed_at)` DEVE fechar só alerta aberto.
  Testes: `test_open_grava_e_devolve_alerta`, `test_close_fecha_e_calcula_duracao`, `test_close_duas_vezes_mantem_primeiro_fechamento`.
- **R3.2** `Alert.duration_seconds` DEVE ser `closed_at − opened_at` em segundos inteiros, `None` enquanto aberto. `attr` aceita `temperature`, `humidity`, `luminosity` e `offline`; o alerta `offline` tem `value` nulo. O alerta da EC2 usa `device_id = "fiware"` e `attr = "offline"`.
  Testes: `test_close_fecha_e_calcula_duracao`, `test_alerta_offline_sem_valor`.
- **R3.3** `open_alerts()` DEVE devolver só os abertos, por ordem de abertura. `list(device_id=None, limit=100)` DEVE devolver do mais novo para o mais velho, filtrado por vinheria quando pedido.
  Testes: `test_open_alerts_so_abertos`, `test_list_mais_novo_primeiro_e_filtra`.

### R4 — Faixa, conversão de entidade e atributo `configured`
- **R4.1** `LimitsStore.update(device_id, limits)` DEVE substituir as 3 linhas da faixa numa transação própria.
  Teste: `test_limits_update_substitui_faixa`.
- **R4.2** `limits_to_command_value(limits)` DEVE devolver `"tmin,tmax,hmin,hmax,lmin,lmax"`, sem `.0` em inteiros e com decimais quando houver.
  Testes: `test_command_value_padrao`, `test_command_value_com_decimais`.
- **R4.3** `reading_from_entity(device_id, entidade)` DEVE concentrar a conversão de uma entidade do Orion em `CurrentReading`, incluindo `configured`: `True` com valor 1, `False` com 0, `None` ausente ou inválido.
  Teste: `test_reading_from_entity_converte`.
- **R4.4** O provisionamento do device DEVE declarar o atributo `c` → `configured` (`Integer`), sem subscription do STH para ele.
  Teste: `test_provision_device_envia_body` (atualizado).

### R5 — Regras puras do motor
- **R5.1** `parse_instant` DEVE aceitar o `TimeInstant` do IoT Agent (`2026-10-08T11:59:58.000Z`), tratar sem fuso como UTC e devolver `None` para vazio ou inválido.
  Testes: `test_parse_instant_formatos`, `test_parse_instant_invalido`, `test_seconds_since`.
- **R5.2** `is_offline(last_seen, created_at, now, offline_seconds)` DEVE comparar a última leitura com o limite; sem leitura, DEVE usar o `created_at` do cadastro.
  Testes: `test_is_offline_pela_leitura`, `test_is_offline_sem_leitura_usa_cadastro`.
- **R5.3** Abertura: valor `> max` é lado `above`, `< min` é lado `below`; bordas são dentro da faixa. Fechamento com folga (histerese): só dentro da faixa e afastado `margem` da borda do lado violado; lado desconhecido fecha ao entrar na faixa. `margem = min(tabela[attr], 25 % da largura)`, tabela temperatura 0,5 · umidade 2 · luminosidade 2.
  Testes: `test_direction`, `test_hysteresis_margin_limitada_pela_largura`, `test_can_close_respeita_lado`.
- **R5.4** `command_plan(ativos)` DEVE devolver `alert_off` seguido de um `blink_*` por atributo ativo, na ordem luminosidade, umidade, temperatura (a temperatura por último define o padrão).
  Teste: `test_command_plan`.

### R6 — Alertas em memória e retrato da frota
- **R6.1** `AlertTracker` DEVE espelhar o `AlertLog`: abrir é idempotente por `(device_id, attr)`, fechar grava no log, `active(device_id)` devolve os ativos na ordem temperatura, umidade, luminosidade, offline, e `close_except(ids)` fecha os de quem não está na lista.
  Testes: `test_open_e_idempotente`, `test_close_fecha_no_log`, `test_active_em_ordem_canonica`, `test_close_except_fecha_quem_nao_esta`.
- **R6.2** `FleetState` DEVE guardar o último retrato (com `fiware_online`, `fiware_offline_since`, `updated_at`) e devolver `report(device_ids)` só com as vinherias pedidas, ordenadas por id.
  Testes: `test_fleet_comeca_vazio`, `test_fleet_snapshot_ordena_e_filtra`, `test_fleet_status_of`, `test_fleet_replace_troca_tudo`, `test_fleet_report`.

### R7 — Motor: alertas de sensor (RF07)
- **R7.1** Cada `tick()` DEVE fazer **uma** chamada `list_entities` para a frota inteira; sem vinherias, nenhuma.
  Testes: `test_uma_chamada_list_entities_por_ciclo`, `test_frota_vazia_nao_chama_fiware`.
- **R7.2** Atributo fora da faixa DEVE abrir exatamente um alerta e enviar o plano de comandos uma vez; o mesmo valor no ciclo seguinte NÃO DEVE reenviar nada.
  Testes: `test_acima_do_maximo_abre_alerta_e_envia_blink_uma_vez`, `test_abaixo_do_minimo_abre_alerta`.
- **R7.3** Volta à faixa (com folga) DEVE fechar o alerta e enviar `alert_off`.
  Testes: `test_volta_a_faixa_fecha_alerta_e_envia_alert_off`, `test_histerese_segura_alerta_perto_do_limite`, `test_histerese_so_vale_do_lado_violado`.
- **R7.4** Duas anomalias: o ESP32 DEVE ficar no padrão da temperatura e, quando uma normaliza, receber `alert_off` + o `blink` da que restou.
  Teste: `test_duas_anomalias_temperatura_por_ultimo`.
- **R7.5** Leitura ausente de um atributo NÃO DEVE abrir nem fechar alerta dele.
  Teste: `test_leitura_ausente_nao_muda_estado`.
- **R7.6** Anomalia numa vinheria NÃO DEVE afetar outra.
  Teste: `test_anomalia_numa_vinheria_nao_afeta_outra`.
- **R7.7** A faixa usada é a do SQLite no momento do ciclo.
  Teste: `test_faixa_nova_vale_no_proximo_ciclo`.
- **R7.8** O motor só manda o plano de alerta quando o conjunto ativo muda em relação ao último entregue (ou na ressincronização). Comando manual do painel não é desfeito no ciclo seguinte.
  Testes: `test_primeira_passada_sincroniza_faixa_e_desliga_alerta`, `test_segunda_passada_sem_mudanca_nao_envia_nada`.
- **R7.9** `mark_limits_pending(device_id)` DEVE fazer o próximo ciclo enviar `set_limits` com a faixa atual, uma vez.
  Teste: `test_faixa_pendente_envia_set_limits`.
- **R7.10** Cada ciclo DEVE publicar um `VinheriaStatus` por vinheria: status `ok`/`alerta`/`offline`/`configurando`, `offline_reason`, `last_seen`, `seconds_since`, valores atuais, `score` (nulo se offline ou sem leitura completa) e alertas ativos.
  Teste: `test_retrato_da_frota_tem_valores_score_e_alertas`.

### R8 — Motor: configuração do ESP32 (pedido do usuário)
- **R8.1** QUANDO a vinheria está online e `configured` não é `True` (0 ou ausente), o motor DEVE enviar `set_limits` no mesmo ciclo, repetir a cada ciclo até o ESP32 responder `c=1`, NÃO DEVE avaliar nem abrir alertas de sensor e DEVE mostrar status `configurando`.
  Testes: `test_sem_configuracao_recebe_faixa_na_hora_e_nao_avalia`, `test_configured_ausente_conta_como_nao_configurado`.
- **R8.2** Depois de configurado, o motor DEVE mandar o plano de alerta do conjunto ativo, sem reenviar a faixa.
  Teste: `test_apos_configurar_sincroniza_alerta_sem_reenviar_faixa`.
- **R8.3** ESP32 que reinicia com alerta aberto DEVE receber primeiro a faixa e, depois de confirmar, o plano de alerta; o alerta continua o mesmo (não duplica).
  Teste: `test_reinicio_do_esp32_reenvia_faixa_e_depois_o_alerta`.
- **R8.4** Falha ao enviar a faixa DEVE ser repetida no ciclo seguinte.
  Teste: `test_falha_ao_enviar_faixa_tenta_no_proximo_ciclo`.

### R9 — Motor: vinheria offline e falhas (RF13)
- **R9.1** Vinheria sem leitura há mais de `offline_seconds` DEVE abrir um alerta `offline` (um só), ficar `offline` com `offline_reason = "sem_leitura"` e NÃO receber comando. Alertas de sensor abertos ficam como estão.
  Teste: `test_sem_leitura_ha_mais_de_offline_seconds_abre_alerta_offline_sem_comando`.
- **R9.2** Na volta, o alerta `offline` DEVE fechar e o ESP32 DEVE ser ressincronizado (faixa + plano de alerta).
  Testes: `test_volta_do_offline_fecha_alerta_e_ressincroniza`, `test_volta_do_offline_com_anomalia_reenvia_blink`.
- **R9.3** Vinheria recém-cadastrada e sem leitura NÃO DEVE ficar offline antes de `offline_seconds` depois do cadastro; vinheria antiga sem entidade DEVE ficar offline.
  Testes: `test_vinheria_recem_cadastrada_sem_leitura_fica_configurando_ate_o_limite`, `test_vinheria_antiga_sem_entidade_fica_offline`.
- **R9.4** Falha de comando: o alerta continua aberto (um só) e o envio é repetido no ciclo seguinte.
  Teste: `test_falha_no_comando_tenta_de_novo_no_proximo_ciclo`.
- **R9.5** Alertas abertos no SQLite DEVEM ser retomados na primeira passada, sem duplicar, e fechados normalmente.
  Testes: `test_alertas_abertos_sao_retomados_apos_reinicio`, `test_alerta_retomado_fecha_quando_volta_a_faixa`.
- **R9.6** Vinheria removida com alerta aberto DEVE ter o alerta fechado no ciclo seguinte e sair do retrato.
  Teste: `test_vinheria_removida_tem_alertas_fechados`.
- **R9.7** `run()` DEVE repetir `tick()` com espera de `poll_seconds` (lido a cada volta) e sobreviver a exceção num ciclo.
  Teste: `test_run_repete_tick_e_sobrevive_a_erro`.

### R10 — Motor: EC2/FIWARE fora do ar (pedido do usuário)
- **R10.1** QUANDO `list_entities` falha há até `offline_seconds`, o ciclo NÃO DEVE mudar nada (retrato, alertas, comandos); só registra aviso no log.
  Teste: `test_falha_curta_do_fiware_mantem_retrato`.
- **R10.2** QUANDO a falha passa de `offline_seconds`, o motor DEVE abrir **um** alerta `device_id="fiware"`, `attr="offline"`, com início no momento da primeira falha, publicar `fiware_online = false` e marcar **todas** as vinherias como `offline` com `offline_reason = "fiware"` (últimos valores conhecidos, score nulo), sem abrir alertas `offline` por vinheria.
  Teste: `test_ec2_fora_marca_offline_com_um_alerta`.
- **R10.3** Na volta da EC2, o alerta `fiware` DEVE fechar e todos os ESP32 DEVEM ser ressincronizados.
  Teste: `test_ec2_volta_fecha_alerta_e_ressincroniza`.
- **R10.4** Logo depois da volta, as vinherias ainda com leitura velha (os ESP32 reconectando ao Mosquitto) DEVEM aparecer `offline` (`sem_leitura`), mas o alerta `offline` por vinheria só DEVE abrir se a leitura não chegar em `offline_seconds` depois da volta.
  Teste: `test_leitura_velha_logo_apos_a_volta_nao_abre_offline`.
- **R10.5** Alerta `fiware` aberto retomado após reinício do backend DEVE fechar quando o FIWARE responder.
  Teste: `test_alerta_da_ec2_retomado_apos_reinicio_fecha_quando_volta`.

### R11 — Controle da vinheria: faixa e comandos manuais (RF06, RF09)
- **R11.1** `DeviceControl.update_limits(device_id, limits)` DEVE, nesta ordem: validar o cadastro (`DeviceNotFound` sem rede), publicar `temp_min`…`lux_max` no Orion, gravar no SQLite e **enviar o `set_limits` na hora** se a vinheria não está offline. Devolve `LimitsUpdate` com `device_sync = "enviado"`.
  Teste: `test_update_limits_publica_grava_e_envia_na_hora`.
- **R11.2** Vinheria offline, ou falha no envio: a faixa fica gravada, o motor é avisado (`mark_limits_pending`) e a resposta traz `device_sync = "pendente"`.
  Testes: `test_update_limits_offline_fica_pendente`, `test_update_limits_falha_no_envio_fica_pendente`.
- **R11.3** QUANDO o Orion falha ao gravar a faixa, `update_limits` DEVE propagar o `FiwareError`, sem gravar no SQLite e sem enviar.
  Testes: `test_update_limits_fiware_fora_nao_grava`, `test_update_limits_inexistente_sem_rede`.
- **R11.4** `send_command(device_id, command)` DEVE enviar `blink_temp`, `blink_hum`, `blink_lux` ou `alert_off`. Vinheria `offline` ou `configurando` DEVE levantar `DeviceUnavailable` sem enviar.
  Testes: `test_send_command_envia`, `test_send_command_offline_recusa`, `test_send_command_configurando_recusa`, `test_send_command_inexistente_sem_rede`.
- **R11.5** `get_limits(device_id)` DEVE devolver a faixa ou levantar `DeviceNotFound`.
  Testes: `test_get_limits`, `test_get_limits_inexistente`.

### R12 — API
- **R12.1** As rotas da seção 4.4 DEVEM responder com os status indicados lá.
  Testes: `test_get_triggers_200`, `test_get_triggers_404`, `test_put_triggers_200`, `test_put_triggers_min_maior_que_max_422`, `test_put_triggers_fiware_fora_503`, `test_post_command_202`, `test_post_command_invalido_422`, `test_post_command_indisponivel_409`, `test_get_alerts_lista_e_filtra`, `test_get_alerts_limit_invalido_422`, `test_get_fleet_so_vinherias_cadastradas`, `test_get_fleet_ec2_offline`.
- **R12.2** `DeviceUnavailable` DEVE sair como 409 no formato `{detail, service: "registry"}`.
  Teste: `test_post_command_indisponivel_409`.

### R13 — Montagem
- **R13.1** Com `run_background` ligado, o lifespan DEVE iniciar `TriggerEngine.run()` e `BackupService.run()` (este só com backup ligado) e, no desligamento, cancelá-los, gravar o backup final e fechar HTTP e banco. Com `run_background` desligado, nada roda em fundo.
  Testes: `test_lifespan_inicia_e_para_o_fundo_e_faz_backup_na_saida`, `test_sem_run_background_nao_inicia_poller`.

### R14 — Firmware (RF08, RF19; absorve a antiga Task 4B)
- **R14.1** O ESP32 DEVE nascer **sem faixa** (`configurado = false`) e, enquanto não receber um `set_limits` válido, mostrar no LCD "Configure o" / "dispositivo" com pontos animados (ou "Conectando" / `ID_DEVICE` sem MQTT), sem o carrossel.
- **R14.2** O `set_limits` DEVE aceitar `"tmin,tmax,hmin,hmax,lmin,lmax"` com decimais opcionais, exigir exatamente 6 números e `min < max` em cada par, e só então aplicar (validação atômica). Inválido: ack `erro` e nada muda.
- **R14.3** Na primeira faixa válida, o LCD DEVE mostrar "Configurado!" e seguir para o carrossel; a faixa aparece nas telas de temperatura, umidade e luz (inteiro sem casas, decimal com 1 casa).
- **R14.4** Enquanto não configurado, `blink_temp`, `blink_hum` e `blink_lux` DEVEM ser recusados (ack `erro`, nada toca); `alert_off` é sempre aceito.
- **R14.5** A telemetria DEVE incluir `c|0` ou `c|1` (`t|<t>|h|<h>|l|<l>|c|<c>`).
- **R14.6** As funções de parse e impressão da faixa DEVEM ficar em `firmware/limites.h`, sem depender de variáveis globais do `.ino`.

Verificação: no Wokwi (subtarefa 4.15), não há teste automatizado de firmware.

## 4. Detalhes técnicos (design)

### 4.1 Estrutura de arquivos

```
firmware/
├── limites.h                    # novo: struct Faixa, parseDecimal, parseFaixa, imprimirLimite
└── vinheria_full.ino            # configurado, tela de configuração, blink recusado, c na telemetria
backend/app/
├── core/
│   ├── db.py                    # + Result, Database (RLock); connect() devolve Database
│   ├── config.py                # + backup_dir, backup_minutes, backup_keep, run_background; tipo Database
│   └── backup.py                # novo: list_backups, restore_if_missing, BackupService
├── tools/
│   ├── __init__.py              # novo
│   └── restore_backup.py        # novo: CLI de listar/restaurar backup
├── models/
│   ├── schemas.py               # CurrentReading ganha configured
│   └── schemas_fleet.py         # novo: Alert, ActiveAlert, SensorValues, VinheriaStatus, FleetReport,
│                                #   LimitsUpdate, CommandRequest, CommandResult, FIWARE_ALERT_ID
├── services/
│   ├── fiware_constants.py      # + STATUS_ATTRS (c → configured)
│   ├── fiware_iota.py           # provisiona também STATUS_ATTRS
│   ├── limits.py                # + LimitsStore.update, limits_to_command_value; tipo Database
│   ├── readings.py              # + reading_from_entity (com configured)
│   ├── device_registry.py       # tipo Database (só anotação)
│   ├── registry_errors.py       # + DeviceUnavailable
│   ├── alert_log.py             # novo: AlertLog
│   ├── alert_tracker.py         # novo: AlertTracker (alertas abertos em memória)
│   ├── trigger_rules.py         # novo: funções puras do motor
│   ├── fleet_state.py           # novo: FleetState
│   ├── trigger_engine.py        # novo: TriggerEngine
│   └── device_control.py        # novo: DeviceControl
├── api/
│   ├── deps.py                  # + get_alert_log, get_fleet, get_control
│   ├── errors.py                # DeviceUnavailable → 409
│   ├── routes_triggers.py       # novo: GET/PUT triggers, POST commands
│   ├── routes_alerts.py         # novo: GET /api/alerts
│   └── routes_fleet.py          # novo: GET /api/fleet
└── main.py                      # monta tudo; restaura banco ausente; lifespan com tarefas de fundo
backend/.env.example             # + BACKUP_DIR, BACKUP_MINUTES, BACKUP_KEEP
backend/tests/
├── fakes.py                     # novo: FiwareFalso, Relogio, entidade(), instante_de(), status_vinheria()
├── conftest.py                  # + created_at no cadastrar; fixtures alert_log, fleet, fiware_falso, relogio, engine
├── test_db_concurrency.py       # R1
├── test_config.py               # R2.1
├── test_backup.py               # R2.2–R2.4
├── test_restore_backup.py       # R2.5
├── test_alert_log.py            # R3
├── test_limits.py, test_readings.py, test_fiware_iota.py   # R4
├── test_trigger_rules.py        # R5
├── test_alert_tracker.py, test_fleet.py                     # R6
├── test_trigger_engine.py       # R7
├── test_trigger_config.py       # R8
├── test_trigger_offline.py      # R9
├── test_trigger_fiware.py       # R10
├── test_device_control.py       # R11
├── test_routes_control.py       # R12
└── test_lifespan.py             # R13 (+ R2.3, R2.4)
```

Nenhum arquivo novo passa de ~250 linhas. O `.ino` já passa (era assim antes desta task); o que é novo vai para `limites.h`.

### 4.2 Contratos públicos

```python
# app/core/db.py
class Result:          # fetchone(), fetchall(), __iter__, rowcount, lastrowid
class Database:        # execute(sql, params=()) -> Result; with db: (transação sob RLock); backup_to(destino); close()
def connect(path: str) -> Database

# app/core/backup.py
def list_backups(backup_dir: Path) -> list[Path]                       # mais novo primeiro
def restore_if_missing(database_path: str, backup_dir: str) -> Path | None
class BackupService:   # (db, backup_dir, keep, minutes, clock=datetime.now, sleep=asyncio.sleep)
                       # enabled; backup_now() -> Path | None; async run()

# app/tools/restore_backup.py
def is_valid_backup(path: Path) -> bool
def restore(backup: Path, database_path: Path, clock=datetime.now) -> Path | None
def main(argv: list[str] | None = None, settings: Settings | None = None) -> int

# app/models/schemas.py
class CurrentReading(BaseModel):   # + configured: bool | None = None

# app/models/schemas_fleet.py
FIWARE_ALERT_ID = "fiware"
AlertAttr = Literal["temperature", "humidity", "luminosity", "offline"]
FleetStatus = Literal["ok", "alerta", "offline", "configurando"]
OfflineReason = Literal["sem_leitura", "fiware"]
ManualCommand = Literal["blink_temp", "blink_hum", "blink_lux", "alert_off"]
class Alert(BaseModel):          # id, device_id, attr, value, opened_at, closed_at, duration_seconds
class ActiveAlert(BaseModel):    # attr, value, since
class SensorValues(BaseModel):   # temperature, humidity, luminosity
class VinheriaStatus(BaseModel): # device_id, name, city, status, offline_reason, last_seen, seconds_since,
                                 # current, score, active_alerts
class FleetReport(BaseModel):    # fiware_online, fiware_offline_since, updated_at, vinherias
class LimitsUpdate(BaseModel):   # device_id, limits, device_sync: "enviado" | "pendente"
class CommandRequest(BaseModel): # command: ManualCommand
class CommandResult(BaseModel):  # device_id, command

# app/services/fiware_constants.py
STATUS_ATTRS = (("c", "configured", "Integer"),)

# app/services/alert_log.py
class AlertLog:   # (db) open(device_id, attr, value, opened_at) -> Alert; close(alert_id, closed_at);
                  # open_alerts() -> list[Alert]; list(device_id=None, limit=100) -> list[Alert]

# app/services/limits.py
def limits_to_command_value(limits: Limits) -> str
class LimitsStore:  # + update(device_id, limits) -> None (transação própria)

# app/services/readings.py
def reading_from_entity(device_id: str, entidade: dict) -> CurrentReading

# app/services/trigger_rules.py
SENSOR_ORDER, BLINK_COMMANDS, SEND_ORDER, DEFAULT_HYSTERESIS, MAX_HYSTERESIS_FRACTION
def parse_instant(texto) -> datetime | None
def seconds_since(reference, now) -> int | None
def is_offline(last_seen, created_at, now, offline_seconds) -> bool
def direction(value, lo, hi) -> str | None
def hysteresis_margin(attr, lo, hi, table=DEFAULT_HYSTERESIS) -> float
def can_close(value, lo, hi, side, margin) -> bool
def command_plan(active) -> list[str]

# app/services/alert_tracker.py
OFFLINE = "offline"; ORDEM_ALERTAS
class OpenAlert:      # alert_id, side, value, since
class AlertTracker:   # (alerts) load() -> list[Alert]; get(device_id, attr); open(device_id, attr, value, side, when);
                      # close(device_id, attr, when); close_except(keep: set[str], when);
                      # active(device_id) -> list[ActiveAlert]; active_sensors(device_id) -> frozenset[str]

# app/services/fleet_state.py
class FleetState:     # updated_at, fiware_online, fiware_offline_since
                      # replace(statuses, at, fiware_online=True, fiware_offline_since=None)
                      # snapshot(device_ids=None); get(device_id); status_of(device_id); report(device_ids) -> FleetReport

# app/services/trigger_engine.py
class TriggerEngine:  # (registry, limits, alerts, fiware, config, fleet, clock=..., sleep=asyncio.sleep, hysteresis=None)
                      # mark_limits_pending(device_id); async tick(); async run()

# app/services/device_control.py
class DeviceControl:  # (registry, limits, fiware, fleet, engine)
                      # get_limits(device_id) -> Limits; async update_limits(device_id, limits) -> LimitsUpdate;
                      # async send_command(device_id, command) -> None

# app/services/registry_errors.py
class DeviceUnavailable(RegistryError)
```

### 4.3 Ciclo do motor (`tick`)

1. Na primeira passada, retoma os alertas abertos do SQLite. Se um deles é o da EC2, o motor começa considerando a EC2 fora.
2. `registry.list()`; fecha os alertas de vinherias que não estão mais cadastradas (exceto o da EC2).
3. Sem vinherias: retrato vazio e fim, sem chamada ao FIWARE.
4. `list_entities()` uma vez.
   - **Falha:** guarda o instante da primeira falha. Até `offline_seconds`, não muda nada. Passando disso: abre o alerta `fiware` (início = primeira falha), esquece o que foi entregue a cada ESP32 e publica todas as vinherias `offline` (`fiware`). Fim do ciclo.
   - **Sucesso depois de EC2 fora:** fecha o alerta `fiware` e abre uma carência de `offline_seconds` para alertas `offline` por vinheria.
5. Para cada vinheria, com a entidade dela (ou `{}`):
   - **offline** (`is_offline`): abre o alerta `offline` (fora da carência), esquece o que foi entregue ao ESP32 e não manda nada;
   - **online sem `configured = True`:** fecha o alerta `offline`, envia `set_limits` agora e não avalia sensores (status `configurando`);
   - **online e configurado:** fecha o alerta `offline`; abre ou fecha os alertas de sensor (com folga); envia `set_limits` se a faixa não chegou a esse ESP32 (partida, volta ou faixa pendente) e o plano de alerta se o conjunto ativo mudou;
   - falha de comando: aviso no log, tenta de novo no ciclo seguinte;
   - monta o `VinheriaStatus`.
6. Publica o retrato com o estado da EC2.

Estado do motor, só em memória: alertas abertos (no `AlertTracker`), último conjunto entregue por ESP32, conjunto de ESP32 que já têm a faixa atual, instante da primeira falha da EC2, EC2 fora (sim/não) e instante da volta. O SQLite guarda os alertas; o resto se refaz pela ressincronização.

### 4.4 API

| Rota | Entrada | Sucesso | Erros |
|---|---|---|---|
| `GET /api/devices/{device_id}/triggers` | — | 200 `Limits` | 404 |
| `PUT /api/devices/{device_id}/triggers` | JSON `Limits` | 200 `LimitsUpdate` | 422 (min ≥ max, campo faltando) · 404 · 503/502 |
| `POST /api/devices/{device_id}/commands` | JSON `CommandRequest` | 202 `CommandResult` | 422 (comando fora da lista, inclusive `set_limits`) · 404 · 409 (offline ou configurando) · 503/502 |
| `GET /api/alerts` | query `device_id?` (inclusive `fiware`), `limit` 1–500 (padrão 100) | 200 `[Alert]` | 422 |
| `GET /api/fleet` | — | 200 `FleetReport` (só vinherias cadastradas, por id) | — |

Exemplo de `GET /api/fleet` com a EC2 fora:

```json
{ "fiware_online": false, "fiware_offline_since": "2026-10-20T14:03:11+00:00",
  "updated_at": "2026-10-20T14:03:45+00:00",
  "vinherias": [{ "device_id": "vinheria001", "name": "Vinheria Paulista", "city": "São Paulo",
                  "status": "offline", "offline_reason": "fiware", "last_seen": "2026-10-20T14:03:09.000Z",
                  "seconds_since": 36, "current": { "temperature": 14.2, "humidity": 62, "luminosity": 20 },
                  "score": null, "active_alerts": [] }] }
```

### 4.5 Decisões de design

| # | Decisão | Motivo |
|---|---|---|
| D1 | `Database` com `RLock` em volta de cada transação e de cada `execute`. | Decisão do usuário (aviso 1). Defeito reproduzido e correção provada em protótipo (F2). |
| D2 | Backup a cada 10 min e no desligamento, em `~/SmartSolutions/backups` (configurável), 20 mantidos. Restauração automática só quando o banco não existe; manual por CLI. | Decisão do usuário (aviso 2). Nunca sobrescreve um banco existente sozinho. |
| D3 | `Settings` direto (testes) desliga backup e tarefas de fundo; `load_settings()` liga. | Teste nenhum grava na pasta do usuário nem sobe o poller contra a rede. |
| D4 | Plano de comandos = `alert_off` + `blink_*` dos ativos, temperatura por último. | F4; confirmado pelo usuário em 09/10. |
| D5 | O plano de alerta só sai quando o conjunto ativo muda ou na ressincronização. | Não reenvia a cada 5 s e não desfaz o comando manual (RF09). Um `alert_off` manual silencia o ESP32 até o conjunto mudar. |
| D6 | Folga (histerese) só no fechamento e só do lado violado, até 25 % da largura. | Confirmado pelo usuário em 09/10. Evita o buzzer tremendo na borda; do lado oposto não há folga, senão a adega escura nunca fecharia um alerta de luz alta. |
| D7 | Alerta retomado após reinício tem lado desconhecido e fecha ao entrar na faixa. | Guardar o lado exigiria mudar o schema por pouco ganho. |
| D8 | ESP32 nasce sem faixa e publica `c` (0/1). O backend envia `set_limits` no mesmo ciclo em que vê `c≠1`, sem avaliar alertas até `c=1`; o firmware recusa `blink_*` antes disso. | Pedido do usuário: nenhum parâmetro não cadastrado funciona e nenhum alerta dispara sozinho ao ligar. F5: o ciclo do poller (até 5 s) é o mais rápido possível sem a EC2 alcançar o notebook. |
| D9 | `configured` ausente conta como não configurado. | Firmware antigo (sem `c`) nunca recebe alertas; obriga a atualizar o firmware das 5 instâncias. |
| D10 | `PUT /triggers` envia o `set_limits` na hora; offline ou falha deixa pendente para o motor. | Pedido do usuário ("enviar na hora"). |
| D11 | EC2 sem resposta por mais de `offline_seconds`: um alerta `fiware`, todas as vinherias `offline` (`fiware`) no painel, sem alertas por vinheria. Na volta, carência de `offline_seconds` para alertas `offline` por vinheria. | Decisão do usuário. A carência evita 5 alertas falsos enquanto os ESP32 reconectam ao Mosquitto. Falha curta (até 30 s) não mexe em nada, para um timeout isolado não piscar a frota inteira. |
| D12 | Score nulo enquanto offline; calculado em `configurando` (a faixa é a do cadastro). | Valor antigo não gera nota. |
| D13 | RF09 = `POST /api/devices/{id}/commands`, sem `set_limits`; 409 se offline ou configurando. | Decisão do usuário. A faixa só sai pelo `PUT /triggers`. |
| D14 | O atributo `c` exige reprovisionar a 001 e a 002 (remover e cadastrar de novo com o mesmo nome e cidade). | O IoT Agent só mapeia `c → configured` em device provisionado com ele. Antes da Task 4 não há faixa editada nem alertas a perder. |
| D15 | Alertas abertos em memória ficam no `AlertTracker`, separados do motor. | Mantém o `trigger_engine.py` abaixo de ~250 linhas. |

### 4.6 Fora de escopo

- Front (barra, cards, toasts, painel de faixa, timeline): Tasks 5 e 6.
- Exportar e importar o banco por API (JSON).
- Guardar o lado violado no SQLite (D7).
- Avisar o backend por push (subscription do Orion para o notebook): impossível sem expor o notebook (F5).

## 5. Ferramentas e requisitos

- Nenhuma dependência nova no backend nem no firmware.
- Testes sem rede: fakes para o FIWARE no motor e no controle, `respx` onde já era usado, SQLite em `tmp_path`.
- Variáveis novas no `.env` (opcionais): `BACKUP_DIR`, `BACKUP_MINUTES`, `BACKUP_KEEP`.
- Firmware: o projeto do Wokwi precisa ganhar o arquivo `limites.h` (botão "+" ao lado das abas), em todas as instâncias que forem usadas.
- Verificação real (4.15 e 4.16): EC2 ligada, Wokwi da 001 e da 002 com o firmware novo, sensores dentro da faixa padrão no início (temperatura ~15 °C, umidade ~60 %, luminosidade ≤ 30 %).

## 6. Como verificar (aceite da task)

1. `cd backend && .venv/Scripts/python -m pytest -q` passa inteiro, sem rede.
2. O Swagger (`/docs`) mostra as 5 rotas novas da seção 4.4.
3. Wokwi com o firmware novo e o backend parado: o LCD mostra "Configure o dispositivo" e não sai disso; um `blink_temp` enviado pelo Orion é recusado (ack `erro`); um `set_limits` com `"12.5,18,50,70,0,30"` mostra "Configurado!" e depois `Ideal 12.5-18C`.
4. Com a 001 e a 002 recadastradas e o backend subido: ao reiniciar um Wokwi, o LCD mostra "Configure o dispositivo" e passa ao carrossel em até ~5 s depois da primeira leitura, sem nenhum alerta disparar sozinho.
5. `PUT` de faixa da 002 com `temperature.max` abaixo da temperatura atual: resposta `device_sync: "enviado"`, a faixa nova aparece no LCD dela na hora, e em até ~5 s ela pisca e apita no padrão de temperatura; a 001 não reage; `GET /api/fleet` e `GET /api/alerts` refletem isso. `PUT` de volta: para e o alerta fecha com duração.
6. `POST .../vinheria001/commands` com `blink_hum`: o bipe longo continua por pelo menos 3 ciclos; `alert_off` para.
7. Parar o Wokwi da 002: em até ~35 s, `offline` (`sem_leitura`) com alerta e 409 em comandos. Religar: "Configure o dispositivo", depois `ok`, alerta fechado.
8. EC2 fora, simulada sem desligar a EC2 de verdade: `PUT /api/config` com um IP inexistente (`10.255.255.1`), que faz o backend perder o FIWARE enquanto os ESP32 seguem ligados: em até ~40 s, `fiware_online: false`, todas as vinherias `offline` (`fiware`) e um alerta `fiware`. Voltar o IP: o alerta `fiware` fecha e as vinherias voltam a `ok`.
9. Ctrl+C no backend grava um `vinheria-*.db` em `BACKUP_DIR`; renomeando o banco e subindo de novo, ele é restaurado com a 001 e a 002.
10. `git status` não mostra `.env`, `*.db` nem backups.
