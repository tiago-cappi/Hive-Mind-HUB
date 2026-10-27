"""Cadastro rico de abelhas, ferramentas por abelha, progress e resumo por abelha (VR-01 a VR-03)."""

from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace

from flask import Flask
import pytest

import HiveMind.backend.routes as routes
from HiveMind.backend.bees import profile_gaps
from HiveMind.backend.capabilities import PauseRequested, ToolBroker, ToolNotAllowed
from HiveMind.backend.missions import validate_plan
from HiveMind.backend.service import HiveService
from HiveMind.backend.store import Conflict, Store, digest
from HiveMind.backend.workspaces import manifest, snapshot
from test_hivemind_missions import plan


def rich(bee_id, role, **extra):
    tools = ["read", "checks"] if role in {"queen", "verifier"} else ["read", "patch", "checks"]
    return {"id": bee_id, "role": role, "provider": "codex", "model": "fixture", "effort": "high", "temporary": False,
            "description": "Does " + role + " work", "skills": {"tags": ["python"], "instructions": "Be careful."},
            "tools": tools, **extra}


def roster():
    return [rich("queen", "queen"), rich("worker1", "worker"), rich("verifier", "verifier")]


@pytest.mark.parametrize("provider", ["codex", "claude"])
@pytest.mark.parametrize("configured", ["read", "checks", "legacy"])
def test_planning_broker_obeys_queen_registry(tmp_path, monkeypatch, provider, configured):
    import importlib
    module = importlib.import_module("HiveMind.backend.adapters." + provider)
    team = roster()
    queen = team[0]
    queen["provider"] = provider
    if configured == "legacy":
        queen.pop("tools")
    else:
        queen["tools"] = [configured]
    source = tmp_path / "project"
    source.mkdir()
    (source / "note.txt").write_text("original", encoding="utf-8")
    calls = []
    class FixtureSession:
        def __init__(self, adapter, model, effort, workspace, broker):
            calls.append("session")
            self.broker = broker
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def interrupt(self): pass
        def turn(self, prompt, schema):
            calls.append("turn")
            assert self.broker.names == ("read",)
            assert self.broker.dispatch("read", {"path": "note.txt"})["content"] == "original"
            replies = []
            for name in ("patch", "checks", "progress"):
                self.broker.dispatch_and_reply(name, {}, lambda ok, result: replies.append((ok, result)))
            assert replies == [(False, {"error": "tool_not_allowed"})] * 3
            return json.dumps({"clarification": "Question?"})
    monkeypatch.setattr(module, "CodexProofSession" if provider == "codex" else "ClaudeProofSession", FixtureSession)
    service = HiveService(tmp_path / "state", generation=generation(tmp_path), adapters={provider: SimpleNamespace()})
    monkeypatch.setattr(service, "_session_started", lambda *args: None)
    try:
        service.missions.create("m", "create", "fixture")
        service.missions.request_planning("m", "ask", 0, source, queen, "fixture", team)
        service.scheduler.reserve_planning("m", "plan")
        service._plan_job("m", "plan")
        if configured == "checks":
            assert calls == []
            errors = [event for event in service.store.events("m") if event["kind"] == "job_error"]
            assert errors[-1]["data"]["reason"] == "planning_read_required"
        else:
            assert calls == ["session", "turn"]
            assert service.store.get("m")["state"] == "clarifying"
        assert (source / "note.txt").read_text(encoding="utf-8") == "original"
    finally:
        service.close()


LEGACY = [{"id": "queen", "role": "queen", "provider": "codex", "model": "fixture", "effort": "high", "temporary": False},
          {"id": "worker1", "role": "worker", "provider": "codex", "model": "fixture", "effort": "high", "temporary": False},
          {"id": "verifier", "role": "verifier", "provider": "codex", "model": "fixture", "effort": "high", "temporary": False}]


def seed_legacy(store, bees=LEGACY):
    with sqlite3.connect(str(store.path)) as connection:
        connection.execute("UPDATE roster_settings SET data=?,revision=1 WHERE id=1", (json.dumps(bees),))


# ---- B01: regras do cadastro -------------------------------------------------------------------

