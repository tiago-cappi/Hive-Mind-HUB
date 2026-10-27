from flask import Flask
import pytest

import HiveMind.backend.routes as routes
from HiveMind.backend.service import HiveService
from HiveMind.backend.store import digest
from HiveMind.backend.workspaces import manifest
from test_hivemind_missions import plan


def test_api_requires_same_origin_and_lease_and_preserves_approval(tmp_path, monkeypatch):
    generation_path = tmp_path / "runtime"
    generation_path.mkdir()
    (generation_path / "runtime.py").write_text("fixture")
    contents = manifest(generation_path)
    service = HiveService(tmp_path / "state", generation={"path": str(generation_path), "manifest": contents,
                          "hash": digest(contents)})
    monkeypatch.setattr(routes, "get_service", lambda: service)
    app = Flask(__name__)
    app.register_blueprint(routes.blueprint)
    client = app.test_client()
    headers = {"Origin": "http://localhost"}
    try:
        assert client.post("/hive-api/missions", json={"id": "m", "key": "create", "title": "fixture"}).status_code == 403
        assert client.post("/hive-api/missions", json={"id": "m", "key": "create", "title": "fixture"},
                           headers={"Origin": "https://attacker.invalid"}).status_code == 403
        created = client.post("/hive-api/missions", json={"id": "m", "key": "create", "title": "fixture"}, headers=headers)
        assert created.status_code == 200
        source = tmp_path / "source"
        source.mkdir()
        proposed = plan()
        proposed["project"]["path"] = str(source)
        command = {"owner": "tab", "action": "propose", "key": "plan", "revision": 0, "plan": proposed}
        assert client.post("/hive-api/missions/m/command", json=command, headers=headers).status_code == 409
        assert client.post("/hive-api/missions/m/lease", json={"owner": "tab"}, headers=headers).status_code == 200
        response = client.post("/hive-api/missions/m/command", json=command, headers=headers)
        assert response.status_code == 200
        mission = response.get_json()
        assert mission["state"] == "awaiting_plan_approval"
        wrong = {"owner": "tab", "action": "approve_plan", "key": "approve", "revision": mission["revision"], "plan_hash": "old"}
        assert client.post("/hive-api/missions/m/command", json=wrong, headers=headers).get_json()["error"] == "stale_plan"
        assert client.get("/hive-api/missions/m").get_json()["mission"]["data"]["approved_plan_hash"] is None
        blocked = {"owner": "tab", "action": "apply", "key": "apply", "revision": mission["revision"], "delivery_hash": "0" * 64}
        assert client.post("/hive-api/missions/m/command", json=blocked, headers=headers).get_json()["error"] == "invalid_state:awaiting_plan_approval"
    finally:
        service.close()


def test_exit_beacon_shape_is_accepted_by_presence_route(monkeypatch):
    class Presence:
        def __init__(self):
            self.calls = []

        def bye(self, hud):
            self.calls.append(hud)

    presence = Presence()
    monkeypatch.setattr(routes, "get_service", lambda: presence)
    app = Flask(__name__)
    app.register_blueprint(routes.blueprint)
    # Chrome sendBeacon(Blob application/json): same-origin POST with Origin and Sec-Fetch-Site, no preflight.
    response = app.test_client().post(
        "/hive-api/presence", data='{"hud":"h1","present":false}', content_type="application/json",
        headers={"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"})
    assert response.status_code == 200
    assert presence.calls == ["h1"]


@pytest.fixture
def hive(tmp_path, monkeypatch):
    service = HiveService(tmp_path / "state")
    monkeypatch.setattr(routes, "get_service", lambda: service)
    app = Flask(__name__)
    app.register_blueprint(routes.blueprint)
    client = app.test_client()
    headers = {"Origin": "http://localhost"}
    assert client.post("/hive-api/missions", json={"id": "m", "key": "create", "title": "fixture"}, headers=headers).status_code == 200
    assert client.post("/hive-api/missions/m/lease", json={"owner": "tab"}, headers=headers).status_code == 200
    def stuck(delivery_hash=None):
        def change(connection, record):
            record["state"] = "recovery_required"
            record["data"]["delivery_hash"] = delivery_hash
            return {}
        return service.store.mutate("m", "stuck", 0, "recovery_required", {}, change)
    def command(action, key, revision, **extra):
        return client.post("/hive-api/missions/m/command", headers=headers,
                           json={"owner": "tab", "action": action, "key": key, "revision": revision, **extra})
    yield service, stuck, command
    service.close()


def test_abandon_command_closes_recovery_required_and_replays(hive):
    service, stuck, command = hive
    mission = stuck()
    response = command("abandon", "abandon", mission["revision"])
    assert response.status_code == 200
    done = response.get_json()
    assert done["state"] == "abandoned" and done["revision"] == mission["revision"] + 1
    assert done["data"]["abandoned"]["previous_state"] == "recovery_required"
    assert command("abandon", "abandon", mission["revision"]).get_json() == done
    assert command("abandon", "abandon", done["revision"]).get_json()["error"] == "idempotency_key_reused"
    assert service.store.events("m")[-1]["kind"] == "mission_abandoned"


def test_abandon_command_refuses_other_states_and_existing_delivery_journal(hive):
    service, stuck, command = hive
    mission = stuck("c" * 64)
    with service.store.transaction() as connection:
        service.store.event(connection, "m", "delivery_applying", {"delivery_hash": "c" * 64})
    directory = service.delivery.journal_root / ("delivery-" + digest(["m", "c" * 64]))
    directory.mkdir()
    (directory / "journal.json").write_text('{"items": [{"attempted": true}]}', encoding="utf-8")
    blocked = command("abandon", "blocked", mission["revision"])
    assert blocked.status_code == 409 and blocked.get_json()["error"] == "delivery_recovery_required"
    assert service.store.get("m")["state"] == "recovery_required"


def test_abandon_command_is_refused_before_recovery_required(hive):
    service, stuck, command = hive
    response = command("abandon", "early", 0)
    assert response.status_code == 409 and response.get_json()["error"] == "invalid_state:draft"
    assert service.store.get("m")["revision"] == 0


@pytest.mark.parametrize("action, extra", [
    ("ask", {"source": ".", "queen": {"id": "queen", "role": "queen", "provider": "codex", "model": "m",
                                       "effort": "high", "temporary": False}, "message": "go"}),
    ("propose", {"plan": plan()}), ("approve_plan", {"plan_hash": "x"}), ("start", {}), ("pause", {}),
    ("resume", {}), ("cycle_limit", {"limit": 5}), ("approve_delivery", {"candidate_hash": "a" * 64, "delivery_hash": "a" * 64}),
    ("apply", {"delivery_hash": "a" * 64}), ("recover_delivery", {}), ("reconcile_source", {}), ("abandon", {}),
])
def test_abandoned_mission_refuses_every_command(hive, action, extra):
    service, stuck, command = hive
    mission = stuck()
    done = command("abandon", "abandon", mission["revision"]).get_json()
    response = command(action, "again-" + action, done["revision"], **extra)
    assert response.status_code == 409 and response.get_json()["error"] != "lease_required"
    current = service.store.get("m")
    assert current["state"] == "abandoned" and current["revision"] == done["revision"]
