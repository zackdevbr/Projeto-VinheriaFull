# Roteiro do pitch — Smart Solutions

Duração alvo: 5 a 7 minutos (total planejado: 6:15). Preencher o nome de quem fala em cada bloco.

| Tempo | Bloco | Quem fala | O que mostrar e dizer |
|---|---|---|---|
| 0:00 – 0:45 | Problema | _______ | Vinho é sensível a temperatura, umidade e luz. Em uma rede de lojas, ninguém vigia cada adega o tempo todo e o problema aparece quando o estoque já foi afetado. |
| 0:45 – 1:45 | Arquitetura em camadas | _______ | Mostrar o diagrama de `docs/arquitetura.md`: ESP32 → MQTT → IoT Agent → Orion → STH-Comet → backend → painel. Explicar que o comando de alerta faz o caminho inverso. |
| 1:45 – 4:15 | Demo ao vivo com 5 vinherias | _______ | 1) Visão geral com as 5 vinherias e seus status. 2) Baixar o limite máximo de temperatura só da `vinheria002`. 3) LED vermelho e buzzer reagem no ESP32. 4) Banner e toast aparecem no painel. 5) Subir o limite de volta; LED volta ao verde. 6) Parar um Wokwi e mostrar a vinheria ficando offline. |
| 4:15 – 5:15 | Chatbot | _______ | Fazer as três perguntas das sugestões do chat. O bot responde com os dados reais de cada vinheria. |
| 5:15 – 6:00 | Diferenciais | _______ | Score de qualidade de 0 a 100, histórico de alertas, troca do IP da EC2 em runtime pelo painel Avançado, cadastro de qualquer número de vinherias. |
| 6:00 – 6:15 | Encerramento | _______ | Resumo em uma frase e agradecimento. |

## Checklist de preparação

- [ ] EC2 ligada, containers de pé (`docker ps`) e IP elástico conferido no painel Avançado.
- [ ] Backend e front-end rodando; visão geral mostra FIWARE saudável.
- [ ] 4 abas do Wokwi abertas (`vinheria002` a `vinheria005`), cada uma com seu `ID_DEVICE`, e Start dado em todas.
- [ ] ESP32 físico (`vinheria001`) ligado e com LED verde.
- [ ] As 5 vinherias cadastradas no painel e online antes de começar.
- [ ] Faixa ideal da `vinheria002` anotada, para voltar ao valor original depois da demo.
- [ ] Chat ensaiado alguns minutos antes, sem exagero: o plano gratuito do Gemini tem cota diária baixa.
- [ ] Vídeo e Wokwi com link público funcionando.