@pytest.mark.parametrize("change, gaps", [
    ({}, []),
    ({"description": ""}, ["description"]), ({"description": "   "}, ["description"]),
    ({"description": "x" * 2001}, ["description"]), ({"description": "x" * 2000}, []),
    ({"description": 5}, ["description"]),
    ({"skills": {"tags": ["a"] * 21, "instructions": ""}}, ["skills"]),
    ({"skills": {"tags": ["a"] * 20, "instructions": ""}}, []),
    ({"skills": {"tags": ["x" * 61], "instructions": ""}}, ["skills"]),
    ({"skills": {"tags": ["x" * 60]}}, []),
    ({"skills": {"tags": [""], "instructions": ""}}, ["skills"]),
    ({"skills": {"tags": [3], "instructions": ""}}, ["skills"]),
    ({"skills": {"tags": [], "instructions": "x" * 4001}}, ["skills"]),
    ({"skills": {"tags": [], "instructions": "x" * 4000}}, []),
    ({"skills": {"instructions": ""}}, ["skills"]), ({"skills": {"tags": [], "other": 1}}, ["skills"]),
    ({"skills": ["python"]}, ["skills"]),
    ({"tools": ["read", "shell"]}, ["tools"]), ({"tools": ["read", "read"]}, ["tools"]),
    ({"tools": "read"}, ["tools"]), ({"tools": [["read"]]}, ["tools"]), ({"tools": []}, []),
    ({"tools": ["progress"]}, ["tools"]),
])
def test_profile_gaps_apply_the_documented_limits(change, gaps):
    assert profile_gaps({**rich("worker1", "worker"), **change}) == gaps


def test_profile_gaps_report_every_missing_field_and_forbid_patch_for_queen_and_verifier():
    assert profile_gaps(LEGACY[1]) == ["description", "skills", "tools"]
    assert profile_gaps({**rich("v", "verifier"), "tools": ["read", "patch"]}) == ["tools"]
    assert profile_gaps({**rich("q", "queen"), "tools": ["patch"]}) == ["tools"]
    assert profile_gaps({**rich("s", "subagent"), "tools": ["patch"]}) == []


def test_roster_saves_the_rich_registry_and_fills_optional_instructions(tmp_path):
    store = Store(tmp_path / "hive.db")
    bees = roster()
    bees[0]["skills"] = {"tags": ["planning"]}
    saved = store.set_configured_bees(bees, "roster", 0)
    assert saved["revision"] == 1 and saved["incomplete"] == []
    assert saved["bees"][0]["skills"] == {"tags": ["planning"], "instructions": ""}
    assert store.configured_bees() == {"bees": saved["bees"], "revision": 1, "incomplete": []}


def test_roster_refuses_a_new_incomplete_bee_naming_bee_and_field(tmp_path):
    store = Store(tmp_path / "hive.db")
    bees = roster()
    del bees[1]["description"]
    with pytest.raises(ValueError) as caught:
        store.set_configured_bees(bees, "roster", 0)
    assert caught.value.detail == {"bee": "worker1", "field": "description"}
    bees = roster()
    bees[2]["tools"] = ["read", "patch"]
    with pytest.raises(ValueError) as caught:
        store.set_configured_bees(bees, "roster", 0)
    assert caught.value.detail == {"bee": "verifier", "field": "tools"}
    assert store.configured_bees()["bees"] == []


def test_old_roster_loads_as_incomplete_and_unchanged_old_bees_may_stay_while_others_are_completed(tmp_path):
    store = Store(tmp_path / "hive.db")
    seed_legacy(store)
    current = store.configured_bees()
    assert current["bees"] == LEGACY and current["revision"] == 1
    assert current["incomplete"] == [{"id": bee["id"], "missing": ["description", "skills", "tools"]} for bee in LEGACY]
    # Completar só a Rainha: as outras seguem iguais ao salvo e continuam incompletas.
    saved = store.set_configured_bees([rich("queen", "queen"), LEGACY[1], LEGACY[2]], "step", 1)
    assert [item["id"] for item in saved["incomplete"]] == ["worker1", "verifier"]
    # Uma abelha alterada, mesmo que antiga, precisa vir completa.
    with pytest.raises(ValueError):
        store.set_configured_bees([rich("queen", "queen"), {**LEGACY[1], "model": "other"}, LEGACY[2]], "bad", 2)


