"""Cancelamento real do fallback e exclusão entre inicializações concorrentes."""
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from unittest.mock import patch

import pytest
import types
_fw = types.ModuleType("faster_whisper")
_fw.WhisperModel = lambda *a, **k: object()
sys.modules.setdefault("faster_whisper", _fw)
import server
import launch
from hub_runtime import instance_lock


class BlockingFallback:
    def __init__(self):
        self.started = threading.Event()
        self.finished = threading.Event()
        self.returncode = None

    def communicate(self, input=None, timeout=None):
        self.started.set()
        assert self.finished.wait(5)
        return "resposta que não pode aparecer depois de cancelada", ""

    def poll(self):
        return self.returncode

    def kill(self):
        self.returncode = -1
        self.finished.set()


@pytest.mark.parametrize("route", ["/abort", "/session_end"])
def test_cancelamento_alcanca_fallback_sem_publicar_resposta(tmp_path, monkeypatch, route):
    monkeypatch.setattr(server, "LOG", str(tmp_path / "transcript.md"))
    server.SESS.clear()
    process = BlockingFallback()
    output = []

    def request():
        with server.app.test_client() as client:
            output.append(client.post("/ask", json={"sid": "cancel", "texto": "fixture", "mudo": True}).get_data())

    with patch.object(server, "spawn_claude", side_effect=RuntimeError("fixture")), \
         patch.object(server.subprocess, "Popen", return_value=process):
        thread = threading.Thread(target=request)
        thread.start()
        assert process.started.wait(3)
        assert server.SESS["cancel"]["proc"] is process
        response = server.app.test_client().post(route, json={"sid": "cancel"})
        assert response.status_code == 200
        thread.join(3)
        assert not thread.is_alive()
    assert process.poll() is not None
    assert b'"t": "done"' not in output[0]
    assert not (tmp_path / "transcript.md").exists()
    server.SESS.clear()


def test_abortar_persistente_nao_inicia_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "LOG", str(tmp_path / "transcript.md"))
    server.SESS.clear()
    client = server.app.test_client()
    response = client.post("/ask", json={"sid": "early", "texto": "fixture", "mudo": True}, buffered=False)
    client.post("/abort", json={"sid": "early"})
    with patch.object(server, "spawn_claude", side_effect=RuntimeError("fixture")), \
         patch.object(server.subprocess, "Popen") as popen:
        body = response.get_data()
    popen.assert_not_called()
    assert b'"t": "done"' not in body
    server.SESS.clear()


@pytest.mark.skipif(os.name != "nt", reason="árvore Windows usada pela instalação")
def test_timeout_fallback_mata_descendente_que_tentaria_escrever(tmp_path, monkeypatch):
    leaf = tmp_path / "leaf.py"
    marker = tmp_path / "orphan.txt"
    parent = tmp_path / "parent.py"
    leaf.write_text("import sys,time\nfrom pathlib import Path\ntime.sleep(2)\nPath(sys.argv[1]).write_text('orphan')\n")
    parent.write_text("import subprocess,sys,time\nsubprocess.Popen([sys.executable,sys.argv[1],sys.argv[2]])\ntime.sleep(30)\n")
    monkeypatch.setattr(server, "LOG", str(tmp_path / "transcript.md"))
    monkeypatch.setattr(server, "FALLBACK_TIMEOUT", 0.4)
    monkeypatch.setattr(server, "bridge_command", lambda args: subprocess.list2cmdline([sys.executable, str(parent), str(leaf), str(marker)]))
    server.SESS.clear()
    with patch.object(server, "spawn_claude", side_effect=RuntimeError("fixture")):
        body = server.app.test_client().post("/ask", json={"sid": "timeout", "texto": "fixture", "mudo": True}).get_data()
    time.sleep(2.1)
    assert not marker.exists(), "descendente continuou escrevendo depois do timeout"
    assert server.SESS["timeout"]["proc"] is None
    assert b"fallback excecao" in body
    server.SESS.clear()


def hold_instance(state, entered, leave):
    instance_lock.RUNTIME_ROOT = Path(state)
    with instance_lock.hold("bridge", timeout=1):
        entered.set()
        leave.wait(5)


