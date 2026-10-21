"""
Chatbot multi-vinheria (Task 7A) com Google Gemini e function calling.

A cada pergunta, o backend acrescenta uma linha com a situação da frota
(para o bot avisar sozinho de vinheria em alerta ou offline), manda ao
Gemini a conversa e as declarações das tools e executa as tools que ele
pedir, até a resposta final ou o limite de chamadas. Nada é executado no
FIWARE por aqui: as ações viram propostas que o painel confirma.
"""
from datetime import tzinfo

from app.models.schemas_fleet import FleetReport
from app.services.chat_stats import NOME_ATRIBUTO, hora_local


def resumo_frota(report: FleetReport, fuso: tzinfo | None = None) -> str:
    """Uma linha em português com a situação da EC2 e das vinherias com problema."""
    if not report.fiware_online:
        desde = (f" desde {hora_local(report.fiware_offline_since, fuso)}"
                 if report.fiware_offline_since else "")
        return (f"Situação agora: FIWARE fora do ar{desde}; "
                "os dados das vinherias podem estar desatualizados.")
    total = len(report.vinherias)
    if total == 0:
        return "Situação agora: FIWARE ok; nenhuma vinheria cadastrada."
    problemas = []
    for status in report.vinherias:
        rotulo = f"{status.device_id} ({status.name})"
        if status.status == "alerta":
            atributos = ", ".join(NOME_ATRIBUTO.get(a.attr, a.attr) for a in status.active_alerts)
            problemas.append(f"{rotulo} em alerta de {atributos or 'faixa'}")
        elif status.status == "offline":
            problemas.append(f"{rotulo} offline")
        elif status.status == "configurando":
            problemas.append(f"{rotulo} aguardando a faixa (configurando)")
    plural = "vinheria" if total == 1 else "vinherias"
    if not problemas:
        return f"Situação agora: FIWARE ok; {total} {plural}, todas normais."
    return f"Situação agora: FIWARE ok; {total} {plural}; " + "; ".join(problemas) + "."
