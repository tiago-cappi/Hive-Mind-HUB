import json
from dataclasses import replace
from pathlib import Path
import sys
import threading

import pytest

from HiveMind.backend.adapters.base import DiscoveryError, DiscoveryRpc
from HiveMind.backend.adapters.claude import (ClaudeAdapter, ClaudeProofSession, model_only_arguments,
                                              model_only_environment)
from HiveMind.backend.adapters.codex import (CodexAdapter, CodexProofSession, disabled_mcp_roster,
                                             security_inventory, session_params)
from HiveMind.backend.capabilities import (PauseRequested, ToolAdmission, ToolBroker,
                                           ToolNotAllowed, evaluate)


FIXTURE = Path(__file__).parent / "fixtures" / "hivemind" / "fake_cli.py"


def command(provider):
    return [sys.executable, str(FIXTURE), provider]


def test_codex_discovery_is_sanitized_and_never_starts_a_turn(tmp_path, monkeypatch):
    log = tmp_path / "requests.jsonl"
    monkeypatch.setenv("HIVEMIND_FIXTURE_LOG", str(log))
    monkeypatch.setenv("OPENAI_API_KEY", "secret-fixture")
    discovery = CodexAdapter(command("codex"), timeout=5).discover()

    assert discovery.installed and discovery.compatible and discovery.authenticated
    assert discovery.account_kind == "chatgpt"
    assert [(m.name, m.efforts) for m in discovery.models] == [
        ("fixture-model", ("high",)), ("fixture-other", ("low",))]
    assert discovery.ordinary_usage_allowed is True and discovery.has_credits is False
    assert "private-fixture" not in repr(discovery) and "secret-fixture" not in repr(discovery)
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert events[0] == {"api_key_present": False}
    requests = [event for event in events if "method" in event]
    assert [event["method"] for event in requests] == [
        "initialize", "initialized", "account/read", "model/list", "model/list", "account/rateLimits/read"]
    assert requests[2]["params"] == {"refreshToken": False}
    assert requests[0]["params"]["capabilities"]["experimentalApi"] is False


def test_claude_discovery_does_not_expose_identity_or_api_key(tmp_path, monkeypatch):
    log = tmp_path / "status.jsonl"
    monkeypatch.setenv("HIVEMIND_FIXTURE_LOG", str(log))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-fixture")
    discovery = ClaudeAdapter(command("claude"), timeout=5).discover()

    assert discovery.installed and discovery.compatible and discovery.authenticated
    assert discovery.account_kind == "claude.ai"
    assert [(item.name, item.efforts) for item in discovery.models] == [("sonnet", ("medium", "high"))]
    assert discovery.ordinary_usage_allowed is True and discovery.extra_usage_enabled is False
    assert discovery.policy_customizations_absent is True
    assert "private-fixture" not in repr(discovery) and "secret-fixture" not in repr(discovery)
    assert [json.loads(line) for line in log.read_text().splitlines()] == [
        {"api_key_present": False},
        {"claude_request_type": "control_request", "request": {"subtype": "initialize"}},
        {"claude_request_type": "control_request", "request": {"subtype": "get_settings"}},
        {"claude_request_type": "control_request", "request": {"subtype": "get_usage", "skip_behaviors": True}}]


def test_gate_does_not_confuse_catalog_with_permission_or_enable_execution():
    discovery = CodexAdapter(command("codex"), timeout=5).discover()
    listed = evaluate(discovery, "fixture-model", "high")
    assert listed.catalog == "listed" and listed.entitlement == "not_tested"
    assert listed.included_billing == "ordinary_available"
    assert not listed.execution_allowed and "enforcement_evidence_unverified" in listed.reasons
    assert evaluate(discovery, "fixture-model", "low").catalog == "effort_unlisted"
    assert evaluate(discovery, "absent-model", "high").catalog == "model_unlisted"
    assert evaluate(ClaudeAdapter(command("claude"), timeout=5).discover(), "any", "high").catalog == "model_unlisted"


