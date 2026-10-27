"""Regressões de paths, identidade e continuidade da conversa na migração."""
import io
import json
import sys
import types
from unittest.mock import patch

import pytest

_fw = types.ModuleType("faster_whisper")
_fw.WhisperModel = lambda *a, **k: object()
sys.modules.setdefault("faster_whisper", _fw)

import server
import launch
from hub_runtime import instance
from hub_runtime.paths import PROJECT_ROOT, RUNTIME_ROOT


def test_identidade_informa_origem_e_caminhos_de_voz_locais():
    data = server.app.test_client().get("/hub_identity").get_json()
    assert data["protocol"] == instance.PROTOCOL
    assert data["project_root"] == str(PROJECT_ROOT)
    assert server.SPEAK_SRV == str(RUNTIME_ROOT / "voice/speak_server.py")
    assert ".claude" not in server.KPY


@pytest.mark.parametrize("data", [
    {"protocol": "other", "project_root": str(PROJECT_ROOT), "pid": 1},
    {"protocol": instance.PROTOCOL, "project_root": "/outro", "pid": 1},
    {"protocol": instance.PROTOCOL, "pid": 1},
    {"protocol": instance.PROTOCOL, "project_root": str(PROJECT_ROOT), "pid": -1},
])
def test_porta_com_origem_desconhecida_nao_e_reutilizada(data):
    with patch.object(instance, "urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
        with pytest.raises(RuntimeError, match="não identificada"):
            instance.verify("http://127.0.0.1:8765")


def test_lancador_nao_abre_chrome_sobre_instancia_alheia():
    with patch.object(launch, "port_open", return_value=True), \
         patch.object(launch, "verify", side_effect=RuntimeError("outra origem")), \
         patch.object(launch.subprocess, "Popen") as popen:
        with pytest.raises(RuntimeError):
            launch.main()
        popen.assert_not_called()


def test_fallback_isola_sids_e_retoma_id_sem_continue_global(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "LOG", str(tmp_path / "transcript.md"))
    server.SESS.clear()
    completed = types.SimpleNamespace(returncode=0, communicate=lambda **kw: ("resposta", ""), poll=lambda: 0)
    commands = []

    def run(cmd, **kwargs):
        assert kwargs["cwd"] == str(PROJECT_ROOT)
        assert "hub_runtime.assistant" in cmd
        assert "--continue" not in cmd
        commands.append(cmd)
        return completed

    with patch.object(server, "spawn_claude", side_effect=RuntimeError("persistente indisponível")), \
         patch.object(server.subprocess, "Popen", side_effect=run):
        client = server.app.test_client()
        for sid in ("isolado-a", "isolado-b", "isolado-a"):
            client.post("/ask", json={"sid": sid, "texto": "pergunta", "mudo": True}).get_data()
    first, second = server.SESS["isolado-a"]["cid"], server.SESS["isolado-b"]["cid"]
    assert first and second and first != second
    assert "--session-id " + first in commands[0]
    assert "--session-id " + second in commands[1]
    assert "--resume " + first in commands[2]
    server.SESS.clear()
