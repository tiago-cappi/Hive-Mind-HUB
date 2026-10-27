from copy import deepcopy
from pathlib import Path

import pytest

from HiveMind.backend.delivery import Delivery
from HiveMind.backend.service import HiveService
from HiveMind.backend.missions import Missions
from HiveMind.backend.store import Conflict, Store, digest
from HiveMind.backend.tools import WorkspaceTools
from HiveMind.backend.workspaces import manifest, snapshot
from test_hivemind_missions import plan


def prepared(tmp_path, two_files=False, operation="replace"):
    source = tmp_path / "source"
    (source / "src").mkdir(parents=True)
    (source / "src" / "main.py").write_text("old", encoding="utf-8")
    if two_files:
        (source / "src" / "second.py").write_text("old-second", encoding="utf-8")
    state = tmp_path / "workspaces"
    state.mkdir()
    journals = tmp_path / "journals"
    journals.mkdir()
    workspace = snapshot(source, state, "m")
    store = Store(tmp_path / "state.db")
    missions = Missions(store)
    mission = missions.create("m", "create", "fixture")
    proposal = deepcopy(plan())
    proposal["project"]["path"] = str(source)
    if two_files:
        proposal["tasks"][0]["files"].append("src/second.py")
    if operation == "add":
        proposal["tasks"][0]["files"].append("src/added.py")
    mission = missions.propose("m", "plan", mission["revision"], proposal)
    mission = missions.approve_plan("m", "approve-plan", mission["revision"], mission["data"]["plan_hash"])
    mission = missions.bind_workspace("m", "workspace", mission["revision"], source, workspace)
    mission = missions.start("m", "start", mission["revision"])
    tools = WorkspaceTools(workspace["path"], proposal["tasks"][0]["files"], [])
    if operation == "add":
        tools.broker.dispatch("patch", {"path": "src/added.py", "content": "new", "expected_sha256": None})
    else:
        tools.broker.dispatch("patch", {"path": "src/main.py", "content": None if operation == "remove" else "new", "expected_sha256": workspace["base"]["src/main.py"]})
    if two_files:
        tools.broker.dispatch("patch", {"path": "src/second.py", "content": "new-second", "expected_sha256": workspace["base"]["src/second.py"]})
    candidate_hash = digest(manifest(workspace["path"]))
    mission = missions.begin_verification("m", "verify", mission["revision"], candidate_hash)
    mission = missions.record_verdict("m", "verdict", mission["revision"], candidate_hash, "reviewer", {"checks": "passed", "scope": "passed"})
    delivery = Delivery(store, journals)
    mission = delivery.prepare("m", "package", mission["revision"], source, workspace["path"], workspace["base"])
    mission = missions.approve_delivery("m", "approve-delivery", mission["revision"], candidate_hash, mission["data"]["delivery_hash"])
    return source, workspace, store, delivery, mission


def test_delivery_requires_exact_approval_and_preserves_temporary_history(tmp_path):
    source, workspace, store, delivery, mission = prepared(tmp_path)
    with pytest.raises(Conflict, match="delivery_not_approved"):
        delivery.apply("m", "wrong", mission["revision"], "0" * 64)
    result = delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    assert result["state"] == "completed" and (source / "src" / "main.py").read_text() == "new"
    assert not next(bee for bee in store.roster("m") if bee["id"] == "worker")["active"]
    assert delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])["state"] == "completed"


def test_source_change_invalidates_delivery_without_overwrite(tmp_path):
    source, workspace, store, delivery, mission = prepared(tmp_path)
    (source / "src" / "main.py").write_text("external")
    with pytest.raises(Conflict, match="source_changed"):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    assert (source / "src" / "main.py").read_text() == "external"
    assert store.get("m")["state"] == "recovery_required"
    assert store.get("m")["data"]["approved_delivery_hash"] is None


def test_candidate_changed_after_review_is_not_applied(tmp_path):
    source, workspace, store, delivery, mission = prepared(tmp_path)
    (Path(workspace["path"]) / "src" / "main.py").write_text("tampered")
    with pytest.raises(Conflict, match="candidate_changed"):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    assert (source / "src" / "main.py").read_text() == "old"


def test_different_volume_is_rejected_before_any_mutation(tmp_path, monkeypatch):
    source, workspace, store, delivery, mission = prepared(tmp_path)
    monkeypatch.setattr(delivery, "_same_volume", lambda *_: False)
    with pytest.raises(Conflict, match="delivery_same_volume_required"):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    assert store.get("m") == mission
    assert list(delivery.journal_root.iterdir()) == []
    assert (source / "src" / "main.py").read_text() == "old"