def test_status_route_reports_incomplete_bees(tmp_path, monkeypatch):
    service = HiveService(tmp_path / "state")
    service.adapters = {}
    monkeypatch.setattr(routes, "get_service", lambda: service)
    app = Flask(__name__)
    app.register_blueprint(routes.blueprint)
    client = app.test_client()
    headers = {"Origin": "http://localhost"}
    try:
        seed_legacy(service.store)
        body = client.get("/hive-api/status").get_json()
        assert body["roster"]["incomplete"][1] == {"id": "worker1", "missing": ["description", "skills", "tools"]}
        bad = roster()
        bad[1]["description"] = ""
        response = client.post("/hive-api/settings", headers=headers,
                               json={"kind": "roster", "bees": bad, "key": "k", "revision": 1})
        assert response.status_code == 400
        assert response.get_json() == {"error": "invalid_request", "bee": "worker1", "field": "description"}
        good = client.post("/hive-api/settings", headers=headers,
                           json={"kind": "roster", "bees": roster(), "key": "k2", "revision": 1})
        assert good.status_code == 200 and good.get_json()["incomplete"] == []
        assert client.get("/hive-api/status").get_json()["roster"]["incomplete"] == []
    finally:
        service.close()


def generation(tmp_path):
    path = tmp_path / "generation"
    path.mkdir()
    (path / "service.py").write_text("fixture runtime")
    contents = manifest(path)
    return {"path": str(path), "manifest": contents, "hash": digest(contents)}


def test_planning_with_an_incomplete_team_is_refused_naming_the_bee(tmp_path, monkeypatch):
    source = tmp_path / "project"
    source.mkdir()
    service = HiveService(tmp_path / "state", generation=generation(tmp_path), adapters={"codex": SimpleNamespace()})
    monkeypatch.setattr(routes, "get_service", lambda: service)
    app = Flask(__name__)
    app.register_blueprint(routes.blueprint)
    client = app.test_client()
    headers = {"Origin": "http://localhost"}
    try:
        service.heartbeat("hud")
        seed_legacy(service.store, [roster()[0], LEGACY[1], roster()[2]])
        mission = service.missions.create("m", "create", "fixture")
        with pytest.raises(Conflict, match="^roster_incomplete$") as caught:
            service.ask_queen("m", "ask", mission["revision"], source, roster()[0], "go")
        assert caught.value.detail == {"bee": "worker1", "missing": ["description", "skills", "tools"]}
        assert service.store.get("m")["state"] == "draft"
        assert client.post("/hive-api/missions/m/lease", json={"owner": "tab"}, headers=headers).status_code == 200
        response = client.post("/hive-api/missions/m/command", headers=headers, json={
            "owner": "tab", "action": "ask", "key": "ask2", "revision": 0, "source": str(source),
            "queen": roster()[0], "message": "go"})
        assert response.status_code == 409
        assert response.get_json() == {"error": "roster_incomplete", "bee": "worker1",
                                       "missing": ["description", "skills", "tools"]}
        # Sem cadastro, a Rainha enviada vale sozinha, mas também precisa estar completa.
        seed_legacy(service.store, [])
        with pytest.raises(Conflict, match="^roster_incomplete$") as caught:
            service.ask_queen("m", "ask3", mission["revision"], source, LEGACY[0], "go")
        assert caught.value.detail["bee"] == "queen"
    finally:
        service.close()


def test_plan_validation_requires_the_same_fields_for_every_bee_including_temporary():
    complete = plan()
    assert validate_plan(complete)
    for field in ("description", "skills", "tools"):
        broken = deepcopy(complete)
        del broken["bees"][1][field]
        with pytest.raises(ValueError) as caught:
            validate_plan(broken)
        assert caught.value.detail == {"bee": "worker", "field": field}
    broken = deepcopy(complete)
    broken["bees"][2]["tools"] = ["read", "patch"]
    with pytest.raises(ValueError):
        validate_plan(broken)


