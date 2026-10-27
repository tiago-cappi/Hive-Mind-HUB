"""Testes estaticos do redesenho da gaveta CONVERSA (docs/task-hud-gaveta.md).

Sao asserts sobre o index.html: garantem que as cinco etapas continuam no
arquivo e, principalmente, que o redesenho segue escopado em `body.minimal` --
o painel completo tem de sobreviver intacto.

Rodar:  python -m pytest tests/test_dock_redesign.py -q
"""
import re
from pathlib import Path

INDEX = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


# ---------------------------- Etapa 1: largura -------------------------------
def test_largura_da_gaveta_e_elastica_e_persistente():
    assert "--dock-w:clamp(420px, 34vw, 760px)" in INDEX
    assert "core.dockw" in INDEX
    assert 'id="dockGrip"' in INDEX


def test_arrasto_nao_redimensiona_o_nucleo():
    # a gaveta flutua por cima: mexer no grafo a cada pointermove era o que o
    # usuario explicitamente nao queria.
    trecho = INDEX[INDEX.index("dockGrip"):]
    trecho = trecho[:trecho.index("Etapa 2") if "Etapa 2" in trecho else 4000]
    assert "graph.resize()" not in trecho


# ---------------------------- Etapa 2: rail ----------------------------------
def test_rail_vertical_com_icones_sem_tocar_no_markup_das_abas():
    assert 'grid-template-columns:104px 1fr' in INDEX
    assert '<button class="tab" data-tab="chg">ALTERAÇÕES</button>' in INDEX
    assert '<button class="tab" data-tab="reps">RELATÓRIOS</button>' in INDEX
    for tab in ("log", "chg", "debug", "convs", "reps"):
        assert f'.tab[data-tab="{tab}"]::before' in INDEX


def test_cabecalho_da_visao_existe_e_tem_titulo_proprio():
    assert 'id="dockHead"' in INDEX and 'id="dockTitle"' in INDEX
    assert "DOCK_VIEW_LABELS" in INDEX


# ---------------------------- Etapa 3: tipografia ----------------------------
def test_escala_do_corpo_sobe_so_na_gaveta():
    assert "body.minimal #log{ font-size:13.5px; }" in INDEX
    assert "body.minimal #debug{ font-size:12.5px; }" in INDEX
    # o painel completo continua com a regra base
    assert re.search(r"#log\{[^}]*font-size:12px", INDEX, re.S)


def test_densidade_persiste_e_tem_botao():
    assert 'id="densToggle"' in INDEX and "core.dense" in INDEX


# ---------------------------- Etapa 4: busca ---------------------------------
def test_busca_filtra_a_visao_ativa():
    assert 'id="dockFind"' in INDEX
    assert "function applyFind()" in INDEX
    for sel in ("'.line'", "'.dl'", "'.chg-row'", "'.conv-item'", "'.rep-item'"):
        assert sel in INDEX


def test_esc_na_busca_nao_encerra_a_sessao():
    # o handler global de keydown encerra a sessao no Esc; o campo tem de parar
    # o evento antes de chegar la.
    i = INDEX.index("els.dockFind.addEventListener('keydown'")
    assert "e.stopPropagation()" in INDEX[i:i + 500]


def test_filtro_so_esconde_no_minimalista():
    # com o filtro escrito, voltar ao painel completo nao pode sumir com linhas
    assert "body.minimal .nomatch{ display:none !important; }" in INDEX


def test_chips_de_nivel_do_debug():
    assert "core.dbgLevels" in INDEX
    for lv in ("info", "ok", "warn", "err", "net", "step"):
        assert f'data-lv="{lv}"' in INDEX
        # o CSS alinha os seletores em coluna, entao o espaco entre eles varia
        assert re.search(rf"#debug\.hide-{lv}\s+\.dl\.{lv}", INDEX)


# ---------------------------- Etapa 5: transcript ----------------------------
def test_turno_vira_bloco_com_faixa_por_autor():
    assert "body.minimal #log .line{" in INDEX
    for autor, cor in (("eu", "--teal"), ("claude", "--green"), ("sys", "--err")):
        assert f"body.minimal #log .line.{autor}{{ border-left-color:var({cor}); }}" in INDEX


def test_gaveta_demora_mais_pra_recolher_e_respeita_leitura():
    assert "const DOCK_HIDE_MS = 45000;" in INDEX
    assert "function dockBusy(el)" in INDEX
    assert "window.getSelection" in INDEX


def test_legenda_cala_com_a_gaveta_aberta():
    assert "body.minimal.dock-l .caption{ display:none; }" in INDEX


# ---------------------------- regra transversal ------------------------------
def test_o_redesenho_nao_vaza_pro_painel_completo():
    # toda regra nova das seções 9b-* tem de estar sob body.minimal (ou ser
    # definicao de componente que so' aparece la dentro).
    inicio = INDEX.index("9b-bis. RAIL VERTICAL")
    fim = INDEX.index("9c. CHAT POR TEXTO")
    bloco = INDEX[inicio:fim]
    seletores = [ln.strip() for ln in bloco.splitlines()
                 if ln.strip().endswith("{") and not ln.strip().startswith(("/*", "*", "@"))]
    livres = [x for x in seletores
              if "body.minimal" not in x
              and not x.startswith((".dh-btn", ".dbg-chip", ".dock-head", ".dh-find",
                                    ".dh-count", ".dbg-levels"))]
    assert not livres, f"regras fora de body.minimal: {livres}"