def test_partial_apply_rolls_back_confirmed_writes(tmp_path, monkeypatch):
    source, workspace, store, delivery, mission = prepared(tmp_path, two_files=True)
    original_replace = delivery._replace
    def fail_second(target, staged, captured):
        if target == source / "src" / "second.py":
            raise OSError("fixture failure")
        return original_replace(target, staged, captured)
    monkeypatch.setattr(delivery, "_replace", fail_second)
    with pytest.raises(OSError, match="fixture failure"):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    assert (source / "src" / "main.py").read_text() == "old"
    assert (source / "src" / "second.py").read_text() == "old-second"
    assert store.get("m")["state"] == "recovery_required"
    assert store.events("m")[-1]["data"]["rollback_complete"] is True
    monkeypatch.setattr(delivery, "_replace", original_replace)
    interrupted = store.get("m")
    recovered = delivery.recover("m", "recover", interrupted["revision"])
    assert recovered["state"] == "awaiting_user"
    assert (source / "src" / "main.py").read_text() == "old"
    assert recovered["data"]["approved_delivery_hash"] is None


def test_concurrent_write_between_check_and_replace_is_retained(tmp_path, monkeypatch):
    source, workspace, store, delivery, mission = prepared(tmp_path)
    original_replace = delivery._replace
    def race(target, staged, captured):
        target.write_text("concurrent", encoding="utf-8")
        return original_replace(target, staged, captured)
    monkeypatch.setattr(delivery, "_replace", race)
    with pytest.raises(Conflict, match="source_changed_during_apply"):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    directory = next(delivery.journal_root.iterdir())
    assert (directory / "0.captured").read_text() == "concurrent"
    assert (directory / "0.original").read_text() == "old"
    assert (source / "src" / "main.py").read_text() == "new"
    interrupted = store.get("m")
    assert interrupted["state"] == "recovery_required"
    with pytest.raises(Conflict, match="delivery_recovery_ambiguous"):
        delivery.recover("m", "recover", interrupted["revision"])
    assert (directory / "0.captured").read_text() == "concurrent"


def test_concurrent_write_during_rollback_is_retained(tmp_path, monkeypatch):
    source, workspace, store, delivery, mission = prepared(tmp_path, two_files=True)
    original_replace = delivery._replace
    def race(target, staged, captured):
        if target.name == "second.py":
            raise OSError("fixture failure")
        if captured.name.endswith(".rollback"):
            target.write_text("concurrent during rollback", encoding="utf-8")
        return original_replace(target, staged, captured)
    monkeypatch.setattr(delivery, "_replace", race)
    with pytest.raises(OSError, match="fixture failure"):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    directory = next(delivery.journal_root.iterdir())
    assert (directory / "0.rollback").read_text() == "concurrent during rollback"
    assert (directory / "0.captured").read_text() == "old"
    assert (source / "src" / "main.py").read_text() == "old"
    assert store.events("m")[-1]["data"]["rollback_complete"] is False


@pytest.mark.parametrize("operation", ["add", "remove"])
def test_add_and_remove_are_limited_to_approved_package(tmp_path, operation):
    source, workspace, store, delivery, mission = prepared(tmp_path, operation=operation)
    delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    if operation == "add":
        assert (source / "src" / "added.py").read_text() == "new"
        assert (source / "src" / "main.py").read_text() == "old"
    else:
        assert not (source / "src" / "main.py").exists()
        directory = next(delivery.journal_root.iterdir())
        assert (directory / "0.captured").read_text() == "old"


def test_concurrent_add_is_not_replaced(tmp_path, monkeypatch):
    source, workspace, store, delivery, mission = prepared(tmp_path, operation="add")
    original_move = delivery._move
    def race(staged, target):
        if target.name == "added.py":
            target.write_text("concurrent", encoding="utf-8")
        return original_move(staged, target)
    monkeypatch.setattr(delivery, "_move", race)
    with pytest.raises(OSError):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    assert (source / "src" / "added.py").read_text() == "concurrent"
    directory = next(delivery.journal_root.iterdir())
    assert (directory / "0.new").read_text() == "new"
    assert store.get("m")["state"] == "recovery_required"


