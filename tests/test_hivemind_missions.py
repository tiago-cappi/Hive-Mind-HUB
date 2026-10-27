from copy import deepcopy
import json
import threading

import pytest

from HiveMind.backend.missions import InvalidTransition, Missions, validate_plan
from HiveMind.backend.store import Conflict, Store
from HiveMind.backend.workspaces import snapshot


def plan():
    return {"objective": "Update the fixture", "project": {"path": "C:/fixture/project"},
            "acceptance": [{"id": "checks", "description": "Tests pass"}, {"id": "scope", "description": "Only approved files change"}],
            "bees": [
                {"id": "queen", "role": "queen", "provider": "codex", "model": "fixture", "effort": "high", "temporary": False,
                 "description": "Plans and coordinates", "skills": {"tags": ["planning"], "instructions": ""}, "tools": ["read"]},
                {"id": "worker", "role": "worker", "provider": "claude", "model": "fixture", "effort": "medium", "temporary": True,
                 "description": "Edits the main module", "skills": {"tags": ["python"], "instructions": "Keep changes small."},
                 "tools": ["read", "patch", "checks"]},
                {"id": "reviewer", "role": "verifier", "provider": "codex", "model": "fixture", "effort": "high", "temporary": False,
                 "description": "Verifies the candidate", "skills": {"tags": ["review"], "instructions": ""}, "tools": ["read", "checks"]}],
            "tasks": [{"id": "one", "description": "Update the main module", "bee_id": "worker", "files": ["src/main.py"], "depends_on": []}],
            "checks": [["python", "-m", "pytest"]]}


def service(tmp_path):
    store = Store(tmp_path / "state" / "hive.db")
    return store, Missions(store)


def running(tmp_path):
    store, missions = service(tmp_path)
    mission = missions.create("m", "create", "fixture")
    source = tmp_path / "project"
    source.mkdir()
    state = tmp_path / "workspaces"
    state.mkdir()
    candidate = snapshot(source, state, "mission")
    proposal = plan()
    proposal["project"]["path"] = str(source)
    mission = missions.propose("m", "plan", mission["revision"], proposal)
    mission = missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
    mission = missions.bind_workspace("m", "bind", mission["revision"], source, candidate)
    mission = missions.start("m", "start", mission["revision"])
    return store, missions, mission


def test_approval_is_versioned_idempotent_and_precedes_work(tmp_path):
    store, missions = service(tmp_path)
    first = missions.create("m", "create", "fixture")
    assert missions.create("m", "create", "fixture") == first
    with pytest.raises(Conflict, match="idempotency"):
        missions.create("m", "create", "other")
    with pytest.raises(InvalidTransition):
        missions.start("m", "too-early", 0)
    first = missions.propose("m", "plan-a", 0, plan())
    old_hash = first["data"]["plan_hash"]
    changed = deepcopy(plan())
    changed["tasks"][0]["files"] = ["src/new.py"]
    second = missions.propose("m", "plan-b", first["revision"], changed)
    with pytest.raises(Conflict, match="stale_plan"):
        missions.approve_plan("m", "bad-approve", second["revision"], old_hash)
    approved = missions.approve_plan("m", "approve", second["revision"], second["data"]["plan_hash"])
    assert missions.approve_plan("m", "approve", second["revision"], second["data"]["plan_hash"]) == approved
    assert len(store.events("m")) == 4 and len(store.roster("m")) == 3
    with pytest.raises(Conflict, match="stale_revision"):
        missions.start("m", "wrong-revision", 0)


def test_cycles_and_independent_verdict_are_not_reset(tmp_path):
    store, missions, mission = running(tmp_path)
    candidate = "a" * 64
    for cycle in (1, 2, 3):
        mission = missions.begin_verification("m", "verify-" + str(cycle), mission["revision"], candidate)
        with pytest.raises(Conflict, match="independent_verifier"):
            missions.record_verdict("m", "worker-review-" + str(cycle), mission["revision"], candidate, "worker", {"checks": "passed", "scope": "passed"})
        with pytest.raises(Conflict, match="criteria_incomplete"):
            missions.record_verdict("m", "incomplete-" + str(cycle), mission["revision"], candidate, "reviewer", {"checks": "passed"})
        mission = missions.record_verdict("m", "failed-" + str(cycle), mission["revision"], candidate, "reviewer", {"checks": "failed", "scope": "passed"})
        assert mission["state"] == ("awaiting_user" if cycle == 3 else "correcting")
    assert mission["cycle"] == 3 and len(mission["data"]["verification_history"]) == 3
    with pytest.raises(Conflict, match="below_current"):
        missions.set_cycle_limit("m", "reduce", mission["revision"], 2)
    assert Store(store.path).get("m")["cycle"] == 3


