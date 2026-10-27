from copy import deepcopy

import pytest

from HiveMind.backend.scheduler import Scheduler
from HiveMind.backend.store import Conflict
from test_hivemind_missions import interrupted, running, service, plan
from HiveMind.backend.workspaces import snapshot


def test_reservations_enforce_task_once_and_pause_state(tmp_path):
    store, missions, mission = running(tmp_path)
    scheduler = Scheduler(store)
    assert scheduler.reserve("m", "j1", "worker", "one")["task_id"] == "one"
    with pytest.raises(Conflict, match="jobs_still_running"):
        missions.begin_verification("m", "premature", mission["revision"], "a" * 64)
    with pytest.raises(Conflict, match="bee_busy"):
        scheduler.reserve("m", "j2", "worker", "one")
    scheduler.finish("j1", True)
    with pytest.raises(Conflict, match="task_already_attempted"):
        scheduler.reserve("m", "j2", "worker", "one")
    mission = missions.begin_verification("m", "verify", mission["revision"], "a" * 64)
    assert scheduler.reserve("m", "review", "reviewer")["candidate_hash"] == "a" * 64
    with pytest.raises(Conflict, match="dispatch_not_allowed"):
        scheduler.reserve("m", "j3", "worker", "one")


def test_worker_and_subagents_share_two_slots_queen_separate(tmp_path):
    store, missions = service(tmp_path)
    mission = missions.create("m", "create", "fixture")
    source, workspaces = tmp_path / "project", tmp_path / "workspaces"
    source.mkdir()
    workspaces.mkdir()
    workspace = snapshot(source, workspaces, "m")
    proposal = plan()
    proposal["project"]["path"] = str(source)
    for number in (2, 3):
        bee = deepcopy(proposal["bees"][1])
        bee.update({"id": "worker" + str(number), "role": "subagent"})
        proposal["bees"].append(bee)
        task = deepcopy(proposal["tasks"][0])
        task.update({"id": "task" + str(number), "bee_id": bee["id"], "files": ["src/" + str(number) + ".py"]})
        proposal["tasks"].append(task)
    mission = missions.propose("m", "plan", mission["revision"], proposal)
    mission = missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
    mission = missions.bind_workspace("m", "workspace", mission["revision"], source, workspace)
    missions.start("m", "start", mission["revision"])
    scheduler = Scheduler(store)
    scheduler.reserve("m", "one", "worker", "one")
    scheduler.reserve("m", "two", "worker2", "task2")
    with pytest.raises(Conflict, match="worker_slots_full"):
        scheduler.reserve("m", "three", "worker3", "task3")
    assert scheduler.reserve("m", "queen", "queen")["task_id"] is None
    assert store.set_worker_limit(3, "limit", 0)["worker_limit"] == 3
    assert scheduler.reserve("m", "three", "worker3", "task3")["task_id"] == "task3"
    assert store.settings() == {"worker_limit": 3, "revision": 1}


def test_process_identity_is_recorded_for_recovery(tmp_path):
    import os
    import subprocess
    import sys
    from types import SimpleNamespace
    from HiveMind.backend.service import HiveService
    if os.name != "nt":
        pytest.skip("Windows process identity")
    service = HiveService(tmp_path / "state")
    process = None
    try:
        mission = service.missions.create("m", "create", "fixture")
        source = tmp_path / "project"
        source.mkdir()
        proposal = plan()
        proposal["project"]["path"] = str(source)
        mission = service.missions.propose("m", "plan", mission["revision"], proposal)
        mission = service.missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
        workspace = snapshot(source, service.state_root / "workspaces", "m")
        mission = service.missions.bind_workspace("m", "bind", mission["revision"], source, workspace)
        service.missions.start("m", "start", mission["revision"])
        service.scheduler.reserve("m", "job", "worker", "one")
        process = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"], stdin=subprocess.PIPE)
        service._session_started("m", "job", SimpleNamespace(rpc=SimpleNamespace(process=process)))
        identity = service.store.jobs("m")[0]["data"]["process"]
        assert identity["pid"] == process.pid and identity["created"] > 0
        service.scheduler.finish("job", True)
    finally:
        if process:
            process.stdin.close()
            process.wait(timeout=5)
        service.close()