def test_concurrent_remove_is_quarantined_not_lost(tmp_path, monkeypatch):
    source, workspace, store, delivery, mission = prepared(tmp_path, operation="remove")
    original_move = delivery._move
    def race(target, captured):
        if target.name == "main.py":
            target.write_text("concurrent", encoding="utf-8")
        return original_move(target, captured)
    monkeypatch.setattr(delivery, "_move", race)
    with pytest.raises(Conflict, match="source_changed_during_apply"):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    directory = next(delivery.journal_root.iterdir())
    assert (directory / "0.captured").read_text() == "concurrent"
    assert (directory / "0.original").read_text() == "old"
    assert store.get("m")["state"] == "recovery_required"


def test_stale_source_reconciliation_creates_new_base_and_candidate(tmp_path):
    source = tmp_path / "source"
    (source / "src").mkdir(parents=True)
    (source / "src" / "main.py").write_text("old", encoding="utf-8")
    (source / "notes.txt").write_text("old notes", encoding="utf-8")
    service = HiveService(tmp_path / "state")
    try:
        mission = service.missions.create("m", "create", "fixture")
        proposal = deepcopy(plan())
        proposal["project"]["path"] = str(source)
        mission = service.missions.propose("m", "plan", mission["revision"], proposal)
        mission = service.missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
        workspace = snapshot(source, service.state_root / "workspaces", "original")
        mission = service.missions.bind_workspace("m", "bind", mission["revision"], source, workspace)
        mission = service.missions.start("m", "start", mission["revision"])
        WorkspaceTools(workspace["path"], ["src/main.py"], []).patch({"path": "src/main.py", "content": "candidate", "expected_sha256": workspace["base"]["src/main.py"]})
        candidate_hash = digest(manifest(workspace["path"]))
        mission = service.missions.begin_verification("m", "verify", mission["revision"], candidate_hash)
        mission = service.missions.record_verdict("m", "verdict", mission["revision"], candidate_hash, "reviewer",
                                                   {"checks": "passed", "scope": "passed"}, "verified")
        mission = service.delivery.prepare("m", "package", mission["revision"], source, workspace["path"], workspace["base"])
        mission = service.missions.approve_delivery("m", "approve-delivery", mission["revision"], candidate_hash,
                                                     mission["data"]["delivery_hash"])
        (source / "notes.txt").write_text("external notes", encoding="utf-8")
        with pytest.raises(Conflict, match="source_changed"):
            service.delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
        recovered = service.delivery.recover("m", "recover", service.store.get("m")["revision"])
        assert recovered["data"]["reconciliation_required"]["workspace"] == workspace["path"]
        reconciled = service.reconcile_source("m", "reconcile", recovered["revision"])
        new_workspace = reconciled["data"]["workspace"]
        assert reconciled["state"] == "verifying" and new_workspace["path"] != workspace["path"]
        assert (Path(new_workspace["path"]) / "src" / "main.py").read_text() == "candidate"
        assert (Path(new_workspace["path"]) / "notes.txt").read_text() == "external notes"
        assert reconciled["data"]["verdict"] is None and reconciled["data"]["approved_delivery_hash"] is None
        assert reconciled["data"]["workspace_history"][-1]["workspace"]["path"] == workspace["path"]
    finally:
        service.close()


def test_stale_source_conflict_preserves_isolated_versions_for_conscious_replan(tmp_path):
    source, workspace, store, delivery, mission = prepared(tmp_path)
    service = HiveService(tmp_path / "unused")
    service.close()
    (source / "src" / "main.py").write_text("external", encoding="utf-8")
    with pytest.raises(Conflict, match="source_changed"):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    recovered = delivery.recover("m", "recover", store.get("m")["revision"])
    # This path is exercised through a service in the preceding test; the durable
    # marker here proves a conflicting source never updates the old workspace/base.
    assert recovered["data"]["reconciliation_required"]["workspace"] == workspace["path"]
    assert (Path(workspace["path"]) / "src" / "main.py").read_text() == "new"
    assert (source / "src" / "main.py").read_text() == "external"