def test_gate_requires_live_verified_session_and_current_billing(tmp_path, monkeypatch):
    marker = tmp_path / "changed"
    monkeypatch.setenv("HIVEMIND_FIXTURE_CHANGED", str(marker))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    broker = ToolBroker({name: lambda args: None for name in ("read", "patch", "checks")})
    adapter = CodexAdapter(command("codex"), timeout=5)
    codex = adapter.discover()
    assert not evaluate(codex, "fixture-model", "high", {"protocol": True}).execution_allowed
    with CodexProofSession(adapter, "fixture-model", "high", str(tmp_path), broker) as session:
        evidence = session.evidence()
        assert evaluate(codex, "fixture-model", "high", evidence).execution_allowed
        assert not evaluate(codex, "fixture-other", "low", evidence).execution_allowed
        assert not evaluate(replace(codex, has_credits=True), "fixture-model", "high", evidence).execution_allowed
        marker.touch()
        assert not evaluate(codex, "fixture-model", "high", evidence).execution_allowed
    assert not evaluate(codex, "fixture-model", "high", evidence).execution_allowed

    claude_adapter = ClaudeAdapter(command("claude"), timeout=5)
    claude = claude_adapter.discover()
    with ClaudeProofSession(claude_adapter, "sonnet", "high", str(tmp_path), broker) as session:
        evidence = session.evidence()
        assert evaluate(claude, "sonnet", "high", evidence).execution_allowed
        assert not evaluate(replace(claude, extra_usage_enabled=True), "sonnet", "high", evidence).execution_allowed
        assert not evaluate(replace(claude, policy_customizations_absent=None), "sonnet", "high", evidence).execution_allowed
        broker.admission.request_pause()
        assert not evaluate(claude, "sonnet", "high", evidence).execution_allowed
    assert not evaluate(claude, "sonnet", "high", evidence).execution_allowed