def test_concurrent_revision_and_crash_recovery(tmp_path):
    store, missions, mission = running(tmp_path)
    revision = mission["revision"]
    outcomes = []
    def update(key):
        try:
            missions.set_cycle_limit("m", key, revision, 4)
            outcomes.append("ok")
        except Conflict:
            outcomes.append("conflict")
    threads = [threading.Thread(target=update, args=(str(index),)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["conflict", "ok"]
    assert Store(store.path).recover_interrupted() == 1
    assert store.get("m")["state"] == "recovery_required"
    assert Store(store.path).recover_interrupted() == 0


def test_plan_rejects_escape_dependencies_and_queen_worker():
    bad = plan()
    bad["tasks"][0]["files"] = ["../outside"]
    with pytest.raises(ValueError, match="files"):
        validate_plan(bad)
    bad = plan()
    bad["tasks"][0]["depends_on"] = ["one"]
    with pytest.raises(ValueError, match="cycle"):
        validate_plan(bad)
    bad = plan()
    bad["tasks"][0]["bee_id"] = "queen"
    with pytest.raises(ValueError, match="worker"):
        validate_plan(bad)
    bad = plan()
    second = deepcopy(bad["tasks"][0])
    second.update({"id": "two", "files": ["SRC/MAIN.PY"]})
    bad["tasks"].append(second)
    with pytest.raises(ValueError, match="overlapping"):
        validate_plan(bad)
    second["depends_on"] = ["one"]
    assert validate_plan(bad)


def interrupted(tmp_path):
    """A running mission with a running job, restarted: recovery_required with an unknown job."""
    store, missions, mission = running(tmp_path)
    with store.transaction() as connection:
        connection.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?)", ("job", "m", "worker", "worker", "running", "{}"))
    Store(store.path).recover_interrupted()
    return store, missions, store.get("m")


def test_abandon_closes_recovery_required_and_preserves_history(tmp_path):
    store, missions, mission = interrupted(tmp_path)
    journals = tmp_path / "deliveries"
    journals.mkdir()
    jobs_before, workspace_before = store.jobs("m"), mission["data"]["workspace"]
    assert [job["state"] for job in jobs_before] == ["unknown"]
    done = missions.abandon("m", "abandon", mission["revision"], journals)
    assert done["state"] == "abandoned" and done["revision"] == mission["revision"] + 1
    assert done["data"]["abandoned"]["previous_state"] == "recovery_required"
    assert set(done["data"]["abandoned"]) == {"previous_state", "at"}
    assert done["data"]["workspace"] == workspace_before and store.jobs("m") == jobs_before
    events = store.events("m")
    assert events[-1]["kind"] == "mission_abandoned"
    assert missions.abandon("m", "abandon", mission["revision"], journals) == done
    assert store.events("m") == events
    assert store.get("m")["revision"] == done["revision"]
    with pytest.raises(Conflict, match="idempotency_key_reused"):
        missions.abandon("m", "abandon", done["revision"], journals)


def test_abandon_is_refused_outside_recovery_required_and_ignores_old_journal(tmp_path):
    store, missions, mission = running(tmp_path)
    journals = tmp_path / "deliveries"
    journals.mkdir()
    with pytest.raises(InvalidTransition, match="invalid_state:running"):
        missions.abandon("m", "early", mission["revision"], journals)
    Store(store.path).recover_interrupted()
    mission = store.get("m")
    package_hash = "b" * 64
    def prepared(connection, record):
        record["data"]["delivery_hash"] = package_hash
        return {}
    from HiveMind.backend.store import digest
    (journals / ("delivery-" + digest(["m", package_hash]))).mkdir()
    # Journal on disk but no apply ever started: old leftovers do not block.
    mission = store.mutate("m", "prepared", mission["revision"], "delivery_prepared", {}, prepared)
    assert missions.abandon("m", "no-apply", mission["revision"], journals)["state"] == "abandoned"


def write_journal(journals, package_hash, items=None, raw=None):
    from HiveMind.backend.store import digest
    directory = journals / ("delivery-" + digest(["m", package_hash]))
    directory.mkdir(exist_ok=True)
    if items is not None or raw is not None:
        (directory / "journal.json").write_text(raw if raw is not None else json.dumps({"items": items}), encoding="utf-8")
    return directory


@pytest.mark.parametrize("journal, accepted", [
    ({}, True),
    ({"items": []}, True),
    ({"items": [{"attempted": False}, {"attempted": False}]}, True),
    ({"items": [{"attempted": False}, {"attempted": True}]}, False),
    ({"raw": "{not json"}, False),
    ({"raw": "[]"}, False),
    ({"items": [{"path": "x"}]}, False),
    ({"items": [{"attempted": "yes"}]}, False),
    ({"items": {}}, False),
    ({"items": ""}, False),
])
def test_abandon_pending_journal_depends_on_whether_the_source_was_touched(tmp_path, journal, accepted):
    store, missions, mission = running(tmp_path)
    journals = tmp_path / "deliveries"
    journals.mkdir()
    Store(store.path).recover_interrupted()
    package_hash = "b" * 64
    write_journal(journals, package_hash, **journal)
    def change(connection, record):
        record["data"]["delivery_hash"] = package_hash
        return {}
    store.mutate("m", "applying", store.get("m")["revision"], "delivery_applying", {}, change)
    revision = store.get("m")["revision"]
    if accepted:
        assert missions.abandon("m", "abandon", revision, journals)["state"] == "abandoned"
    else:
        with pytest.raises(Conflict, match="delivery_recovery_required"):
            missions.abandon("m", "abandon", revision, journals)
        assert store.get("m")["state"] == "recovery_required"


def test_abandon_refuses_an_oversized_journal(tmp_path):
    store, missions, mission = running(tmp_path)
    journals = tmp_path / "deliveries"
    journals.mkdir()
    Store(store.path).recover_interrupted()
    package_hash = "b" * 64
    directory = write_journal(journals, package_hash, [])
    with (directory / "journal.json").open("wb") as stream:
        stream.truncate(10 * 1024 * 1024 + 1)
    def change(connection, record):
        record["data"]["delivery_hash"] = package_hash
        return {}
    store.mutate("m", "applying", store.get("m")["revision"], "delivery_applying", {}, change)
    with pytest.raises(Conflict, match="delivery_recovery_required"):
        missions.abandon("m", "abandon", store.get("m")["revision"], journals)


def test_abandon_is_refused_only_while_the_journal_is_pending(tmp_path):
    from HiveMind.backend.store import digest
    store, missions, mission = running(tmp_path)
    journals = tmp_path / "deliveries"
    journals.mkdir()
    Store(store.path).recover_interrupted()
    package_hash = "b" * 64
    write_journal(journals, package_hash, [{"attempted": True}])
    def mark(kind):
        def change(connection, record):
            record["data"]["delivery_hash"] = package_hash
            return {}
        return lambda: store.mutate("m", "mark-" + kind + str(store.get("m")["revision"]),
                                    store.get("m")["revision"], kind, {}, change)
    mission = mark("delivery_applying")()
    with pytest.raises(Conflict, match="delivery_recovery_required"):
        missions.abandon("m", "blocked", mission["revision"], journals)
    current = store.get("m")
    assert current["state"] == "recovery_required" and current["revision"] == mission["revision"]
    mission = mark("delivery_recovered")()
    assert missions.abandon("m", "after-recovery", mission["revision"], journals)["state"] == "abandoned"


def test_abandoned_is_terminal_for_every_mission_transition(tmp_path):
    store, missions, mission = interrupted(tmp_path)
    mission = missions.abandon("m", "abandon", mission["revision"], tmp_path)
    revision = mission["revision"]
    attempts = {
        "request_planning": lambda: missions.request_planning("m", "k1", revision, str(tmp_path), plan()["bees"][0], "go"),
        "propose": lambda: missions.propose("m", "k2", revision, plan()),
        "approve_plan": lambda: missions.approve_plan("m", "k3", revision, "x"),
        "start": lambda: missions.start("m", "k4", revision),
        "cycle_limit": lambda: missions.set_cycle_limit("m", "k5", revision, 5),
        "approve_delivery": lambda: missions.approve_delivery("m", "k6", revision, "a" * 64, "a" * 64),
        "abandon": lambda: missions.abandon("m", "k7", revision, tmp_path),
        "begin_reconciliation": lambda: missions.begin_reconciliation("m", "k8", revision, "op"),
        "begin_verification": lambda: missions.begin_verification("m", "k9", revision, "a" * 64),
    }
    for name, attempt in attempts.items():
        with pytest.raises(InvalidTransition, match="invalid_state:abandoned"):
            attempt()
    assert store.get("m")["revision"] == revision
