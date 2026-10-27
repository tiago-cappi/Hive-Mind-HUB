"""Testes estaticos do front (index.html) para o eixo de esforco (F2/ISS-001)
e o modal de composicao (F1/ISS-003).

Nao ha runtime JS no ambiente de teste (sem browser/jsdom) — estes testes
verificam por regex a presenca e a forma exata do markup/JS que o PRD exige:
mesmas opcoes de esforco no rodape e no modal, `currentEffort()` normalizando
para o conjunto permitido, e os handlers do modal (abrir/fechar/enviar/ESC)
usando os ids do contrato.

Rodar:  python -m pytest tests/test_frontend_static.py -q
"""
import re
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "index.html"
SRC = HTML.read_text(encoding="utf-8")

EFFORT_OPTIONS = [
    ("", "PADRÃO"), ("low", "LOW"), ("medium", "MEDIUM"),
    ("high", "HIGH"), ("xhigh", "XHIGH"), ("max", "MAX"),
]


def _select_block(select_id):
    m = re.search(
        r'<select id="%s"[^>]*>(.*?)</select>' % re.escape(select_id), SRC, re.S)
    assert m, f"select#{select_id} nao encontrado em index.html"
    return m.group(1)


def _option_values(block):
    return re.findall(r'<option(?:\s+value="([^"]*)")?', block)


# --------------------------- F2 / ISS-001 -----------------------------------
def test_effort_dropdown_rodape_tem_as_opcoes_reais_do_cli():
    block = _select_block("effort")
    vals = _option_values(block)
    assert vals == [v for v, _ in EFFORT_OPTIONS]


def test_effort_dropdown_modal_tem_as_mesmas_opcoes_do_rodape():
    rodape = _option_values(_select_block("effort"))
    modal = _option_values(_select_block("modalEffort"))
    assert rodape == modal


def test_effort_dropdown_labels_em_maiusculas():
    block = _select_block("effort")
    labels = re.findall(r'<option[^>]*>([^<]*)</option>', block)
    assert labels == [lbl for _, lbl in EFFORT_OPTIONS]


def test_current_effort_normaliza_e_restringe_ao_conjunto_permitido():
    m = re.search(r'function currentEffort\([^\n]*\)\{(.*?)\n\}', SRC, re.S)
    assert m, "currentEffort() nao encontrada"
    body = m.group(1)
    assert "toLowerCase" in body
    assert re.search(r"\[\s*'low'\s*,\s*'medium'\s*,\s*'high'\s*,\s*'xhigh'\s*,\s*'max'\s*\]", body)
    assert "els.effort.value" in body


def test_ask_e_session_routes_enviam_esforco_no_corpo():
    for route in ("/ask", "/session_start", "/session_reset"):
        assert re.search(
            r"fetch\('%s'.*?esforco:\s*currentEffort\(\)" % re.escape(route), SRC, re.S), \
            f"{route} nao envia esforco:currentEffort() no corpo"


# --------------------------- F1 / ISS-003 ------------------------------------
def test_text_input_focus_abre_modal():
    assert "els.textInput.addEventListener('focus', openTextModal)" in SRC


def test_modal_enter_envia_shift_enter_quebra_linha_esc_fecha():
    m = re.search(r"els\.modalTextInput\.addEventListener\('keydown', \(e\) => \{(.*?)\}\);", SRC, re.S)
    assert m, "handler de keydown do modal nao encontrado"
    body = m.group(1)
    assert "Enter" in body and "!e.shiftKey" in body and "modalSend.click" in body
    assert "Escape" in body and "closeTextModal(true)" in body


def test_modal_close_e_backdrop_fecham_sincronizando_sem_enviar():
    assert "els.modalClose.addEventListener('click', () => closeTextModal(true))" in SRC
    m = re.search(r"els\.modalOverlay\.addEventListener\('click', \(e\) => \{(.*?)\}\);", SRC)
    assert m and "closeTextModal(true)" in m.group(1) and "e.target === els.modalOverlay" in m.group(1)


def test_modal_send_copia_selecoes_e_dispara_um_unico_send_prompt():
    m = re.search(r"els\.modalSend\.addEventListener\('click', \(\) => \{(.*?)\}\);", SRC, re.S)
    assert m, "handler de click do modalSend nao encontrado"
    body = m.group(1)
    assert "els.model.value = els.modalModel.value" in body
    assert "els.effort.value = els.modalEffort.value" in body
    assert "sendTextPrompt(v)" in body


