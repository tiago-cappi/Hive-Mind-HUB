"""Contratos da separação das pastas e concorrência real entre processos."""
import json
import multiprocessing
import os
from pathlib import Path

import pytest

from hub_runtime import assistant, paths
from hub_runtime.guards import file_guard as guard


def event(session, tool, file, stage="PreToolUse", tool_id="tool"):
    return {"session_id": session, "tool_name": tool,
            "tool_input": {"file_path": str(file)},
            "hook_event_name": stage, "tool_use_id": tool_id}


def read(vault, state, session, file):
    guard.handle(event(session, "Read", file), vault, state, session, os.getpid())
    value = file.read_text()
    guard.handle(event(session, "Read", file, "PostToolUse"), vault, state, session, os.getpid())
    return value


def writer(vault, state, barrier, results, session, shell):
    vault, state = Path(vault), Path(state)
    file = vault / "nota.md"
    original = read(vault, state, session, file)
    barrier.wait(timeout=10)
    tool = "Bash" if shell else "Edit"
    try:
        guard.handle(event(session, tool, file), vault, state, session, os.getpid())
        file.write_text(str(int(original) + 1))
        guard.handle(event(session, tool, file, "PostToolUse"), vault, state, session, os.getpid())
        results.put("written")
    except RuntimeError:
        results.put("stale")


@pytest.mark.parametrize("shell", [False, True])
def test_duas_sessoes_nao_sobrescrevem_versao_defasada(tmp_path, shell):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "nota.md").write_text("1")
    state = tmp_path / "guards"
    context = multiprocessing.get_context("spawn")
    barrier, results = context.Barrier(2), context.Queue()
    procs = [context.Process(target=writer, args=(str(vault), str(state), barrier, results, sid, shell))
             for sid in ("a", "b")]
    for p in procs:
        p.start()
    for p in procs:
        p.join(20)
        if p.is_alive():
            p.kill()
        assert p.exitcode == 0
    assert sorted([results.get(timeout=2), results.get(timeout=2)]) == ["stale", "written"]
    assert (vault / "nota.md").read_text() == "2"
    # Releitura explícita permite recalcular a segunda alteração, sem perdê-la.
    file = vault / "nota.md"
    assert read(vault, state, "b", file) == "2"
    guard.handle(event("b", "Edit", file), vault, state, "b", os.getpid())
    file.write_text("3")
    guard.handle(event("b", "Edit", file, "PostToolUse"), vault, state, "b", os.getpid())
    assert file.read_text() == "3"


def test_nota_existente_exige_leitura_e_falha_libera_lock(tmp_path):
    file = tmp_path / "nota.md"
    file.write_text("original")
    state = tmp_path / "state"
    with pytest.raises(RuntimeError, match="Leia"):
        guard.handle(event("s", "Write", file), tmp_path, state, "s", os.getpid())
    assert not (state / "active").exists()
    read(tmp_path, state, "s", file)
    guard.handle(event("s", "Edit", file), tmp_path, state, "s", os.getpid())
    guard.handle(event("s", "Edit", file, "PostToolUseFailure"), tmp_path, state, "s", os.getpid())
    assert not (state / "active").exists()
    assert file.read_text() == "original"


def test_lock_de_outro_escritor_vivo_nao_e_roubado(tmp_path):
    guard.acquire(tmp_path, "a", os.getpid(), "one")
    with pytest.raises(RuntimeError, match="Outra ferramenta"):
        guard.acquire(tmp_path, "b", os.getpid(), "two", timeout=0.1)
    guard.release_owner(tmp_path, "b")
    assert (tmp_path / "active").exists()
    guard.release_owner(tmp_path, "a")


def test_recusa_de_permissao_no_batch_nao_prende_acervo(tmp_path):
    file = tmp_path / "nova.md"
    state = tmp_path / "state"
    ev = event("s", "Write", file)
    guard.handle(ev, tmp_path, state, "s", os.getpid())
    guard.handle({"session_id": "s", "hook_event_name": "PostToolBatch", "tool_calls": [ev]},
                 tmp_path, state, "s", os.getpid())
    assert not (state / "active").exists()
    assert not file.exists()


def test_lock_de_dono_morto_e_recuperado(tmp_path, monkeypatch):
    guard.acquire(tmp_path, "old", os.getpid(), "one")
    monkeypatch.setattr(guard, "pid_alive", lambda pid: False)
    guard.acquire(tmp_path, "new", os.getpid(), "two")
    assert json.loads((tmp_path / "active/owner.json").read_text())["owner"] == "new"
    guard.release_owner(tmp_path, "new")


def test_background_nao_libera_escritor_antes_do_fim(tmp_path):
    ev = event("s", "Bash", tmp_path / "nota.md")
    ev["tool_input"]["run_in_background"] = True
    with pytest.raises(RuntimeError, match="termine"):
        guard.handle(ev, tmp_path, tmp_path / "state", "s", os.getpid())


