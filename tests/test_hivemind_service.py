from HiveMind.backend.adapters.base import DiscoveryError
import pytest
from HiveMind.backend.service import HiveService
from HiveMind.backend.store import Conflict
from HiveMind.backend.workspaces import manifest, snapshot
from HiveMind.backend.store import digest
from test_hivemind_missions import plan


def test_presence_waits_for_all_huds_and_grace_and_never_auto_resumes(tmp_path):
    clock = [100.0]
    huds = {"one": 100.0, "two": 100.0}
    service = HiveService(tmp_path / "state", lambda: {"ever": True, "huds": dict(huds), "ttl": 90},
                          clock=lambda: clock[0], presence_grace=10)
    try:
        mission = service.missions.create("m", "create", "fixture")
        def planning(connection, current):
            current["state"] = "planning"
            return {}
        service.store.mutate("m", "planning", mission["revision"], "planning", {}, planning)
        service.check_presence()
        del huds["one"]
        service.check_presence()
        assert service.store.get("m")["state"] == "planning"
        del huds["two"]
        service.check_presence()
        clock[0] += 9
        service.check_presence()
        assert service.store.get("m")["state"] == "planning"
        clock[0] += 2
        service.check_presence()
        assert service.store.get("m")["state"] == "paused"
        huds["new"] = clock[0]
        service.check_presence()
        assert service.store.get("m")["state"] == "paused"
    finally:
        service.close()


def test_expired_heartbeat_is_reported_as_uncertain(tmp_path):
    clock = [100.0]
    huds = {"one": 100.0}
    service = HiveService(tmp_path / "state", lambda: {"ever": True, "huds": dict(huds), "ttl": 90},
                          clock=lambda: clock[0], presence_grace=10)
    try:
        mission = service.missions.create("m", "create", "fixture")
        def planning(connection, current):
            current["state"] = "planning"
            return {}
        service.store.mutate("m", "planning", mission["revision"], "planning", {}, planning)
        service.check_presence()
        clock[0] += 100
        service.check_presence()
        clock[0] += 11
        service.check_presence()
        assert service.store.get("m")["data"]["pause"]["reason"] == "presence_uncertain"
    finally:
        service.close()


def test_hub_exit_waits_for_reload_grace_and_then_pauses(tmp_path):
    clock = [100.0]
    service = HiveService(tmp_path / "state", clock=lambda: clock[0], presence_grace=10)
    try:
        mission = service.missions.create("m", "create", "fixture")
        def planning(connection, current):
            current["state"] = "planning"
            return {}
        service.store.mutate("m", "planning", mission["revision"], "planning", {}, planning)
        service.heartbeat("old")
        assert not service.hub_exit_ready()
        service.bye("old")
        assert not service.hub_exit_ready()
        clock[0] += 5
        service.heartbeat("new")
        assert not service.hub_exit_ready()
        service.bye("new")
        assert not service.hub_exit_ready()
        clock[0] += 11
        assert service.hub_exit_ready()
        assert service.store.get("m")["state"] == "paused"
    finally:
        service.close()