def test_open_text_modal_herda_texto_modelo_e_esforco_do_rodape():
    m = re.search(r"function openTextModal\(\)\{(.*?)\n\}", SRC, re.S)
    assert m, "openTextModal() nao encontrada"
    body = m.group(1)
    assert "els.modalModel.value = els.model.value" in body
    assert "els.modalEffort.value = els.effort.value" in body
    assert "els.modalTextInput.value = els.textInput.value" in body


def test_teclado_global_nao_intercepta_com_modal_aberto():
    m = re.search(r"document\.addEventListener\('keydown', \(e\) => \{(.*?)\n\}\);", SRC, re.S)
    assert m, "handler global de teclado nao encontrado"
    body = m.group(1)
    assert "!els.modalOverlay.hidden" in body


def test_send_text_prompt_guarda_contra_texto_vazio():
    m = re.search(r"function sendTextPrompt\(v\)\{(.*?)\n\}", SRC, re.S)
    assert m, "sendTextPrompt() nao encontrada"
    body = m.group(1)
    assert "if (!v) return;" in body
    assert "v = (v || '').trim();" in body


# --------------------------- F6: aba ALTERACOES -----------------------------
def test_aba_alteracoes_existe_com_painel_proprio():
    assert '<button class="tab" data-tab="chg">ALTERAÇÕES</button>' in SRC
    assert '<div id="chg" hidden></div>' in SRC
    assert "#chg[hidden]" in SRC          # [hidden] vence o display:flex do painel


def test_troca_de_aba_esconde_e_mostra_o_painel_de_alteracoes():
    m = re.search(r"tabBtns\.forEach\(b => b\.addEventListener\('click', \(\) => \{(.*?)\n\}\)\);", SRC, re.S)
    assert m, "handler das abas nao encontrado"
    body = m.group(1)
    assert "els.chg.hidden   = (t !== 'chg');" in body
    assert "if (t === 'chg'){ chgUnread = 0; renderChgBadge(); renderChanges(); }" in body


def test_evento_change_do_servidor_alimenta_a_aba():
    assert "ev.t==='change'" in SRC
    assert "noteChange(tab, ev.ch)" in SRC


def test_alteracoes_sao_por_aba_e_por_conversa():
    assert "changes:[]" in SRC                       # estado inicial de cada aba
    assert "tab.changes = [];" in SRC                # NOVA CONVERSA zera
    assert "changes: tab.changes.slice()" in SRC     # NOVA CONVERSA arquiva no historico
    m = re.search(r"function renderActiveTranscript\(\)\{(.*?)\n\}", SRC, re.S)
    assert m and "renderChanges();" in m.group(1)    # trocar de aba repinta


def test_resumo_conta_arquivos_distintos_adicoes_e_remocoes():
    m = re.search(r"function chgSummary\(list\)\{(.*?)\n\}", SRC, re.S)
    assert m, "chgSummary() nao encontrada"
    body = m.group(1)
    assert "new Set()" in body
    assert "c.kind === 'cmd'" in body


# --------------------------- 8e: RELATORIOS VISUAIS ---------------------------
def test_aba_relatorios_existe_com_painel_proprio():
    assert '<button class="tab" data-tab="reps">RELATÓRIOS</button>' in SRC
    assert '<div id="reps" hidden></div>' in SRC
    assert "#reps[hidden]" in SRC          # [hidden] vence o display:flex do painel


def test_troca_de_aba_esconde_e_mostra_o_painel_de_relatorios():
    m = re.search(r"tabBtns\.forEach\(b => b\.addEventListener\('click', \(\) => \{(.*?)\n\}\)\);", SRC, re.S)
    assert m, "handler das abas nao encontrado"
    body = m.group(1)
    assert "els.reps.hidden  = (t !== 'reps');" in body
    assert "if (t === 'reps'){ repsUnread = 0; renderRepsBadge(); renderReports(); }" in body


def test_visor_de_relatorio_tem_overlay_iframe_e_botoes():
    assert 'id="repOverlay"' in SRC
    assert '<iframe id="repFrame"' in SRC
    assert 'id="repClose"' in SRC
    assert 'id="repOpen"' in SRC and 'target="_blank"' in SRC