def test_reapproved_plan_generation_does_not_reuse_completed_or_failed_task(tmp_path):
    store, missions, mission = running(tmp_path)
    scheduler = Scheduler(store)
    first_hash = mission["data"]["plan_hash"]
    scheduler.reserve("m", "old-success", "worker", "one")
    scheduler.finish("old-success", True)
    mission = missions.set_cycle_limit("m", "one-cycle", mission["revision"], 1)
    mission = missions.begin_verification("m", "verify-old", mission["revision"], "a" * 64)
    mission = missions.record_verdict("m", "fail-old", mission["revision"], "a" * 64, "reviewer",
                                      {"checks": "failed", "scope": "passed"}, "old evidence")
    assert mission["state"] == "awaiting_user" and mission["cycle"] == 1
    mission = missions.set_cycle_limit("m", "raise-limit", mission["revision"], 2)
    replacement = plan()
    source = tmp_path / "project"
    replacement["project"]["path"] = str(source)
    replacement["tasks"][0]["description"] = "A changed approved task"
    replacement["tasks"][0]["files"] = ["src/replanned.py"]
    mission = missions.propose("m", "plan-new", mission["revision"], replacement)
    second_hash = mission["data"]["plan_hash"]
    assert second_hash != first_hash and mission["data"].get("workspace") is None
    mission = missions.approve_plan("m", "approve-new", mission["revision"], second_hash)
    workspaces = tmp_path / "workspaces"
    workspace = snapshot(source, workspaces, "replanned")
    mission = missions.bind_workspace("m", "bind-new", mission["revision"], source, workspace)
    missions.start("m", "start-new", mission["revision"])
    reserved = scheduler.reserve("m", "new-attempt", "worker", "one")
    assert reserved["plan_hash"] == second_hash
    assert store.get("m")["cycle"] == 2
    assert len(store.get("m")["data"]["plan_history"]) == 2
    assert [item["cycle"] for item in store.get("m")["data"]["attempt_history"]] == [1]


def test_unknown_effect_requires_recovery_before_replanning(tmp_path):
    store, missions, mission = running(tmp_path)
    scheduler = Scheduler(store)
    scheduler.reserve("m", "unknown-job", "worker", "one")
    scheduler.finish("unknown-job", False)
    mission = missions.set_cycle_limit("m", "one-cycle", mission["revision"], 1)
    mission = missions.begin_verification("m", "verify", mission["revision"], "a" * 64)
    mission = missions.record_verdict("m", "fail", mission["revision"], "a" * 64, "reviewer",
                                      {"checks": "failed", "scope": "passed"})
    with store.transaction() as connection:
        connection.execute("UPDATE jobs SET state='unknown' WHERE id='unknown-job'")
    with pytest.raises(Conflict, match="recovery_required"):
        missions.propose("m", "blocked-plan", mission["revision"], plan())


def test_failed_task_from_old_plan_does_not_block_reapproved_generation(tmp_path):
    store, missions, mission = running(tmp_path)
    scheduler = Scheduler(store)
    scheduler.reserve("m", "old-failure", "worker", "one")
    scheduler.finish("old-failure", False)
    mission = missions.set_cycle_limit("m", "one-cycle", mission["revision"], 1)
    mission = missions.begin_verification("m", "verify-old", mission["revision"], "a" * 64)
    mission = missions.record_verdict("m", "fail-old", mission["revision"], "a" * 64, "reviewer",
                                      {"checks": "failed", "scope": "passed"})
    mission = missions.set_cycle_limit("m", "raise-limit", mission["revision"], 2)
    replacement = plan()
    replacement["project"]["path"] = str(tmp_path / "project")
    replacement["tasks"][0]["description"] = "A separately approved retry"
    mission = missions.propose("m", "plan-new", mission["revision"], replacement)
    mission = missions.approve_plan("m", "approve-new", mission["revision"], mission["data"]["plan_hash"])
    workspace = snapshot(tmp_path / "project", tmp_path / "workspaces", "failedreplanned")
    mission = missions.bind_workspace("m", "bind-new", mission["revision"], tmp_path / "project", workspace)
    started = missions.start("m", "start-new", mission["revision"])
    assert started["cycle"] == 2
    assert scheduler.reserve("m", "new-attempt", "worker", "one")["plan_hash"] == mission["data"]["plan_hash"]


def _rejected_at_ceiling(tmp_path, fail_job=False):
    store, missions, mission = running(tmp_path)
    scheduler = Scheduler(store)
    scheduler.reserve("m", "old", "worker", "one")
    scheduler.finish("old", not fail_job)
    mission = missions.set_cycle_limit("m", "one-cycle", mission["revision"], 1)
    plan_hash = mission["data"]["plan_hash"]
    mission = missions.begin_verification("m", "verify:" + plan_hash + ":1:1", mission["revision"], "a" * 64)
    mission = missions.record_verdict("m", "reject", mission["revision"], "a" * 64, "reviewer",
                                      {"checks": "failed", "scope": "passed"}, "fix needed")
    assert mission["state"] == "awaiting_user" and mission["cycle"] == mission["cycle_limit"] == 1
    return store, missions, scheduler, mission