def test_queen_schema_and_planning_prompt_carry_the_registry(tmp_path, monkeypatch):
    import threading
    import HiveMind.backend.adapters.codex as codex
    from HiveMind.backend.service import _QUEEN_OUTPUT
    bee = _QUEEN_OUTPUT["properties"]["plan"]["anyOf"][1]["properties"]["bees"]["items"]
    assert {"description", "skills", "tools"} <= set(bee["properties"])
    assert set(bee["properties"]["skills"]["properties"]) == {"tags", "instructions"}
    source = tmp_path / "project"
    source.mkdir()
    proposal = plan()
    proposal["project"]["path"] = str(source)
    proposal["bees"][1]["temporary"] = False
    prompts = []

    class Session:
        def __init__(self, *args):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def interrupt(self):
            pass
        def turn(self, prompt, output_schema=None):
            prompts.append(prompt)
            # A Rainha devolve a equipe com a ordem das ferramentas e das tags trocada: continua a mesma.
            echoed = deepcopy(proposal)
            echoed["bees"][1]["tools"].reverse()
            return json.dumps({"plan": echoed})
    monkeypatch.setattr(codex, "CodexProofSession", Session)
    service = HiveService(tmp_path / "state", generation=generation(tmp_path), adapters={"codex": SimpleNamespace()})
    monkeypatch.setattr(service, "_session_started", lambda *args: None)
    try:
        service.heartbeat("hud")
        service.store.set_configured_bees(proposal["bees"], "roster", 0)
        mission = service.missions.create("m", "create", "fixture")
        service.ask_queen("m", "ask", mission["revision"], source, proposal["bees"][0], "go")
        for _ in range(200):
            if service.store.get("m")["state"] == "awaiting_plan_approval":
                break
            threading.Event().wait(0.01)
        assert service.store.get("m")["state"] == "awaiting_plan_approval"
        text = prompts[0]
        assert "Edits the main module" in text and "Keep changes small." in text and '"tools"' in text
        assert "Prefer the supplied permanent bees" in text and "temporary bee only when none fits" in text
        # O plano guardado usa o cadastro exato (ordem original das ferramentas).
        assert service.store.get("m")["data"]["plan"]["bees"][1]["tools"] == ["read", "patch", "checks"]
    finally:
        service.close()


# ---- B02/B03: broker --------------------------------------------------------------------------

def test_broker_accepts_the_job_tool_set_and_refuses_anything_else_at_construction():
    for names in (("read",), ("read", "progress"), ("read", "patch", "checks", "progress"), ("progress",)):
        assert ToolBroker({name: lambda args: None for name in names}).names == tuple(
            name for name in ("read", "patch", "checks", "progress") if name in names)
    for bad in ({}, {"shell": lambda args: None}, {"read": "not callable"}, {"read": lambda a: None, "write": lambda a: None}):
        with pytest.raises(ValueError):
            ToolBroker(bad)


def test_broker_refuses_a_known_tool_outside_the_job_list_without_calling_it():
    called, replies = [], []
    broker = ToolBroker({"read": lambda args: called.append("read") or "ok", "progress": lambda args: called.append("progress")})
    for name in ("patch", "checks"):
        broker.dispatch_and_reply(name, {"path": "a"}, lambda ok, value: replies.append((ok, value)))
        with pytest.raises(ToolNotAllowed):
            broker.dispatch(name, {})
    assert replies == [(False, {"error": "tool_not_allowed"})] * 2 and called == []
    # Ferramenta que nem existe no catálogo mantém a recusa antiga.
    with pytest.raises(ToolNotAllowed):
        broker.dispatch_and_reply("shell", {}, lambda ok, value: None)
    with pytest.raises(ToolNotAllowed):
        broker.dispatch_and_reply(["read"], {}, lambda ok, value: None)
    broker.dispatch_and_reply("read", {}, lambda ok, value: replies.append((ok, value)))
    assert called == ["read"] and replies[-1] == (True, "ok")


def test_a_refusal_still_obeys_pause_admission():
    broker = ToolBroker({"read": lambda args: None})
    assert broker.admission.request_pause() and broker.admission.drained()
    with pytest.raises(PauseRequested):
        broker.dispatch_and_reply("patch", {}, lambda ok, value: None)


def test_codex_turn_refuses_a_tool_outside_the_list_and_keeps_the_job(monkeypatch):
    import HiveMind.backend.capabilities as capabilities
    from test_hivemind_adapter_turns import FakeRpc, session
    from HiveMind.backend.adapters.codex import CodexProofSession
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    called = []
    broker = ToolBroker({"read": lambda args: called.append(args) or {"content": "fixture"}})
    rpc = FakeRpc([
        {"id": 1, "result": {"turn": {"id": "t"}}},
        {"id": "c1", "method": "item/tool/call", "params": {"threadId": "thread", "turnId": "t", "tool": "patch",
                                                                "arguments": {"path": "a", "content": "x", "expected_sha256": None}}},
        {"id": "c2", "method": "item/tool/call", "params": {"threadId": "thread", "turnId": "t", "tool": "read",
                                                                "arguments": {"path": "a"}}},
        {"method": "item/completed", "params": {"threadId": "thread", "turnId": "t", "item": {"type": "agentMessage", "text": "done"}}},
        {"method": "turn/completed", "params": {"threadId": "thread", "turn": {"id": "t", "status": "completed"}}},
    ])
    codex = session(CodexProofSession, broker, rpc)
    codex.thread_id, codex._turn_id, codex._turn_starting = "thread", None, False
    assert codex.turn("fixture") == "done"
    refusal, ok = rpc.sent[1]["result"], rpc.sent[2]["result"]
    assert refusal["success"] is False and json.loads(refusal["contentItems"][0]["text"]) == {"error": "tool_not_allowed"}
    assert ok["success"] is True and called == [{"path": "a"}]