def test_abrir_relatorio_aponta_iframe_e_link_para_a_rota_reports():
    m = re.search(r"function openReport\(r\)\{(.*?)\n\}", SRC, re.S)
    assert m, "openReport() nao encontrada"
    body = m.group(1)
    assert "'/reports/' + encodeURIComponent(r.file)" in body
    assert "els.repFrame.src = url" in body
    assert "els.repOverlay.hidden = false" in body


def test_fechar_relatorio_esvazia_o_iframe():
    m = re.search(r"function closeReport\(\)\{(.*?)\n\}", SRC, re.S)
    assert m, "closeReport() nao encontrada"
    body = m.group(1)
    assert "els.repOverlay.hidden = true" in body
    assert "about:blank" in body


def test_sonda_abre_o_visor_sozinha_e_acende_a_alca():
    m = re.search(r"async function pollReports\(\)\{(.*?)\n\}", SRC, re.S)
    assert m, "pollReports() nao encontrada"
    body = m.group(1)
    assert "fetch('/reports')" in body
    assert "openReport(fresh[0])" in body      # relatorio novo -> visor abre sozinho
    assert "dockNotify('l')" in body           # gaveta recolhida -> ponto na alca
    assert "setTimeout(pollReports, REPS_POLL_MS)" in body


def test_esc_com_visor_aberto_fecha_o_visor_e_nao_encerra_a_sessao():
    m = re.search(r"document\.addEventListener\('keydown', \(e\) => \{(.*?)\n\}\);", SRC, re.S)
    assert m, "handler global de teclado nao encontrado"
    body = m.group(1)
    assert "!els.repOverlay.hidden" in body
    assert "closeReport()" in body


# --------------- tetos da fase de voz (gravacao + transcricao) ---------------
# Contexto: uma fala de 4min42 deixou o HUD em PROCESSANDO por ~13min sem
# transcript e sem resposta. O turno morreu no /stt, que rodava sem teto, sem
# cronometro e fora do alcance do ENCERRAR (tab.askTimer so nasce em streamAsk).
def test_constantes_de_teto_da_voz_existem_com_os_valores_acordados():
    assert re.search(r"const REC_MAX_S\s*=\s*180\b", SRC), "teto de gravacao != 180s"
    assert re.search(r"const STT_MAX_MS\s*=\s*420000\b", SRC), "teto de transcricao ausente"


def test_gravacao_arma_o_teto_e_avisa_o_usuario_ao_bater():
    m = re.search(r"function armRecCap\(\)\{(.*?)\n\}", SRC, re.S)
    assert m, "armRecCap() nao encontrada"
    body = m.group(1)
    assert "REC_MAX_S*1000" in body                 # teto em ms
    assert "showErrBanner(" in body                 # AVISO visivel no HUD
    assert "dbg('WARN'" in body                     # e rastro na aba DEBUG
    assert "sendTurn()" in body                     # envia o que ja foi falado


def test_startlistening_arma_o_teto_e_sendturn_o_desarma():
    m = re.search(r"async function startListening\(\)\{(.*?)\n\}", SRC, re.S)
    assert m and "armRecCap()" in m.group(1), "startListening nao arma o teto"
    m = re.search(r"function sendTurn\(\)\{(.*?)\n\}", SRC, re.S)
    assert m and "clearRecCap()" in m.group(1), "sendTurn nao desarma o teto"


def test_stt_tem_cronometro_abortcontroller_teto_e_manda_o_sid():
    m = re.search(r"async function onRecStop\(tab\)\{(.*?)\n\}", SRC, re.S)
    assert m, "onRecStop() nao encontrada"
    body = m.group(1)
    assert "tab.sttCtrl=new AbortController()" in body        # cancelavel
    assert "signal:tab.sttCtrl.signal" in body                # ...e o fetch usa
    assert "STT_MAX_MS" in body                               # teto proprio
    assert "setStep('TRANSCREVENDO'" in body                  # fase visivel
    assert "tab.sttTimer=setInterval(" in body                # com cronometro
    assert "fd.append('sid',tab.sid)" in body                 # 1 arquivo por sid
    # encerrado durante o STT: nao ressuscita o turno
    assert "if(tab.ui==='idle')" in body