def test_stale_reconciliation_conflict_keeps_old_and_fresh_candidates(tmp_path):
    source = tmp_path / "source"
    (source / "src").mkdir(parents=True)
    (source / "src" / "main.py").write_text("old", encoding="utf-8")
    service = HiveService(tmp_path / "state")
    try:
        mission = service.missions.create("m", "create", "fixture")
        proposal = deepcopy(plan())
        proposal["project"]["path"] = str(source)
        mission = service.missions.propose("m", "plan", mission["revision"], proposal)
        mission = service.missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
        workspace = snapshot(source, service.state_root / "workspaces", "original")
        mission = service.missions.bind_workspace("m", "bind", mission["revision"], source, workspace)
        mission = service.missions.start("m", "start", mission["revision"])
        WorkspaceTools(workspace["path"], ["src/main.py"], []).patch({"path": "src/main.py", "content": "candidate", "expected_sha256": workspace["base"]["src/main.py"]})
        candidate_hash = digest(manifest(workspace["path"]))
        mission = service.missions.begin_verification("m", "verify", mission["revision"], candidate_hash)
        mission = service.missions.record_verdict("m", "verdict", mission["revision"], candidate_hash, "reviewer",
                                                   {"checks": "passed", "scope": "passed"}, "verified")
        mission = service.delivery.prepare("m", "package", mission["revision"], source, workspace["path"], workspace["base"])
        mission = service.missions.approve_delivery("m", "approve-delivery", mission["revision"], candidate_hash,
                                                     mission["data"]["delivery_hash"])
        (source / "src" / "main.py").write_text("external", encoding="utf-8")
        with pytest.raises(Conflict, match="source_changed"):
            service.delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
        recovered = service.delivery.recover("m", "recover", service.store.get("m")["revision"])
        conflicted = service.reconcile_source("m", "reconcile", recovered["revision"])
        marker = conflicted["data"]["reconciliation_required"]
        assert conflicted["state"] == "awaiting_user" and marker["conflicts"] == ["src/main.py"]
        assert marker["workspace"] == workspace["path"] and marker["candidate"]["path"] != workspace["path"]
        assert (Path(workspace["path"]) / "src" / "main.py").read_text() == "candidate"
        assert (Path(marker["candidate"]["path"]) / "src" / "main.py").read_text() == "external"
        assert (source / "src" / "main.py").read_text() == "external"
    finally:
        service.close()


def stale_service(tmp_path, external="notes.txt"):
    """Service with an approved delivery whose source changed, recovered and ready to reconcile."""
    source = tmp_path / "source"
    (source / "src").mkdir(parents=True)
    (source / "src" / "main.py").write_text("old", encoding="utf-8")
    (source / "notes.txt").write_text("old notes", encoding="utf-8")
    service = HiveService(tmp_path / "state")
    mission = service.missions.create("m", "create", "fixture")
    proposal = deepcopy(plan())
    proposal["project"]["path"] = str(source)
    mission = service.missions.propose("m", "plan", mission["revision"], proposal)
    mission = service.missions.approve_plan("m", "approve", mission["revision"], mission["data"]["plan_hash"])
    workspace = snapshot(source, service.state_root / "workspaces", "original")
    mission = service.missions.bind_workspace("m", "bind", mission["revision"], source, workspace)
    mission = service.missions.start("m", "start", mission["revision"])
    WorkspaceTools(workspace["path"], ["src/main.py"], []).patch(
        {"path": "src/main.py", "content": "candidate", "expected_sha256": workspace["base"]["src/main.py"]})
    candidate_hash = digest(manifest(workspace["path"]))
    mission = service.missions.begin_verification("m", "verify", mission["revision"], candidate_hash)
    mission = service.missions.record_verdict("m", "verdict", mission["revision"], candidate_hash, "reviewer",
                                               {"checks": "passed", "scope": "passed"}, "verified")
    mission = service.delivery.prepare("m", "package", mission["revision"], source, workspace["path"], workspace["base"])
    mission = service.missions.approve_delivery("m", "approve-delivery", mission["revision"], candidate_hash,
                                                 mission["data"]["delivery_hash"])
    (source / external).write_text("external", encoding="utf-8")
    with pytest.raises(Conflict, match="source_changed"):
        service.delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    recovered = service.delivery.recover("m", "recover", service.store.get("m")["revision"])
    return service, source, workspace, recovered


def copies(service):
    return sorted(path.name for path in (service.state_root / "workspaces").iterdir())


@pytest.mark.parametrize("external, state", [("notes.txt", "verifying"), ("src/main.py", "awaiting_user")])
def test_reconcile_replay_returns_saved_result_without_new_copy(tmp_path, external, state):
    service, source, workspace, recovered = stale_service(tmp_path, external)
    try:
        first = service.reconcile_source("m", "reconcile", recovered["revision"])
        assert first["state"] == state
        before = copies(service)
        assert service.reconcile_source("m", "reconcile", recovered["revision"]) == first
        assert copies(service) == before and service.store.get("m")["revision"] == first["revision"]
        with pytest.raises(Conflict, match="idempotency_key_reused"):
            service.reconcile_source("m", "apply", recovered["revision"])
    finally:
        service.close()


