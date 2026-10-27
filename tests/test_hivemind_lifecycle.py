import threading

import pytest

from HiveMind.backend.capabilities import PauseRequested, ToolBroker
from HiveMind.backend.lifecycle import Lifecycle
from HiveMind.backend.scheduler import Scheduler
from HiveMind.backend.store import Conflict
from test_hivemind_missions import interrupted, running


def test_pause_denies_new_tools_drains_before_interrupt_and_needs_resume(tmp_path):
    store, missions, mission = running(tmp_path)
    scheduler, lifecycle = Scheduler(store), Lifecycle(store)
    scheduler.reserve("m", "j1", "worker", "one")
    entered, release, calls = threading.Event(), threading.Event(), []
    def write(arguments):
        entered.set()
        release.wait(5)
        calls.append("write_complete")
    broker = ToolBroker({"read": lambda arg: None, "patch": write, "checks": lambda arg: None})
    lifecycle.register("m", "j1", broker, lambda: calls.append("interrupt"))
    thread = threading.Thread(target=lambda: broker.dispatch("patch", {}))
    thread.start()
    assert entered.wait(2)
    pause_revision = mission["revision"]
    mission = lifecycle.request_pause("m", "pause", pause_revision, "last_viewer_closed")
    with pytest.raises(PauseRequested):
        broker.dispatch("read", {})
    assert lifecycle.progress("m")["state"] == "pausing" and calls == []
    release.set()
    thread.join(5)
    assert lifecycle.progress("m")["state"] == "pausing"
    assert calls == ["write_complete", "interrupt"]
    scheduler.finish("j1", False, paused=True)
    lifecycle.unregister("j1")
    mission = lifecycle.progress("m")
    assert mission["state"] == "paused"
    assert store.get("m")["state"] == "paused"
    mission = lifecycle.resume("m", "resume", mission["revision"])
    assert mission["state"] == "running"
    scheduler.reserve("m", "j2", "worker", "one")
    next_broker = ToolBroker({"read": lambda arg: "ok", "patch": lambda arg: None, "checks": lambda arg: None})
    lifecycle.register("m", "j2", next_broker, lambda: None)
    lifecycle.request_pause("m", "pause", pause_revision, "last_viewer_closed")
    assert next_broker.dispatch("read", {}) == "ok"


def test_control_lease_excludes_other_tab_until_expiry(tmp_path, monkeypatch):
    store, _, _ = running(tmp_path)
    lifecycle = Lifecycle(store)
    clock = [100.0]
    monkeypatch.setattr("HiveMind.backend.lifecycle.time.time", lambda: clock[0])
    lifecycle.acquire_control("m", "tab1", ttl=10)
    assert lifecycle.controlled("m", "tab1", lambda: "executed") == "executed"
    with pytest.raises(Conflict, match="lease_held"):
        lifecycle.acquire_control("m", "tab2", ttl=10)
    clock[0] = 111.0
    lifecycle.acquire_control("m", "tab2", ttl=10)
    with pytest.raises(Conflict, match="lease_required"):
        lifecycle.controlled("m", "tab1", lambda: None)


def test_abandoned_mission_cannot_pause_or_resume(tmp_path):
    store, missions, mission = interrupted(tmp_path)
    mission = missions.abandon("m", "abandon", mission["revision"], tmp_path)
    lifecycle = Lifecycle(store)
    with pytest.raises(Conflict, match="pause_not_allowed"):
        lifecycle.request_pause("m", "pause", mission["revision"], "user")
    with pytest.raises(Conflict, match="resume_not_allowed"):
        lifecycle.resume("m", "resume", mission["revision"])
    assert store.get("m")["revision"] == mission["revision"]