def test_job_uses_scoped_broker_and_distinct_verifier_session(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    import HiveMind.backend.adapters.claude as claude
    import HiveMind.backend.adapters.codex as codex
    source = tmp_path / "project"
    (source / "src").mkdir(parents=True)
    (source / "src" / "main.py").write_text("old")
    generation_path = tmp_path / "generation"
    generation_path.mkdir()
    (generation_path / "service.py").write_text("fixture runtime")
    generation_manifest = manifest(generation_path)
    generation = {"path": str(generation_path), "manifest": generation_manifest, "hash": digest(generation_manifest)}
    service = HiveService(tmp_path / "state", generation=generation)
    monkeypatch.setattr(service, "_session_started", lambda *args: None)
    sessions, prompts = [], []
    class FixtureSession:
        def __init__(self, adapter, model, effort, workspace, broker):
            self.broker, self.adapter = broker, adapter
            sessions.append(self)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def interrupt(self):
            pass
        def turn(self, prompt, output_schema=None):
            prompts.append(prompt)
            read = self.broker.dispatch("read", {"path": "src/main.py"})
            if self.adapter.role == "worker":
                self.broker.dispatch("patch", {"path": "src/main.py", "content": "new",
                                               "expected_sha256": read["sha256"]})
                return "updated"
            return json.dumps({"criteria": {"checks": "passed", "scope": "passed"}, "evidence": "Fixture read."})
    monkeypatch.setattr(claude, "ClaudeProofSession", FixtureSession)
    monkeypatch.setattr(codex, "CodexProofSession", FixtureSession)
    adapters = {"claude": SimpleNamespace(role="worker"), "codex": SimpleNamespace(role="verifier", command=("node.exe",))}
    try:
        mission = service.missions.create("m", "create", "fixture")
        proposal = plan()
        proposal["project"]["path"] = str(source)
        mission = service.missions.propose("m", "plan", mission["revision"], proposal)
        mission = service.missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
        workspace = snapshot(source, service.state_root / "workspaces", "m")
        mission = service.missions.bind_workspace("m", "bind", mission["revision"], source, workspace)
        mission = service.missions.start("m", "start", mission["revision"])
        assert service.run_job("m", "work", "worker", "one", adapters) == "updated"
        assert (source / "src" / "main.py").read_text() == "old"
        (tmp_path / "state" / "workspaces" / "m" / "notes.txt").write_text("outside the plan")
        candidate_hash = digest(manifest(workspace["path"]))
        mission = service.missions.begin_verification("m", "verify", mission["revision"], candidate_hash)
        service.run_job("m", "review", "reviewer", None, adapters)
        assert len(sessions) == 2 and sessions[0] is not sessions[1]
        assert service.store.get("m")["data"]["verdict"]["passed"] is True
        # B5 de 25/10/2026: o verificador recebe do backend o escopo real das mudanças.
        evidence = json.loads(prompts[1].split("\n", 1)[1])
        assert evidence["changed_files"] == ["notes.txt", "src/main.py"]
        assert evidence["files_outside_plan"] == ["notes.txt"]
        assert "changed_files" not in prompts[0]
    finally:
        service.close()


def test_queen_plans_with_read_only_broker_before_approval(tmp_path, monkeypatch):
    import json
    import threading
    from types import SimpleNamespace
    import HiveMind.backend.adapters.codex as codex
    source = tmp_path / "project"
    (source / "src").mkdir(parents=True)
    (source / "src" / "main.py").write_text("old")
    generation_path = tmp_path / "generation"
    generation_path.mkdir()
    (generation_path / "service.py").write_text("fixture runtime")
    contents = manifest(generation_path)
    response_ready = threading.Event()
    proposal = plan()
    proposal["project"]["path"] = str(source)
    proposal["bees"][1]["temporary"] = False
    class FixtureSession:
        def __init__(self, adapter, model, effort, workspace, broker):
            self.broker = broker
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def interrupt(self):
            pass
        def turn(self, prompt, output_schema=None):
            assert self.broker.dispatch("read", {"path": "src/main.py"})["content"] == "old"
            from HiveMind.backend.capabilities import ToolNotAllowed
            with pytest.raises(ToolNotAllowed):
                self.broker.dispatch("patch", {"path": "src/main.py", "content": "new", "expected_sha256": None})
            response_ready.set()
            return json.dumps({"plan": proposal})
    monkeypatch.setattr(codex, "CodexProofSession", FixtureSession)
    service = HiveService(tmp_path / "state", generation={"path": str(generation_path), "manifest": contents,
                          "hash": digest(contents)}, adapters={"codex": SimpleNamespace()})
    monkeypatch.setattr(service, "_session_started", lambda *args: None)
    try:
        service.heartbeat("one")
        service.store.set_configured_bees(proposal["bees"], "roster", 0)
        mission = service.missions.create("m", "create", "fixture")
        service.ask_queen("m", "ask", mission["revision"], source, proposal["bees"][0], "update fixture")
        assert response_ready.wait(5)
        for _ in range(100):
            mission = service.store.get("m")
            if mission["state"] == "awaiting_plan_approval":
                break
            threading.Event().wait(0.01)
        assert mission["state"] == "awaiting_plan_approval"
        assert mission["data"]["approved_plan_hash"] is None
        assert (source / "src" / "main.py").read_text() == "old"
        assert service.ask_queen("m", "ask", 0, source, proposal["bees"][0], "update fixture")["state"] == "awaiting_plan_approval"
    finally:
        service.close()


def test_planning_result_remains_strict_and_reports_only_allowlisted_local_reason(tmp_path, monkeypatch):
    import json
    import threading
    from types import SimpleNamespace
    import HiveMind.backend.adapters.codex as codex
    source = tmp_path / "project"
    source.mkdir()
    generation_path = tmp_path / "generation"
    generation_path.mkdir()
    (generation_path / "service.py").write_text("fixture runtime")
    contents = manifest(generation_path)
    proposal = plan()
    proposal["project"]["path"] = str(source)
    proposal["bees"][1]["temporary"] = False
    replies = [json.dumps({"plan": proposal}), "```json\n{}\n```",
               json.dumps({"plan": {**proposal, "project": str(source)}})]
    class FixtureSession:
        def __init__(self, *args):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def interrupt(self):
            pass
        def turn(self, prompt, output_schema=None):
            return replies.pop(0)
    monkeypatch.setattr(codex, "CodexProofSession", FixtureSession)
    service = HiveService(tmp_path / "state", generation={"path": str(generation_path), "manifest": contents,
                          "hash": digest(contents)}, adapters={"codex": SimpleNamespace()})
    monkeypatch.setattr(service, "_session_started", lambda *args: None)
    try:
        service.heartbeat("one")
        service.store.set_configured_bees(proposal["bees"], "roster", 0)
        mission = service.missions.create("m", "create", "fixture")
        service.ask_queen("m", "first", mission["revision"], source, proposal["bees"][0], "fixture")
        for _ in range(100):
            if service.store.get("m")["state"] == "awaiting_plan_approval":
                break
            threading.Event().wait(0.01)
        assert service.store.get("m")["state"] == "awaiting_plan_approval"
        invalid = service.missions.create("invalid", "create-invalid", "fixture")
        service.ask_queen("invalid", "second", invalid["revision"], source, proposal["bees"][0], "fixture")
        for _ in range(100):
            if service.store.get("invalid")["state"] == "awaiting_user":
                break
            threading.Event().wait(0.01)
        events = service.store.events("invalid")
        error = [item for item in events if item["kind"] == "job_error"][-1]
        assert error["data"]["reason"] == "planning_result_invalid"
        assert service.store.get("invalid")["state"] == "awaiting_user"
        shape = service.missions.create("shape", "create-shape", "fixture")
        service.ask_queen("shape", "third", shape["revision"], source, proposal["bees"][0], "fixture")
        for _ in range(100):
            if service.store.get("shape")["state"] == "awaiting_user":
                break
            threading.Event().wait(0.01)
        shaped = [item for item in service.store.events("shape") if item["kind"] == "job_error"][-1]
        assert shaped["data"]["reason"] == "planning_result_invalid"
    finally:
        service.close()


def test_failure_reason_never_exposes_untrusted_provider_text(tmp_path):
    service = HiveService(tmp_path / "state")
    try:
        mission = service.missions.create("m", "create", "fixture")
        def planning(connection, current):
            current["state"] = "planning"
            return {}
        service.store.mutate("m", "planning", mission["revision"], "planning", {}, planning)
        service._fail_job("m", "job", DiscoveryError("provider private message"))
        assert service.store.events("m")[-2]["data"]["reason"] == "job_failed"
    finally:
        service.close()


def test_dispatcher_respects_global_limit_and_does_not_duplicate_pending_jobs(tmp_path, monkeypatch):
    from copy import deepcopy
    import threading
    source = tmp_path / "project"
    source.mkdir()
    service = HiveService(tmp_path / "state", adapters={"fixture": object()})
    gate, both, completed = threading.Event(), threading.Event(), threading.Event()
    lock, started, finished = threading.Lock(), [], []
    try:
        service.heartbeat("hud")
        mission = service.missions.create("m", "create", "fixture")
        proposal = plan()
        proposal["project"]["path"] = str(source)
        bee = deepcopy(proposal["bees"][1])
        bee["id"] = "other"
        proposal["bees"].append(bee)
        task = deepcopy(proposal["tasks"][0])
        task.update({"id": "two", "bee_id": "other", "files": ["src/other.py"]})
        proposal["tasks"].append(task)
        mission = service.missions.propose("m", "plan", mission["revision"], proposal)
        mission = service.missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
        workspace = snapshot(source, service.state_root / "workspaces", "m")
        mission = service.missions.bind_workspace("m", "bind", mission["revision"], source, workspace)
        service.missions.start("m", "start", mission["revision"])
        def fake_job(mission_id, job_id, bee_id, task_id, adapters):
            service.scheduler.reserve(mission_id, job_id, bee_id, task_id)
            with lock:
                started.append(task_id)
                if len(started) == 2:
                    both.set()
            gate.wait(5)
            service.scheduler.finish(job_id, True)
            with lock:
                finished.append(task_id)
                if len(finished) == 2:
                    completed.set()
        monkeypatch.setattr(service, "run_job", fake_job)
        service.advance()
        assert both.wait(5)
        service.advance()
        assert sorted(started) == ["one", "two"]
        gate.set()
        assert completed.wait(5)
    finally:
        gate.set()
        service.close()


def test_queen_coordinates_failed_verdict_before_worker_and_persists_feedback(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    import HiveMind.backend.adapters.claude as claude
    import HiveMind.backend.adapters.codex as codex
    from HiveMind.backend.store import Conflict
    source = tmp_path / "project"
    (source / "src").mkdir(parents=True)
    (source / "src" / "main.py").write_text("old")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "service.py").write_text("fixture")
    contents = manifest(runtime)
    service = HiveService(tmp_path / "state", generation={"path": str(runtime), "manifest": contents,
                          "hash": digest(contents)})
    monkeypatch.setattr(service, "_session_started", lambda *args: None)
    prompts = []
    class FixtureSession:
        def __init__(self, adapter, model, effort, workspace, broker):
            self.adapter, self.broker = adapter, broker
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def interrupt(self):
            pass
        def turn(self, prompt, output_schema=None):
            prompts.append((self.adapter.role, prompt))
            if self.adapter.role == "queen":
                assert "failed evidence" in prompt
                return "Check src/main.py and preserve the approved scope."
            assert "Check src/main.py" in prompt
            current = self.broker.dispatch("read", {"path": "src/main.py"})
            self.broker.dispatch("patch", {"path": "src/main.py", "content": "fixed", "expected_sha256": current["sha256"]})
            return "fixed"
    monkeypatch.setattr(codex, "CodexProofSession", FixtureSession)
    monkeypatch.setattr(claude, "ClaudeProofSession", FixtureSession)
    adapters = {"codex": SimpleNamespace(role="queen", command=("node.exe",)),
                "claude": SimpleNamespace(role="worker")}
    try:
        mission = service.missions.create("m", "create", "fixture")
        proposal = plan()
        proposal["project"]["path"] = str(source)
        mission = service.missions.propose("m", "plan", mission["revision"], proposal)
        mission = service.missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
        workspace = snapshot(source, service.state_root / "workspaces", "m")
        mission = service.missions.bind_workspace("m", "bind", mission["revision"], source, workspace)
        mission = service.missions.start("m", "start", mission["revision"])
        candidate = digest(manifest(workspace["path"]))
        mission = service.missions.begin_verification("m", "verify", mission["revision"], candidate)
        mission = service.missions.record_verdict("m", "failed", mission["revision"], candidate, "reviewer",
                                                   {"checks": "failed", "scope": "passed"}, "failed evidence")
        with pytest.raises(Conflict, match="correction_not_ready"):
            service.scheduler.reserve("m", "too-early", "worker", "one")
        launched = []
        original_launch = service._launch
        monkeypatch.setattr(service, "_launch", lambda key, mission_id, bee_id, task_id: launched.append((bee_id, task_id)))
        service.adapters = adapters
        service.heartbeat("hud")
        service.advance()
        assert launched == [("queen", None)]
        monkeypatch.setattr(service, "_launch", original_launch)
        assert service.run_job("m", "queen-job", "queen", None, adapters).startswith("Check")
        current = service.store.get("m")
        assert current["data"]["correction"]["status"] == "coordinated"
        assert current["data"]["correction"]["feedback"].startswith("Check")
        assert service.run_job("m", "worker-job", "worker", "one", adapters) == "fixed"
        assert [role for role, _ in prompts] == ["queen", "worker"]
    finally:
        service.close()


def test_start_after_ceiling_without_new_cycle_is_refused_before_any_snapshot(tmp_path):
    source = tmp_path / "project"
    (source / "src").mkdir(parents=True)
    (source / "src" / "main.py").write_text("old")
    generation_path = tmp_path / "generation"
    generation_path.mkdir()
    (generation_path / "service.py").write_text("fixture runtime")
    contents = manifest(generation_path)
    service = HiveService(tmp_path / "state", generation={"path": str(generation_path), "manifest": contents,
                                                          "hash": digest(contents)})
    try:
        service.heartbeat("hud")
        mission = service.missions.create("m", "create", "fixture", 1)
        proposal = plan()
        proposal["project"]["path"] = str(source)
        mission = service.missions.propose("m", "plan", mission["revision"], proposal)
        mission = service.missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
        workspace = snapshot(source, service.state_root / "workspaces", "first")
        mission = service.missions.bind_workspace("m", "bind", mission["revision"], source, workspace)
        mission = service.missions.start("m", "start", mission["revision"])
        mission = service.missions.begin_verification("m", "verify", mission["revision"], "a" * 64)
        mission = service.missions.record_verdict("m", "reject", mission["revision"], "a" * 64, "reviewer",
                                                   {"checks": "failed", "scope": "passed"}, "fix needed")
        mission = service.missions.set_cycle_limit("m", "raise", mission["revision"], 2)
        mission = service.missions.propose("m", "again", mission["revision"], mission["data"]["plan"])
        mission = service.missions.approve_plan("m", "approve-again", mission["revision"], mission["data"]["plan_hash"])
        mission = service.missions.set_cycle_limit("m", "lower", mission["revision"], 1)
        with pytest.raises(Conflict, match="cycle_limit_reached"):
            service.start_mission("m", "start-again", mission["revision"])
        current = service.store.get("m")
        assert current["state"] == "ready" and current["data"].get("workspace") is None
        assert [path.name for path in (service.state_root / "workspaces").iterdir()] == ["first"]
    finally:
        service.close()


@pytest.mark.parametrize("message, reason", [
    ("turn_failed:usageLimitExceeded", "turn_failed:usageLimitExceeded"),
    ("turn_failed:unknown", "turn_failed:unknown"),
    ("turn_failed:httpConnectionFailed", "turn_failed:httpConnectionFailed"),
    ("turn_failed:httpConnectionFailed:503", "turn_failed:httpConnectionFailed:503"),
    ("turn_failed:responseStreamDisconnected:429", "turn_failed:responseStreamDisconnected:429"),
    ("turn_failed:httpConnectionFailed:99", "job_failed"),
    ("turn_failed:httpConnectionFailed:0503", "job_failed"),
    ("turn_failed:usageLimitExceeded:503", "job_failed"),
    ("turn_failed:private provider text", "job_failed"),
    ("turn_failed:claude:error_max_turns", "turn_failed:claude:error_max_turns"),
    ("turn_failed:claude:error_during_execution", "turn_failed:claude:error_during_execution"),
    ("turn_failed:claude:api_error_429", "turn_failed:claude:api_error_429"),
    ("turn_failed:claude:unknown", "turn_failed:claude:unknown"),
    ("turn_failed:claude:api_error_99", "job_failed"),
    ("turn_failed:claude:private provider text", "job_failed"),
    ("turn_failed", "job_failed"),
])
def test_failure_reason_keeps_only_closed_turn_categories(message, reason):
    from HiveMind.backend.service import _failure_reason
    assert _failure_reason(DiscoveryError(message)) == reason


def test_structured_outputs_are_closed_schemas():
    from HiveMind.backend.service import _QUEEN_OUTPUT, _verdict_output
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert sorted(node["required"]) == sorted(node["properties"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(_QUEEN_OUTPUT)
    verdict = _verdict_output([{"id": "a"}, {"id": "b"}])
    walk(verdict)
    assert sorted(verdict["properties"]["criteria"]["properties"]) == ["a", "b"]


def test_abandoned_mission_is_ignored_by_exit_recovery_and_dispatch(tmp_path):
    service = HiveService(tmp_path / "state", adapters={})
    try:
        mission = service.missions.create("m", "create", "fixture")
        def stuck(connection, current):
            current["state"] = "recovery_required"
            return {}
        mission = service.store.mutate("m", "stuck", mission["revision"], "recovery_required", {}, stuck)
        mission = service.missions.abandon("m", "abandon", mission["revision"], service.delivery.journal_root)
        assert service.active_missions() == [] and service.hub_exit_ready() and service.ready_to_exit()
        service.heartbeat("hud")
        service.advance()
        service.request_pause_all()
        service.close()
        reopened = HiveService(tmp_path / "state")
        try:
            assert reopened.store.recover_interrupted() == 0
            current = reopened.store.get("m")
            assert current["state"] == "abandoned" and current["revision"] == mission["revision"]
        finally:
            reopened.close()
    finally:
        service.close()


_ADAPTER_SOURCES = ("base.py", "claude.py", "codex.py")


def _adapter_literals():
    import re
    from pathlib import Path
    import HiveMind.backend.adapters as adapters
    text = "".join((Path(adapters.__file__).parent / name).read_text(encoding="utf-8") for name in _ADAPTER_SOURCES)
    return (set(re.findall(r'DiscoveryError\("([a-z_]+)"\)', text)),
            set(re.findall(r'DiscoveryError\("([a-z_]+):"', text)))


def test_failure_reason_lists_cover_every_fixed_adapter_code():
    from HiveMind.backend.service import _ADAPTER_FAILURES, _PREFIXED_FAILURES, _TURN_FAILURES
    fixed, prefixed = _adapter_literals()
    assert fixed == _TURN_FAILURES | _ADAPTER_FAILURES
    assert prefixed - {"gate", "turn_failed"} == set(_PREFIXED_FAILURES)


def test_failure_reason_records_each_adapter_code_as_itself_and_drops_suffixes():
    from HiveMind.backend.service import _failure_reason
    fixed, prefixed = _adapter_literals()
    for code in fixed:
        assert _failure_reason(DiscoveryError(code)) == code
    for code in ("thread_controls_unverified", "protocol_request_failed"):
        assert code in prefixed
        assert _failure_reason(DiscoveryError(code + ":private:roots_x:detail")) == code
    assert _failure_reason(DiscoveryError("protocol_request_failed:thread/start:-32600:invalid")) == "protocol_request_failed"
    assert _failure_reason(DiscoveryError("thread_controls_unverified:sandbox,approval:roots_two")) == "thread_controls_unverified"


@pytest.mark.parametrize("message", [
    "context_unverified extra", "context_unverified:private", "Context_unverified", " context_unverified",
    "thread_controls_unverified", "thread_controls_unverifiedX:a", "protocol_request_failed", "provider private message",
    "catalog_pagination_", "gate:private", "", "xcommand_failed",
])
def test_failure_reason_never_records_text_outside_the_lists(message):
    from HiveMind.backend.service import _failure_reason
    assert _failure_reason(DiscoveryError(message)) == "job_failed"
    assert _failure_reason(ValueError("context_unverified")) == "job_failed"