def test_reconcile_interruption_requires_explicit_recovery_and_repeats_no_effect(tmp_path, monkeypatch):
    import HiveMind.backend.workspaces as workspaces
    service, source, workspace, recovered = stale_service(tmp_path)
    try:
        monkeypatch.setattr(workspaces, "snapshot", lambda *args: (_ for _ in ()).throw(OSError("disk")))
        with pytest.raises(OSError):
            service.reconcile_source("m", "reconcile", recovered["revision"])
        interrupted = service.store.get("m")
        assert interrupted["state"] == "recovery_required"
        assert interrupted["data"]["reconciliation_operation"]["status"] == "recovery_required"
        assert interrupted["data"]["workspace"]["path"] == workspace["path"]
        assert (Path(workspace["path"]) / "src" / "main.py").read_text() == "candidate"
        assert (source / "src" / "main.py").read_text() == "old" and service.active_missions() == []
        monkeypatch.undo()
        with pytest.raises(Conflict, match="recovery_required"):
            service.reconcile_source("m", "reconcile", recovered["revision"])
        assert copies(service) == ["original"]
        again = service.delivery.recover("m", "recover-again", interrupted["revision"])
        assert again["state"] == "awaiting_user"
        done = service.reconcile_source("m", "reconcile-again", again["revision"])
        assert done["state"] == "verifying" and done["data"]["reconciliation_operation"]["status"] == "completed"
    finally:
        service.close()


def test_abandon_is_refused_after_a_failed_apply_until_the_delivery_is_recovered(tmp_path, monkeypatch):
    source, workspace, store, delivery, mission = prepared(tmp_path)
    monkeypatch.setattr(delivery, "_replace", lambda *args: (_ for _ in ()).throw(OSError("fixture failure")))
    with pytest.raises(OSError, match="fixture failure"):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    interrupted = store.get("m")
    assert interrupted["state"] == "recovery_required" and any(delivery.journal_root.iterdir())
    missions = Missions(store)
    with pytest.raises(Conflict, match="delivery_recovery_required"):
        missions.abandon("m", "abandon", interrupted["revision"], delivery.journal_root)
    assert store.get("m") == interrupted
    monkeypatch.undo()
    assert delivery.recover("m", "recover", interrupted["revision"])["state"] == "awaiting_user"