def test_segunda_ponte_e_recusada_enquanto_primeira_esta_viva(tmp_path, monkeypatch):
    context = multiprocessing.get_context("spawn")
    entered, leave = context.Event(), context.Event()
    process = context.Process(target=hold_instance, args=(str(tmp_path), entered, leave))
    process.start()
    try:
        assert entered.wait(5)
        monkeypatch.setattr(instance_lock, "RUNTIME_ROOT", tmp_path)
        with pytest.raises(RuntimeError, match="ponte"):
            with instance_lock.hold("bridge", timeout=0.1):
                pytest.fail("lock duplicado")
    finally:
        leave.set()
        process.join(5)
        if process.is_alive():
            process.kill()
    assert process.exitcode == 0
    with instance_lock.hold("bridge", timeout=0.1):
        pass


def test_lancadores_simultaneos_criam_uma_unica_ponte(tmp_path, monkeypatch):
    monkeypatch.setattr(instance_lock, "RUNTIME_ROOT", tmp_path)
    opened = threading.Event()
    servers = []
    browsers = []
    errors = []

    def popen(args, **kwargs):
        if args[0] == launch.VHPYW:
            servers.append(args)
            time.sleep(0.1)
            opened.set()
        else:
            browsers.append(args)

    def request():
        try:
            launch.main()
        except Exception as error:
            errors.append(error)

    with patch.object(launch, "port_open", side_effect=opened.is_set), \
         patch.object(launch, "verify"), \
         patch.object(launch.subprocess, "Popen", side_effect=popen):
        threads = [threading.Thread(target=request) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(5)
    assert not errors
    assert len(servers) == 1
    assert len(browsers) == 2


def test_shutdown_aguarda_residente_proprio_antes_de_ceder_posse(monkeypatch):
    order = []

    class Resident:
        def wait(self, timeout):
            assert server.SPEAK_OWNED is True
            order.append("resident-exited")

    monkeypatch.setattr(server, "SPEAK_OWNED", True)
    monkeypatch.setattr(server, "SPEAK_PROC", Resident())
    monkeypatch.setattr(server, "kill_all", lambda: order.append("sessions-ended"))
    monkeypatch.setattr(server, "stop_speak_server", lambda: order.append("quit"))
    server._shutdown()
    assert order == ["sessions-ended", "quit", "resident-exited"]
    assert server.SPEAK_OWNED is False
    server._shutdown()
    assert len(order) == 3


def test_fallback_nao_ultrapassa_teto_de_sessoes(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "LOG", str(tmp_path / "transcript.md"))
    server.SESS.clear()
    for index in range(server.MAX_SESS):
        server.get_sess(str(index))["proc"] = BlockingFallback()
    with patch.object(server, "spawn_claude", side_effect=RuntimeError("fixture")), \
         patch.object(server.subprocess, "Popen") as popen:
        body = server.app.test_client().post("/ask", json={"sid": "extra", "texto": "fixture", "mudo": True}).get_data()
    popen.assert_not_called()
    assert b"limite de 6" in body
    assert server._alive_count() == server.MAX_SESS
    server.SESS.clear()


@pytest.mark.skipif(sys.platform != "win32", reason="stop_instance.ps1 é do Windows")
def test_stop_ignora_marcador_velho_sem_encerrar_processo_alheio(tmp_path):
    # 24/10/2026: o Hub caiu, o Windows reaproveitou o PID do marcador e a parada era recusada.
    script = (Path(__file__).resolve().parents[1] / "hub_runtime" / "stop_instance.ps1").read_text(encoding="utf-8")
    runtime = tmp_path / "hub_runtime"
    (runtime / "state").mkdir(parents=True)
    # Porta trocada por uma livre: o teste não depende do Hub real.
    (runtime / "stop_instance.ps1").write_text(script.replace("8765", "1"), encoding="utf-8")
    alien = subprocess.Popen(["ping", "-n", "30", "127.0.0.1"], stdout=subprocess.DEVNULL)
    marker = runtime / "state" / "instance.json"
    marker.write_text(json.dumps({"protocol": "hub-runtime-v1", "project_root": str(tmp_path),
                                  "pid": alien.pid, "speech_pid": 0}), encoding="utf-8")
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                 str(runtime / "stop_instance.ps1")], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        assert alien.poll() is None
        assert not marker.exists()
    finally:
        alien.kill()