def test_claude_turn_refuses_a_tool_outside_the_list_and_keeps_the_job(monkeypatch):
    import HiveMind.backend.capabilities as capabilities
    from test_hivemind_adapter_turns import FakeRpc, session
    from HiveMind.backend.adapters.claude import ClaudeProofSession
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    broker = ToolBroker({"read": lambda args: {"content": "fixture"}, "progress": lambda args: {"recorded": True}})
    rpc = FakeRpc([
        {"type": "result", "subtype": "success", "is_error": False,
         "result": '{"action":"patch","arguments":{"path":"a","content":"x","expected_sha256":null}}'},
        {"type": "result", "subtype": "success", "is_error": False, "result": '{"final":"done"}'},
    ])
    claude = session(ClaudeProofSession, broker, rpc)
    claude._turn_active = False
    assert claude.turn("fixture") == "done"
    assert "tool_not_allowed" in rpc.sent[1]["message"]["content"]
    # O texto de instrução só anuncia as ferramentas do job, inclusive progress.
    first = rpc.sent[0]["message"]["content"]
    assert '"read"|"progress"' in first and "progress takes" in first and "patch takes" not in first


def test_codex_session_params_advertise_only_the_requested_tools_with_progress_schema():
    from HiveMind.backend.adapters.codex import session_params
    params = session_params("fixture-model", "C:/fixture/work", ["fixture"], ("read", "progress"))
    tools = {tool["name"]: tool for tool in params["dynamicTools"]}
    assert list(tools) == ["read", "progress"]
    schema = tools["progress"]["inputSchema"]
    assert schema["required"] == ["done", "total", "note"] and schema["additionalProperties"] is False
    assert schema["properties"]["done"] == {"type": "integer"} and schema["properties"]["note"] == {"type": "string"}


# ---- jobs: ferramentas por abelha, progress e prompts ------------------------------------------

def started(tmp_path, monkeypatch, script, edit=None):
    """Missão em execução com o plano padrão; `script(role, broker, prompt)` faz o papel do modelo."""
    import HiveMind.backend.adapters.claude as claude
    import HiveMind.backend.adapters.codex as codex
    source = tmp_path / "project"
    (source / "src").mkdir(parents=True)
    (source / "src" / "main.py").write_text("old")
    service = HiveService(tmp_path / "state", generation=generation(tmp_path))
    monkeypatch.setattr(service, "_session_started", lambda *args: None)
    sessions = []

    class Session:
        def __init__(self, adapter, model, effort, workspace, broker):
            self.adapter, self.broker = adapter, broker
            sessions.append(self)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def interrupt(self):
            pass
        def turn(self, prompt, output_schema=None):
            return script(self.adapter.role, self.broker, prompt)
    monkeypatch.setattr(claude, "ClaudeProofSession", Session)
    monkeypatch.setattr(codex, "CodexProofSession", Session)
    adapters = {"claude": SimpleNamespace(role="worker"), "codex": SimpleNamespace(role="verifier", command=("node.exe",))}
    mission = service.missions.create("m", "create", "fixture")
    proposal = plan()
    proposal["project"]["path"] = str(source)
    if edit:
        edit(proposal)
    mission = service.missions.propose("m", "plan", mission["revision"], proposal)
    mission = service.missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
    workspace = snapshot(source, service.state_root / "workspaces", "m")
    mission = service.missions.bind_workspace("m", "bind", mission["revision"], source, workspace)
    mission = service.missions.start("m", "start", mission["revision"])
    return service, adapters, sessions, workspace, mission


def replies_of(broker, name, arguments):
    out = []
    broker.dispatch_and_reply(name, arguments, lambda ok, value: out.append((ok, value)))
    return out[0]