def test_encerrar_alcanca_a_transcricao_e_desarma_a_gravacao():
    m = re.search(r"function onStop\(\)\{(.*?)\n\}", SRC, re.S)
    assert m, "onStop() nao encontrada"
    body = m.group(1)
    assert "tab.sttCtrl.abort()" in body       # ESC agora alcanca o /stt
    assert "tab.askCtrl.abort()" in body       # e segue alcancando o /ask
    assert "clearRecCap()" in body


# ------------------- captura do mic: DSP do Chrome desligado -----------------
# `{audio:true}` liga echoCancellation/noiseSuppression/autoGainControl por
# padrao. Medido num turno real: 4,3% da energia entre 1-3,4kHz (normal 15-30%)
# e 41% abaixo de 300Hz -> transcricao repetida e incoerente.
def test_getmic_desliga_o_processamento_que_abafa_a_fala():
    m = re.search(r"const MIC_CONSTRAINTS = \{([^}]*)\}", SRC)
    assert m, "MIC_CONSTRAINTS nao encontrada"
    corpo = m.group(1)
    for k in ("echoCancellation:false", "noiseSuppression:false", "autoGainControl:false"):
        assert k in corpo.replace(" ", ""), f"{k} ausente"


def test_getmic_aplica_as_constraints_nos_dois_caminhos():
    m = re.search(r"async function getMic\(\)\{(.*?)\n\}", SRC, re.S)
    assert m, "getMic() nao encontrada"
    body = m.group(1)
    assert "getUserMedia({audio:MIC_CONSTRAINTS})" in body          # mic default
    assert "MIC_CONSTRAINTS)" in body.split("enumerateDevices")[1]  # fallback por deviceId
    assert "{audio:true}" not in body, "ainda pede audio:true em algum caminho"


# A mensagem fixa "nenhum microfone iniciou" escondia o erro real (NotReadableError
# x NotAllowedError), que e o que separa permissao negada de dispositivo travado.
def test_getmic_propaga_o_erro_real_do_navegador():
    m = re.search(r"async function getMic\(\)\{(.*?)\n\}", SRC, re.S)
    assert m, "getMic() nao encontrada"
    body = m.group(1)
    assert "nenhum microfone iniciou" not in body, "ainda lanca a mensagem fixa"
    assert "micErrText(first)" in body, "nao propaga o erro do mic default"
    for nome in ("NotAllowedError", "NotReadableError", "NotFoundError"):
        assert nome in SRC, f"sem dica legivel para {nome}"


def test_startlistening_registra_o_dsp_que_o_mic_aceitou():
    m = re.search(r"async function startListening\(\)\{(.*?)\n\}", SRC, re.S)
    assert m and "getSettings" in m.group(1), "nao loga as settings efetivas do mic"


# --------------- autoquit: a ponte morre junto com esta janela ---------------
def test_hud_pulsa_com_id_proprio_e_em_intervalo_menor_que_o_ttl():
    assert re.search(r"const HUD_ID = 'hud-'", SRC), "HUD_ID ausente"
    m = re.search(r"const HUD_PING_MS\s*=\s*(\d+)", SRC)
    assert m, "HUD_PING_MS ausente"
    assert int(m.group(1)) <= 30000, "pulso raro demais para o TTL do servidor"
    assert "setInterval(hudPing, HUD_PING_MS)" in SRC
    assert re.search(r"^hudPing\(\);", SRC, re.M), "nao pulsa uma vez no load"


def test_hudping_manda_o_id_para_a_rota_certa():
    m = re.search(r"function hudPing\(\)\{(.*?)\n\}", SRC, re.S)
    assert m, "hudPing() nao encontrada"
    body = m.group(1)
    assert "fetch('/hud_ping'" in body
    assert "hud:HUD_ID" in body
    assert ".catch(" in body, "falha de rede no pulso nao pode estourar no console"


def test_fechar_a_janela_da_baixa_no_hud_via_sendbeacon():
    m = re.search(r"window\.addEventListener\('beforeunload', \(\) => \{(.*?)\n\}\);", SRC, re.S)
    assert m, "handler de beforeunload nao encontrado"
    body = m.group(1)
    assert "'/hud_bye'" in body
    assert "hud:HUD_ID" in body
    assert "sendBeacon" in body
    assert "'/session_end'" in body, "a baixa das sessoes nao pode ter se perdido"
