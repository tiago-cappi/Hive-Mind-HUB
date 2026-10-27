"""Testes das funcoes puras do server do Hub (feedback de progresso).

Cobre F1/F4: traducao de tool_use em etapa legivel (friendly_step) e extracao
do plano a partir de input.todos do TodoWrite (todos_to_plan). Stuba
faster_whisper para nao carregar o modelo Whisper no import (teste instantaneo).

Rodar:  .venv/Scripts/python.exe -m pytest tests/test_progress.py -q
"""
import sys
import types

# --- stub do faster_whisper: server.py faz WMODEL = WhisperModel(...) no import ---
_fw = types.ModuleType("faster_whisper")
_fw.WhisperModel = lambda *a, **k: object()
sys.modules.setdefault("faster_whisper", _fw)

import server  # noqa: E402


# ----------------------------- friendly_step (F1) ---------------------------
def test_friendly_step_read():
    assert server.friendly_step({"name": "Read", "input": {"file_path": "C:/x/server.py"}}) == "Lendo server.py"


def test_friendly_step_bash():
    assert server.friendly_step({"name": "Bash", "input": {}}) == "Rodando comando"


def test_friendly_step_grep_trunca():
    s = server.friendly_step({"name": "Grep", "input": {"pattern": "x" * 80}})
    assert s.startswith("Procurando: ") and len(s) <= len("Procurando: ") + 40


def test_friendly_step_desconhecida_usa_nome():
    assert server.friendly_step({"name": "TaskCreate", "input": {}}) == "TaskCreate"


def test_friendly_step_mcp():
    assert server.friendly_step({"name": "mcp__x__y", "input": {}}) == "Ferramenta externa"


# ----------------------------- todos_to_plan (F4) ---------------------------
def test_plan_mapeia_content_e_status():
    todos = [
        {"content": "Ler inbox", "status": "completed"},
        {"content": "Classificar", "status": "in_progress"},
        {"content": "Arquivar", "status": "pending"},
    ]
    out = server.todos_to_plan(todos)
    assert out == [
        {"txt": "Ler inbox", "status": "completed"},
        {"txt": "Classificar", "status": "in_progress"},
        {"txt": "Arquivar", "status": "pending"},
    ]


def test_plan_fallback_activeForm_e_status_default():
    out = server.todos_to_plan([{"activeForm": "Lendo"}])
    assert out == [{"txt": "Lendo", "status": "pending"}]


def test_plan_tolera_formato_invalido():
    assert server.todos_to_plan(None) == []
    assert server.todos_to_plan("nope") == []
    assert server.todos_to_plan([]) == []
    assert server.todos_to_plan([1, "x", {}]) == []  # itens sem txt sao ignorados


def test_plan_ignora_item_sem_texto_mas_mantem_validos():
    out = server.todos_to_plan([{"status": "pending"}, {"content": "ok", "status": "pending"}])
    assert out == [{"txt": "ok", "status": "pending"}]


# --------------------------- change_from_tool (F6) --------------------------
PATCH_EDIT = {
    "filePath": "C:/vault/server.py",
    "structuredPatch": [{
        "oldStart": 1, "oldLines": 3, "newStart": 1, "newLines": 4,
        "lines": [" linha um", "-linha dois", "+linha DOIS", "+linha nova", " linha tres"],
    }],
}


def test_change_edit_conta_linhas_e_monta_diff():
    ch = server.change_from_tool("Edit", {"file_path": "C:/vault/server.py"}, PATCH_EDIT)
    assert ch["kind"] == "edit" and ch["file"] == "server.py"
    assert ch["add"] == 2 and ch["del"] == 1
    assert ch["diff"][0] == "@@ -1,3 +1,4 @@"
    assert "+linha DOIS" in ch["diff"] and "-linha dois" in ch["diff"]
    assert ch["truncated"] is False and ch["ok"] is True


def test_change_write_novo_conta_conteudo_inteiro():
    res = {"type": "create", "filePath": "C:/vault/nota.md",
           "content": "a\nb\nc", "structuredPatch": []}
    ch = server.change_from_tool("Write", {"file_path": "C:/vault/nota.md"}, res)
    assert ch["kind"] == "create" and ch["add"] == 3 and ch["del"] == 0
    assert ch["diff"] == ["+a", "+b", "+c"]


def test_change_trunca_diff_gigante():
    hunk = {"oldStart": 1, "oldLines": 0, "newStart": 1, "newLines": 999,
            "lines": ["+x" for _ in range(server.MAX_DIFF_LINES + 50)]}
    ch = server.change_from_tool("Write", {"file_path": "/x/big.py"},
                                 {"filePath": "/x/big.py", "structuredPatch": [hunk]})
    assert ch["truncated"] is True
    assert len(ch["diff"]) == server.MAX_DIFF_LINES
    assert ch["add"] == server.MAX_DIFF_LINES + 50   # contagem NAO e' truncada


def test_change_trunca_linha_muito_larga():
    hunk = {"oldStart": 1, "oldLines": 1, "newStart": 1, "newLines": 1,
            "lines": ["+" + "y" * 900]}
    ch = server.change_from_tool("Edit", {}, {"filePath": "/x/a.py", "structuredPatch": [hunk]})
    assert len(ch["diff"][1]) == server.MAX_DIFF_COLS


def test_change_bash_vira_comando():
    ch = server.change_from_tool("Bash", {"command": "git status", "description": "ver estado"}, None)
    assert ch == {"kind": "cmd", "cmd": "git status", "desc": "ver estado", "ok": True}


def test_change_powershell_vira_comando():
    # no Windows o claude aninhado roda comandos por PowerShell, nao por Bash
    ch = server.change_from_tool("PowerShell", {"command": "git status"}, None)
    assert ch["kind"] == "cmd" and ch["cmd"] == "git status"


def test_change_bash_com_erro_marca_ok_falso():
    ch = server.change_from_tool("Bash", {"command": "falha"}, None, is_error=True)
    assert ch["ok"] is False


def test_change_ignora_ferramentas_de_leitura():
    assert server.change_from_tool("Read", {"file_path": "/x/a.py"}, {}) is None
    assert server.change_from_tool("Grep", {"pattern": "x"}, {}) is None
    assert server.change_from_tool("Bash", {"command": "  "}, None) is None


def test_change_tolera_resultado_ausente_ou_invalido():
    ch = server.change_from_tool("Edit", {"file_path": "/x/a.py"}, None)
    assert ch["file"] == "a.py" and ch["add"] == 0 and ch["del"] == 0 and ch["diff"] == []
    ch2 = server.change_from_tool("Edit", {"file_path": "/x/a.py"}, {"structuredPatch": "nope"})
    assert ch2["diff"] == []