def test_each_job_broker_only_has_the_tools_of_its_bee_and_a_refusal_does_not_fail_the_job(tmp_path, monkeypatch):
    seen = {}

    def script(role, broker, prompt):
        seen[role] = broker.names
        if role == "worker":
            seen["refused"] = replies_of(broker, "patch", {"path": "src/main.py", "content": "new", "expected_sha256": None})
            seen["checks"] = replies_of(broker, "checks", {"argv": ["python"]})
            return "tried"
        return json.dumps({"criteria": {"checks": "passed", "scope": "passed"}, "evidence": "ok"})

    def edit(proposal):
        proposal["bees"][1]["tools"] = ["read", "checks"]
    service, adapters, sessions, workspace, mission = started(tmp_path, monkeypatch, script, edit)
    try:
        assert service.run_job("m", "work", "worker", "one", adapters) == "tried"
        assert seen["worker"] == ("read", "checks", "progress")
        assert seen["refused"] == (False, {"error": "tool_not_allowed"})
        assert (tmp_path / "state" / "workspaces" / "m" / "src" / "main.py").read_text() == "old"
        assert service.store.jobs("m")[0]["state"] == "succeeded"
        kinds = [item["kind"] for item in service.store.events("m")]
        assert "job_error" not in kinds
        candidate = digest(manifest(workspace["path"]))
        service.missions.begin_verification("m", "verify", service.store.get("m")["revision"], candidate)
        service.run_job("m", "review", "reviewer", None, adapters)
        assert seen["verifier"] == ("read", "checks", "progress")
    finally:
        service.close()


def test_job_tools_for_a_bee_saved_before_the_registry_keep_the_old_behaviour(tmp_path, monkeypatch):
    seen = {}

    def script(role, broker, prompt):
        seen[role] = broker.names
        return "ok"

    def edit(proposal):
        for bee in proposal["bees"]:
            for field in ("description", "skills", "tools"):
                bee.pop(field)
    service, adapters, sessions, workspace, mission = started(tmp_path, monkeypatch, script)
    try:
        # Plano antigo gravado direto: o validador atual já não o aceitaria.
        legacy = deepcopy(mission["data"]["plan"])
        edit(legacy)

        def change(connection, record):
            record["data"]["plan"] = legacy
            return {}
        service.store.mutate("m", "legacy", mission["revision"], "legacy", {}, change)
        assert service.run_job("m", "work", "worker", "one", adapters) == "ok"
        assert seen["worker"] == ("read", "patch", "checks", "progress")
        summary = service.bees_summary("m")
        assert [item["id"] for item in summary] == ["queen", "worker", "reviewer"]
        assert summary[1]["description"] == "" and summary[1]["skills"] == {"tags": [], "instructions": ""}
        assert summary[1]["tools"] == ["read", "patch", "checks"] and summary[0]["tools"] == ["read", "checks"]
    finally:
        service.close()


def test_progress_records_an_event_validates_arguments_and_never_touches_files(tmp_path, monkeypatch):
    results = []
    bad = [{"done": 3, "total": 2, "note": ""}, {"done": -1, "total": 2, "note": ""},
           {"done": 1, "total": 100001, "note": ""}, {"done": True, "total": 2, "note": ""},
           {"done": 1.0, "total": 2, "note": ""}, {"done": "1", "total": 2, "note": ""},
           {"done": 1, "total": 2, "note": "x" * 201}, {"done": 1, "total": 2, "note": "line\nbreak"},
           {"done": 1, "total": 2, "note": 7}, {"done": 1, "total": 2, "note": "", "extra": 1}, {"total": 2, "note": ""}]

    def script(role, broker, prompt):
        if role == "worker":
            before = sorted(p.name for p in (tmp_path / "state" / "workspaces" / "m" / "src").iterdir())
            results.append(replies_of(broker, "progress", {"done": 0, "total": 100000, "note": "starting"}))
            results.append(replies_of(broker, "progress", {"done": 3, "total": 4, "note": "x" * 200}))
            results.append(replies_of(broker, "progress", {"done": 1, "total": 2}))
            results.extend(replies_of(broker, "progress", arguments) for arguments in bad)
            after = sorted(p.name for p in (tmp_path / "state" / "workspaces" / "m" / "src").iterdir())
            assert before == after
            return "done"
        return json.dumps({"criteria": {"checks": "passed", "scope": "passed"}, "evidence": "ok"})
    service, adapters, sessions, workspace, mission = started(tmp_path, monkeypatch, script)
    try:
        assert service.run_job("m", "work", "worker", "one", adapters) == "done"
        assert results[:3] == [(True, {"recorded": True})] * 3
        assert all(item == (False, {"error": "tool_failed"}) for item in results[3:]) and len(results[3:]) == len(bad)
        events = [item for item in service.store.events("m") if item["kind"] == "bee_progress"]
        assert [item["data"] for item in events] == [
            {"job_id": "work", "bee_id": "worker", "done": 0, "total": 100000, "note": "starting"},
            {"job_id": "work", "bee_id": "worker", "done": 3, "total": 4, "note": "x" * 200},
            {"job_id": "work", "bee_id": "worker", "done": 1, "total": 2, "note": ""}]
        assert service.store.jobs("m")[0]["state"] == "succeeded"
        assert all(item["kind"] != "tool_completed" or item["data"]["tool"] != "progress"
                   for item in service.store.events("m"))
    finally:
        service.close()