def test_abandon_is_refused_when_the_journal_after_a_failed_apply_is_unreadable(tmp_path, monkeypatch):
    source, workspace, store, delivery, mission = prepared(tmp_path)
    monkeypatch.setattr(delivery, "_replace", lambda *args: (_ for _ in ()).throw(OSError("fixture failure")))
    with pytest.raises(OSError, match="fixture failure"):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    interrupted = store.get("m")
    (next(delivery.journal_root.iterdir()) / "journal.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(Conflict, match="delivery_recovery_required"):
        Missions(store).abandon("m", "abandon", interrupted["revision"], delivery.journal_root)
    assert store.get("m") == interrupted


def test_abandon_is_accepted_when_apply_fails_before_any_journal_is_written(tmp_path):
    import shutil
    source, workspace, store, delivery, mission = prepared(tmp_path)
    shutil.rmtree(workspace["path"])
    with pytest.raises(Exception):
        delivery.apply("m", "apply", mission["revision"], mission["data"]["delivery_hash"])
    interrupted = store.get("m")
    directory = next(delivery.journal_root.iterdir())
    assert interrupted["state"] == "recovery_required" and not (directory / "journal.json").exists()
    done = Missions(store).abandon("m", "abandon", interrupted["revision"], delivery.journal_root)
    assert done["state"] == "abandoned"
    assert (source / "src" / "main.py").read_text() == "old"


def restarted_during_apply(tmp_path):
    source, workspace, store, delivery, mission = prepared(tmp_path)
    def begin(connection, record):
        record["state"] = "applying"
        return {}
    store.mutate("m", "begin", mission["revision"], "delivery_applying", {"delivery_hash": mission["data"]["delivery_hash"]}, begin)
    Store(store.path).recover_interrupted()
    interrupted = store.get("m")
    assert interrupted["state"] == "recovery_required"
    return source, store, delivery, interrupted, delivery.journal_root / ("delivery-" + digest(["m", mission["data"]["delivery_hash"]]))


def test_restart_during_apply_without_journal_directory_can_be_abandoned(tmp_path):
    source, store, delivery, interrupted, directory = restarted_during_apply(tmp_path)
    assert not directory.exists()
    assert Missions(store).abandon("m", "abandon", interrupted["revision"], delivery.journal_root)["state"] == "abandoned"
    assert (source / "src" / "main.py").read_text() == "old"


def test_restart_during_apply_with_attempted_journal_cannot_be_abandoned(tmp_path):
    source, store, delivery, interrupted, directory = restarted_during_apply(tmp_path)
    directory.mkdir()
    (directory / "journal.json").write_text('{"items": [{"attempted": true}]}', encoding="utf-8")
    with pytest.raises(Conflict, match="delivery_recovery_required"):
        Missions(store).abandon("m", "abandon", interrupted["revision"], delivery.journal_root)
    assert store.get("m") == interrupted


def test_abandon_is_accepted_when_reconciliation_is_interrupted_after_a_recovered_apply(tmp_path, monkeypatch):
    import HiveMind.backend.workspaces as workspaces
    service, source, workspace, recovered = stale_service(tmp_path)
    try:
        monkeypatch.setattr(workspaces, "snapshot", lambda *args: (_ for _ in ()).throw(OSError("disk")))
        with pytest.raises(OSError):
            service.reconcile_source("m", "reconcile", recovered["revision"])
        interrupted = service.store.get("m")
        assert interrupted["state"] == "recovery_required" and interrupted["data"]["delivery_hash"]
        assert any(service.delivery.journal_root.iterdir())
        kinds = [event["kind"] for event in service.store.events("m")]
        assert kinds.index("delivery_recovered") > kinds.index("delivery_applying")
        done = service.missions.abandon("m", "abandon", interrupted["revision"], service.delivery.journal_root)
        assert done["state"] == "abandoned" and service.active_missions() == []
        assert (source / "src" / "main.py").read_text() == "old"
    finally:
        service.close()


def test_boot_marks_pending_reconciliation_recovery_required(tmp_path):
    service, source, workspace, recovered = stale_service(tmp_path)
    try:
        pending = service.missions.begin_reconciliation("m", "begin", recovered["revision"], "reconcile")
        assert pending["state"] == "awaiting_user" and service.active_missions() == ["m"]
    finally:
        service._owner.close()
    reopened = HiveService(tmp_path / "state")
    try:
        mission = reopened.store.get("m")
        assert mission["state"] == "recovery_required"
        assert mission["data"]["reconciliation_operation"] == {**pending["data"]["reconciliation_operation"],
                                                                "status": "recovery_required"}
        assert reopened.active_missions() == [] and reopened.ready_to_exit() and reopened.hub_exit_ready()
    finally:
        reopened.close()


def test_closing_waits_for_admitted_reconciliation_and_refuses_new_ones(tmp_path, monkeypatch):
    import threading
    import HiveMind.backend.workspaces as workspaces
    service, source, workspace, recovered = stale_service(tmp_path)
    entered, release, outcome = threading.Event(), threading.Event(), []
    original = workspaces.snapshot
    def blocked(*args):
        entered.set()
        release.wait(10)
        return original(*args)
    monkeypatch.setattr(workspaces, "snapshot", blocked)
    def run():
        try:
            outcome.append(service.reconcile_source("m", "reconcile", recovered["revision"])["state"])
        except Exception as exc:
            outcome.append(type(exc).__name__ + ":" + str(exc))
    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert entered.wait(5)
        assert service.active_missions() == ["m"]
        assert service.ready_to_exit() is False and service.hub_exit_ready() is False
        revision = service.store.get("m")["revision"]
        with pytest.raises(Conflict, match="closing"):
            service.reconcile_source("m", "second", revision)
        assert service.store.get("m")["revision"] == revision
    finally:
        release.set()
        thread.join(10)
    assert outcome == ["verifying"]
    assert service.ready_to_exit() is True and service.store.get("m")["state"] == "paused"
    service.close()


def test_new_reconciliation_after_closing_is_refused_before_any_write_until_viewer_returns(tmp_path):
    service, source, workspace, recovered = stale_service(tmp_path)
    try:
        service.request_pause_all("shutdown")
        with pytest.raises(Conflict, match="closing"):
            service.reconcile_source("m", "reconcile", recovered["revision"])
        current = service.store.get("m")
        assert current["revision"] == recovered["revision"] and "reconciliation_operation" not in current["data"]
        assert copies(service) == ["original"]
        service.heartbeat("hud")
        assert service.reconcile_source("m", "reconcile", recovered["revision"])["state"] == "verifying"
    finally:
        service.close()