def test_dados_do_hub_nao_sao_editados_como_notas(tmp_path):
    with pytest.raises(RuntimeError, match="histórico"):
        guard.handle(event("s", "Write", tmp_path / "_agentes/voice-hub.md"),
                     tmp_path, tmp_path / "state", "s", os.getpid())


def test_acervo_deve_existir_ser_absoluto_e_separado(tmp_path, monkeypatch):
    project, vault = tmp_path / "project", tmp_path / "vault"
    project.mkdir()
    vault.mkdir()
    monkeypatch.setattr(paths, "PROJECT_ROOT", project)
    monkeypatch.setenv("HUB_VAULT", str(vault))
    assert paths.vault_root() == vault
    for invalid in ("relativo", str(project), str(tmp_path / "ausente")):
        monkeypatch.setenv("HUB_VAULT", invalid)
        with pytest.raises(ValueError):
            paths.vault_root()


def test_runtime_nao_carrega_pipeline_nem_hooks_globais(tmp_path):
    config = assistant.settings(tmp_path, tmp_path / "state")
    assert config["autoMemoryEnabled"] is False
    assert "**/AGENTS.md" in config["claudeMdExcludes"]
    assert "**/CLAUDE.md" in config["claudeMdExcludes"]
    assert "Stop" not in config["hooks"]
    assert config["hooks"]["PreToolUse"]
    prompt = assistant.operational_prompt(tmp_path)
    assert str(tmp_path) in prompt
    assert "_agentes/relatorios/" in prompt
    assert "não uma sessão de desenvolvimento" in prompt


def abandon_publication(state):
    state = Path(state)
    # Encerramento real enquanto os metadados ainda são preparados.
    guard.atomic_json = lambda *a, **k: os._exit(77)
    guard.acquire(state, "dead", os.getpid(), "one")


def test_morte_antes_de_publicar_dono_nao_bloqueia_guarda(tmp_path):
    context = multiprocessing.get_context("spawn")
    proc = context.Process(target=abandon_publication, args=(str(tmp_path),))
    proc.start()
    proc.join(10)
    assert proc.exitcode == 77
    guard.acquire(tmp_path, "new", os.getpid(), "two", timeout=0.2)
    assert json.loads((tmp_path / "active/owner.json").read_text())["owner"] == "new"
    assert not list(tmp_path.glob(".claim-*"))
    guard.release_owner(tmp_path, "new")


def test_publicacao_antiga_incompleta_e_recuperada(tmp_path):
    (tmp_path / "active").mkdir()
    guard.acquire(tmp_path, "new", os.getpid(), "two", timeout=0.2)
    guard.release_owner(tmp_path, "new")
    assert not (tmp_path / "active").exists()


@pytest.mark.parametrize("stage", ["PostToolUse", "PostToolUseFailure", "PostToolBatch"])
def test_cleanup_atrasado_nao_libera_ferramenta_atual(tmp_path, stage):
    file = tmp_path / "nota.md"
    state = tmp_path / "state"
    current = event("s", "Write", file, tool_id="current")
    guard.handle(current, tmp_path, state, "s", os.getpid())
    previous = event("s", "Write", file, stage, tool_id="previous")
    if stage == "PostToolBatch":
        previous["tool_calls"] = [event("s", "Write", file, tool_id="previous")]
    guard.handle(previous, tmp_path, state, "s", os.getpid())
    assert json.loads((state / "active/owner.json").read_text())["tool"] == "current"
    with pytest.raises(RuntimeError, match="Outra ferramenta"):
        guard.acquire(state, "other", os.getpid(), "other", timeout=0.1)
    guard.handle(event("s", "Write", file, "PostToolUseFailure", "current"),
                 tmp_path, state, "s", os.getpid())


def test_liberacao_repete_falha_transitoria_sem_silenciar_erro(tmp_path, monkeypatch):
    guard.acquire(tmp_path, "a", os.getpid(), "one")
    original = guard.shutil.rmtree
    calls = []

    def transient(lock):
        calls.append(lock)
        if len(calls) == 1:
            raise OSError(145, "diretório ocupado transitoriamente")
        return original(lock)

    monkeypatch.setattr(guard.shutil, "rmtree", transient)
    guard.release_owner(tmp_path, "a")
    assert len(calls) == 2
    assert not (tmp_path / "active").exists()
    guard.acquire(tmp_path, "b", os.getpid(), "two")
    monkeypatch.setattr(guard.shutil, "rmtree", lambda lock: (_ for _ in ()).throw(OSError(145, "persistente")))
    with pytest.raises(OSError):
        guard.release_owner(tmp_path, "b")
    assert (tmp_path / "active").exists()