def test_the_queen_coordination_job_has_no_progress_and_a_verifier_does(tmp_path, monkeypatch):
    seen = {}

    def script(role, broker, prompt):
        role = "queen" if prompt.startswith("Coordinate") else "verifier"
        seen[role] = (broker.names, prompt)
        if role == "queen":
            return "Guidance"
        return json.dumps({"criteria": {"checks": "failed", "scope": "passed"}, "evidence": "bad"})
    service, adapters, sessions, workspace, mission = started(tmp_path, monkeypatch, script)
    try:
        candidate = digest(manifest(workspace["path"]))
        mission = service.missions.begin_verification("m", "verify", mission["revision"], candidate)
        service.run_job("m", "review", "reviewer", None, adapters)
        service.run_job("m", "queen-job", "queen", None, adapters)
        assert seen["verifier"][0] == ("read", "checks", "progress")
        assert seen["queen"][0] == ("read",)
        assert "progress tool" in seen["verifier"][1] and "progress tool" not in seen["queen"][1]
    finally:
        service.close()


def test_bee_prompts_carry_the_profile_and_explain_progress(tmp_path, monkeypatch):
    prompts = {}

    def script(role, broker, prompt):
        prompts[role] = prompt
        return "ok" if role == "worker" else json.dumps({"criteria": {"checks": "passed", "scope": "passed"}, "evidence": "ok"})
    service, adapters, sessions, workspace, mission = started(tmp_path, monkeypatch, script)
    try:
        service.run_job("m", "work", "worker", "one", adapters)
        candidate = digest(manifest(workspace["path"]))
        service.missions.begin_verification("m", "verify", service.store.get("m")["revision"], candidate)
        service.run_job("m", "review", "reviewer", None, adapters)
        head, _, body = prompts["worker"].partition("\n")
        assert "Edits the main module" in head and "Keep changes small." in head and '"python"' in head
        assert "progress tool" in head and "0 <= done <= total <= 100000" in head and "200" in head
        assert json.loads(body)["task"]["id"] == "one"
        head, _, body = prompts["verifier"].partition("\n")
        assert "Verifies the candidate" in head and "progress tool" in head
        assert json.loads(body)["changed_files"] == []
    finally:
        service.close()


# ---- B04: resumo por abelha --------------------------------------------------------------------

def two_task_plan(proposal):
    proposal["tasks"].append({"id": "two", "description": "Then the docs", "bee_id": "worker",
                              "files": ["docs/a.md"], "depends_on": ["one"]})