def _reauthorize_identical(missions, mission, label):
    proposal = deepcopy(mission["data"]["plan"])
    mission = missions.propose("m", "plan-" + label, mission["revision"], proposal)
    assert mission["data"]["plan_hash"] == mission["data"]["plan_history"][0]["hash"]
    return mission


@pytest.mark.parametrize("fail_job", [False, True])
def test_identical_plan_after_ceiling_needs_raised_limit_before_any_snapshot(tmp_path, fail_job):
    store, missions, scheduler, mission = _rejected_at_ceiling(tmp_path, fail_job)
    mission = _reauthorize_identical(missions, mission, "same")
    with pytest.raises(Conflict, match="cycle_limit_reached"):
        missions.approve_plan("m", "approve-same", mission["revision"], mission["data"]["plan_hash"])
    assert store.get("m")["state"] == "awaiting_plan_approval" and store.get("m")["cycle"] == 1
    mission = missions.set_cycle_limit("m", "raise-limit", store.get("m")["revision"], 2)
    mission = missions.approve_plan("m", "approve-same-again", mission["revision"], mission["data"]["plan_hash"])
    workspace = snapshot(tmp_path / "project", tmp_path / "workspaces", "sameplan")
    mission = missions.bind_workspace("m", "bind-same", mission["revision"], tmp_path / "project", workspace)
    mission = missions.start("m", "start-same", mission["revision"])
    assert mission["state"] == "running" and mission["cycle"] == 2
    assert mission["data"]["plan_attempt"] == 2 and mission["data"]["attempt_history"][0]["status"] == "cycle_limit"


def test_identical_plan_reauthorized_with_raised_limit_launches_and_verifies_anew(tmp_path):
    from HiveMind.backend.lifecycle import Lifecycle
    from HiveMind.backend.service import HiveService
    store, missions, scheduler, mission = _rejected_at_ceiling(tmp_path)
    mission = missions.set_cycle_limit("m", "raise-limit", mission["revision"], 3)
    mission = _reauthorize_identical(missions, mission, "same")
    mission = missions.approve_plan("m", "approve-same", mission["revision"], mission["data"]["plan_hash"])
    workspace = snapshot(tmp_path / "project", tmp_path / "workspaces", "sameplan")
    mission = missions.bind_workspace("m", "bind-same", mission["revision"], tmp_path / "project", workspace)
    missions.start("m", "start-same", mission["revision"])
    service = HiveService(tmp_path / "service", adapters={"fixture": object()})
    service.store, service.missions, service.scheduler, service.lifecycle = store, missions, scheduler, Lifecycle(store)
    launches = []
    service._launch = lambda *args: launches.append(args)
    try:
        service.heartbeat("hud")
        service.advance()
        assert [item[3] for item in launches] == ["one"] and launches[0][0][2:4] == (2, 2)
        scheduler.reserve("m", "new-work", "worker", "one")
        scheduler.finish("new-work", True)
        service.advance()
        current = store.get("m")
        assert current["state"] == "verifying"
        assert current["data"]["verification_generation"]["cycle"] == 2
        assert current["data"]["verification_generation"]["plan_attempt"] == 2
    finally:
        service.close()


def test_new_plan_after_ceiling_also_needs_a_new_cycle(tmp_path):
    store, missions, scheduler, mission = _rejected_at_ceiling(tmp_path)
    replacement = plan()
    replacement["project"]["path"] = str(tmp_path / "project")
    replacement["tasks"][0]["files"] = ["src/other.py"]
    mission = missions.propose("m", "plan-new", mission["revision"], replacement)
    with pytest.raises(Conflict, match="cycle_limit_reached"):
        missions.approve_plan("m", "approve-new", mission["revision"], mission["data"]["plan_hash"])



def test_abandoned_mission_admits_no_job(tmp_path):
    store, missions, mission = interrupted(tmp_path)
    missions.abandon("m", "abandon", mission["revision"], tmp_path)
    scheduler = Scheduler(store)
    for bee, task in (("worker", "one"), ("reviewer", None), ("queen", None)):
        with pytest.raises(Conflict, match="dispatch_not_allowed"):
            scheduler.reserve("m", "j-" + bee, bee, task)
    with pytest.raises(Conflict, match="dispatch_not_allowed"):
        scheduler.reserve_planning("m", "planning-job")
    assert [job["state"] for job in store.jobs("m")] == ["unknown"]