def test_codex_session_rejects_native_environment_and_enabled_mcp(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    broker = ToolBroker({name: lambda args: None for name in ("read", "patch", "checks")})
    adapter = CodexAdapter(command("codex"), timeout=5)
    monkeypatch.setenv("HIVEMIND_FIXTURE_BAD_THREAD", "1")
    with pytest.raises(DiscoveryError, match="thread_controls_unverified:environments"):
        with CodexProofSession(adapter, "fixture-model", "high", str(tmp_path), broker):
            pytest.fail("native environment was accepted")
    monkeypatch.delenv("HIVEMIND_FIXTURE_BAD_THREAD")
    monkeypatch.setenv("HIVEMIND_FIXTURE_BAD_MCP", "1")
    with pytest.raises(DiscoveryError, match="session_controls_unverified"):
        with CodexProofSession(adapter, "fixture-model", "high", str(tmp_path), broker):
            pytest.fail("enabled MCP was accepted")


def test_unexpected_server_request_fails_closed(monkeypatch):
    monkeypatch.setenv("HIVEMIND_FIXTURE_SERVER_REQUEST", "1")
    discovery = CodexAdapter(command("codex"), timeout=5).discover()
    assert "unexpected_server_request" in discovery.errors
    assert not evaluate(discovery, "fixture-model", "high").execution_allowed


def test_discovery_transport_rejects_turns_without_sending_them():
    with DiscoveryRpc(command("codex"), timeout=5) as rpc:
        with pytest.raises(DiscoveryError, match="method_not_allowed"):
            rpc.request("turn/start", {})


def test_broker_pause_refuses_new_work_and_waits_for_inflight_write(tmp_path):
    admission = ToolAdmission()
    started = threading.Event()
    finish = threading.Event()
    target = tmp_path / "output.txt"

    def write():
        with admission.admit():
            started.set()
            assert finish.wait(5)
            target.write_text("complete")

    worker = threading.Thread(target=write)
    worker.start()
    try:
        assert started.wait(5)
        assert not admission.request_pause()
        with pytest.raises(PauseRequested):
            with admission.admit():
                pytest.fail("new operation was admitted")
        assert not admission.drained() and not target.exists()
    finally:
        finish.set()
        worker.join(timeout=5)
    assert not worker.is_alive() and admission.drained()
    assert target.read_text() == "complete"


def test_candidate_sessions_disable_native_surfaces():
    params = session_params("fixture-model", "C:/fixture/work", ["fixture"])
    assert params["environments"] == [] and params["allowProviderModelFallback"] is False
    assert [tool["name"] for tool in params["dynamicTools"]] == ["read", "patch", "checks", "progress"]
    assert params["config"]["agents"]["enabled"] is False
    assert params["config"]["features"]["multi_agent_v2"] is False
    assert params["config"]["mcp_servers"] == {"fixture": {"enabled": False}}
    assert params["config"]["project_doc_max_bytes"] == 0
    assert params["permissions"] == ":read-only" and "permissions" not in params["config"]
    args = model_only_arguments()
    assert args[args.index("--tools") + 1] == ""
    assert args[args.index("--setting-sources") + 1] == ""
    assert args[args.index("--mcp-config") + 1] == '{"mcpServers":{}}'
    assert "--strict-mcp-config" in args and "--safe-mode" in args and "--bare" not in args
    assert model_only_environment()["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"


def test_broker_only_dispatches_allowlisted_handlers_and_obeys_pause():
    called = []
    handlers = {name: lambda args, name=name: called.append((name, args))
                for name in ("read", "patch", "checks")}
    broker = ToolBroker(handlers)
    broker.dispatch("read", {"path": "fixture"})
    with pytest.raises(ToolNotAllowed):
        broker.dispatch("shell", {})
    with pytest.raises(ValueError):
        broker.dispatch("patch", "not-an-object")
    assert broker.admission.request_pause() and broker.admission.drained()
    with pytest.raises(PauseRequested):
        broker.dispatch("checks", {})
    assert called == [("read", {"path": "fixture"})]
    with pytest.raises(ValueError):
        ToolBroker({})


def test_inventory_and_roster_fail_closed_without_exposing_config(tmp_path):
    adapter = CodexAdapter(command("codex"), timeout=5)
    first = adapter.security_inventory(tmp_path, tmp_path)
    assert first.mcp_names == ("fixture",) and not first.reasons
    assert "private-fixture" not in repr(first) and "fixture" not in repr(first)
    assert disabled_mcp_roster([{"name": "fixture", "runtimeStatus": "disabled"}], first.mcp_names)
    assert not disabled_mcp_roster([{"name": "fixture", "runtimeStatus": None}], first.mcp_names)
    assert not disabled_mcp_roster([], first.mcp_names)
    assert not disabled_mcp_roster([{"name": "other", "runtimeStatus": "disabled"}], first.mcp_names)
    (tmp_path / "AGENTS.md").write_text("private fixture")
    changed = adapter.security_inventory(tmp_path, tmp_path)
    assert changed.reasons == ("global_instructions_present",) and changed.fingerprint != first.fingerprint
    custom = security_inventory({"mcp_servers": {}, "instructions": "private fixture"}, tmp_path)
    assert "custom_instructions_present" in custom.reasons and "private fixture" not in repr(custom)
    with pytest.raises(DiscoveryError, match="security_config_invalid"):
        security_inventory({}, tmp_path)


def test_claude_accepts_newer_release_only_with_every_isolation_flag(monkeypatch):
    import HiveMind.backend.adapters.claude as claude
    flags = [arg for arg in model_only_arguments() if arg.startswith("--")] + ["--model", "--effort"]
    full = "".join("  " + flag + " <x>\n" for flag in flags)
    missing = "".join("  " + flag + "\n" for flag in flags[1:])
    for version, help_text, expected in (("2.1.305", full, True), ("2.1.306", missing, False),
                                         ("2.1.200", full, False), ("2.1.289", full, True)):
        monkeypatch.setattr(claude, "_flag_proofs", {})
        def status(command, args, timeout, text=help_text, version=version):
            if args == ["--version"]:
                return version + " (Claude Code)"
            if args == ["--help"]:
                return text
            raise DiscoveryError("command_failed")
        monkeypatch.setattr(claude, "run_status", status)
        discovery = ClaudeAdapter(("fixture",), timeout=5).discover()
        assert discovery.version == version and discovery.compatible is expected


def test_claude_catalog_keeps_only_newest_family_aliases():
    from HiveMind.backend.adapters.claude import _parse_controls
    models = [{"value": name, "supportedEffortLevels": ["high"]} for name in
              ("default", "opus", "sonnet", "fable", "haiku", "claude-fable-5", "claude-opus-4-8")]
    usage = {"behaviors": None, "subscription_type": "max", "rate_limits_available": True,
             "rate_limits": {"five_hour": {"utilization": 1}, "seven_day": {"utilization": 1},
                             "extra_usage": {"is_enabled": False}}}
    parsed = _parse_controls({"hivemind-init": {"models": models}, "hivemind-settings": {"effective": {}},
                              "hivemind-usage": usage})
    assert [model.name for model in parsed[0]] == ["opus", "sonnet", "haiku"]


def _alive(pid):
    import subprocess
    listing = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
    return str(pid) in listing


@pytest.mark.skipif(sys.platform != "win32", reason="Hub runs under pythonw only on Windows")
def test_launcher_hands_pipes_to_cli_when_started_without_console(tmp_path):
    import subprocess
    echo = tmp_path / "echo.py"
    echo.write_text("import sys\nfor line in sys.stdin:\n    sys.stdout.write(line)\n    sys.stdout.flush()\n",
                    encoding="utf-8")
    code = ("import sys; sys.path.insert(0, %r)\n"
            "from HiveMind.backend.adapters import launcher\n"
            "launcher.provider_command = lambda provider: (%r, %r)\n"
            "sys.exit(launcher.main(['codex', 'app-server', '--stdio']))\n"
            % (str(Path(__file__).resolve().parents[1]), sys.executable, str(echo)))
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    process = subprocess.Popen([str(pythonw), "-B", "-c", code], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        output = process.communicate('{"ping": 1}\n', timeout=30)[0]
    finally:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    assert output == '{"ping": 1}\n'
    assert process.returncode == 0


@pytest.mark.skipif(sys.platform != "win32", reason="process tree cleanup is Windows-specific")
def test_close_kills_orphaned_cli_after_failed_start(tmp_path):
    import subprocess
    import time
    pid_file = tmp_path / "grandchild.pid"
    holder = tmp_path / "holder.py"
    holder.write_text(
        "import pathlib, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'],\n"
        "                         stdin=subprocess.DEVNULL, stdout=sys.stdout)\n"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid))\n"
        "time.sleep(120)\n", encoding="utf-8")
    rpc = DiscoveryRpc((sys.executable, str(holder)), timeout=2)
    errors = []

    def enter():
        try:
            rpc.__enter__()
        except DiscoveryError as exc:
            errors.append(str(exc))

    worker = threading.Thread(target=enter, daemon=True)
    started = time.monotonic()
    worker.start()
    worker.join(40)
    grandchild = int(pid_file.read_text()) if pid_file.exists() else None
    try:
        assert not worker.is_alive(), "close() deadlocked"
        assert errors == ["protocol_timeout"]
        assert time.monotonic() - started < 40
        assert grandchild is not None and not _alive(grandchild)
    finally:
        if grandchild is not None:
            subprocess.run(["taskkill", "/PID", str(grandchild), "/F"], capture_output=True)


@pytest.mark.skipif(sys.platform != "win32", reason="job objects are Windows-specific")
def test_close_kills_cli_left_behind_by_a_launcher_that_exited(tmp_path):
    # P3 da verificação de 25/10/2026: lançador saiu sozinho e o CLI ficou segurando o pipe.
    import subprocess
    import time
    pid_file = tmp_path / "grandchild.pid"
    holder = tmp_path / "holder.py"
    holder.write_text(
        "import pathlib, subprocess, sys\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'],\n"
        "                         stdin=subprocess.DEVNULL, stdout=sys.stdout)\n"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid))\n", encoding="utf-8")
    rpc = DiscoveryRpc((sys.executable, str(holder)), timeout=3)
    started = time.monotonic()
    try:
        with pytest.raises(DiscoveryError, match="protocol_timeout"):
            rpc.__enter__()
        grandchild = int(pid_file.read_text())
        assert time.monotonic() - started < 20
        deadline = time.monotonic() + 5
        while _alive(grandchild) and time.monotonic() < deadline:
            time.sleep(0.2)
        assert not _alive(grandchild)
    finally:
        if pid_file.exists():
            subprocess.run(["taskkill", "/PID", pid_file.read_text(), "/F"], capture_output=True)


def test_close_always_releases_job_and_job_creation_never_raises():
    # Verificação de 25/10/2026: falha no fechamento não pode deixar o job (e os descendentes) vivos.
    from types import SimpleNamespace
    from HiveMind.backend.adapters import base
    released = []
    def broken_wait(timeout=None):
        raise RuntimeError("wait failed")
    rpc = DiscoveryRpc(("fixture",))
    rpc.process = SimpleNamespace(stdin=None, stdout=None, wait=broken_wait)
    rpc._close_job = lambda: released.append(True)
    with pytest.raises(RuntimeError, match="wait failed"):
        rpc.close()
    assert released == [True] and rpc._close_job is None
    assert base._kill_on_close_job(SimpleNamespace()) is None