def test_bees_summary_follows_plan_jobs_and_events(tmp_path, monkeypatch):
    service, adapters, sessions, workspace, mission = started(tmp_path, monkeypatch, lambda *a: "ok", two_task_plan)
    try:
        summary = service.bees_summary("m")
        assert [item["id"] for item in summary] == ["queen", "worker", "reviewer"]
        worker = summary[1]
        assert worker["tasks"]["total"] == 2 and worker["tasks"]["done"] == 0 and worker["tasks"]["current"] == "one"
        assert [(task["id"], task["status"]) for task in worker["tasks"]["items"]] == [("one", "pending"), ("two", "waiting")]
        assert worker["tasks"]["items"][1] == {"id": "two", "description": "Then the docs", "status": "waiting",
                                                "depends_on": ["one"], "files": ["docs/a.md"]}
        assert worker["job"] == {"state": None, "cycle": None, "started": False} and worker["progress"] is None
        assert worker["tools_used"] == {"read": 0, "patch": 0, "checks": 0, "progress": 0}
        assert summary[0]["tasks"] == {"total": 0, "done": 0, "current": None, "items": []}
        assert worker["temporary"] is True and worker["active"] is True and worker["description"] == "Edits the main module"
        assert worker["skills"] == {"tags": ["python"], "instructions": "Keep changes small."}
        assert (worker["provider"], worker["model"], worker["effort"]) == ("claude", "fixture", "medium")
        # job 1 em execução
        service.scheduler.reserve("m", "j1", "worker", "one")
        with service.store.transaction() as connection:
            for tool, success in (("read", True), ("read", True), ("patch", True), ("patch", False), ("checks", True)):
                service.store.event(connection, "m", "tool_completed",
                                    {"job_id": "j1", "bee_id": "worker", "tool": tool, "success": success})
            service.store.event(connection, "m", "tool_completed", {"job_id": "x", "bee_id": "other", "tool": "read", "success": True})
            service.store.event(connection, "m", "bee_progress", {"job_id": "old", "bee_id": "worker", "done": 9, "total": 9, "note": "old job"})
            service.store.event(connection, "m", "bee_progress", {"job_id": "j1", "bee_id": "worker", "done": 1, "total": 3, "note": "first"})
            service.store.event(connection, "m", "bee_progress", {"job_id": "j1", "bee_id": "worker", "done": 2, "total": 3, "note": "second"})
        worker = service.bees_summary("m")[1]
        assert [task["status"] for task in worker["tasks"]["items"]] == ["running", "waiting"]
        assert worker["tasks"]["current"] == "one" and worker["job"] == {"state": "running", "cycle": 1, "started": True}
        assert worker["tools_used"] == {"read": 2, "patch": 1, "checks": 1, "progress": 3}
        assert worker["progress"]["done"] == 2 and worker["progress"]["note"] == "second"
        assert worker["progress"]["total"] == 3 and isinstance(worker["progress"]["seq"], int)
        service.scheduler.finish("j1", True)
        worker = service.bees_summary("m")[1]
        assert [task["status"] for task in worker["tasks"]["items"]] == ["done", "pending"]
        assert worker["tasks"]["done"] == 1 and worker["tasks"]["current"] == "two"
        assert worker["job"]["state"] == "completed"
        service.scheduler.reserve("m", "j2", "worker", "two")
        service.scheduler.finish("j2", False)
        worker = service.bees_summary("m")[1]
        assert [task["status"] for task in worker["tasks"]["items"]] == ["done", "failed"]
        assert worker["job"]["state"] == "failed" and worker["progress"] is None
    finally:
        service.close()


def test_bees_summary_counts_events_beyond_the_five_hundred_the_front_receives(tmp_path):
    service = HiveService(tmp_path / "state")
    try:
        service.missions.create("m", "create", "fixture")
        proposal = plan()
        service.missions.propose("m", "plan", 0, proposal)
        with service.store.transaction() as connection:
            for _ in range(700):
                service.store.event(connection, "m", "tool_completed",
                                    {"job_id": "j", "bee_id": "worker", "tool": "read", "success": True})
        assert service.bees_summary("m")[1]["tools_used"]["read"] == 700
    finally:
        service.close()


def test_mission_route_returns_bees_summary_and_old_missions_still_open(tmp_path, monkeypatch):
    service = HiveService(tmp_path / "state")
    monkeypatch.setattr(routes, "get_service", lambda: service)
    app = Flask(__name__)
    app.register_blueprint(routes.blueprint)
    client = app.test_client()
    try:
        service.missions.create("empty", "create-empty", "fixture")
        assert client.get("/hive-api/missions/empty").get_json()["bees_summary"] == []
        # Sem plano, mas com o planejamento iniciado: a equipe do planejamento (cadastro antigo incluído).
        service.missions.create("planning", "create-planning", "fixture")
        source = tmp_path / "project"
        source.mkdir()
        service.missions.request_planning("planning", "plan-key", 0, source, LEGACY[0], "go", deepcopy(LEGACY))
        body = client.get("/hive-api/missions/planning").get_json()
        assert [item["id"] for item in body["bees_summary"]] == ["queen", "worker1", "verifier"]
        assert body["bees_summary"][1]["description"] == "" and body["bees_summary"][1]["tasks"]["total"] == 0
        # O job de planejamento da Rainha também aparece como job dela.
        assert body["bees_summary"][0]["job"]["started"] is False
        service.missions.create("planned", "create-planned", "fixture")
        service.missions.propose("planned", "propose", 0, plan())
        body = client.get("/hive-api/missions/planned").get_json()
        assert body["mission"]["data"]["plan"] and len(body["bees_summary"]) == 3
        assert set(body["bees_summary"][1]) == {"id", "role", "temporary", "active", "description", "skills", "tools",
                                                 "provider", "model", "effort", "tasks", "progress", "tools_used", "job"}
        assert client.get("/hive-api/missions/planned?after=999999").get_json()["events"] == []
        assert client.get("/hive-api/missions/nope").status_code == 404
    finally:
        service.close()
