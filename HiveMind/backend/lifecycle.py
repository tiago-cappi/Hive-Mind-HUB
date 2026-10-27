"""Pause admission, drain admitted operations, then interrupt owned sessions."""

import threading
import time
import uuid

from .adapters.base import safe_name
from .store import Conflict


_ACTIVE = {"planning", "running", "verifying", "correcting"}


class Lifecycle:
    def __init__(self, store):
        self.store = store
        self._lock = threading.RLock()
        self._control_lock = threading.RLock()
        self._sessions = {}

    def acquire_control(self, mission_id, owner, ttl=30):
        """Acquire or renew one mission's control lease without preempting a live owner."""
        if not safe_name(owner) or type(ttl) not in (int, float) or not 1 <= ttl <= 120:
            raise ValueError("invalid lease")
        now = time.time()
        with self._control_lock, self.store.transaction() as connection:
            self.store._decode(connection.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone())
            row = connection.execute("SELECT owner,expires_at FROM leases WHERE mission_id=?", (mission_id,)).fetchone()
            if row and row["owner"] != owner and row["expires_at"] > now:
                raise Conflict("lease_held")
            connection.execute("INSERT INTO leases VALUES(?,?,?) ON CONFLICT(mission_id) DO UPDATE SET "
                               "owner=excluded.owner,expires_at=excluded.expires_at", (mission_id, owner, now + ttl))
            return {"expires_at": now + ttl}

    def controlled(self, mission_id, owner, operation):
        """Serialize a UI mutation with lease checks and renewal on this service."""
        if not safe_name(owner) or not callable(operation):
            raise ValueError("invalid lease")
        with self._control_lock:
            with self.store.session() as connection:
                row = connection.execute("SELECT owner,expires_at FROM leases WHERE mission_id=?", (mission_id,)).fetchone()
            if row is None or row["owner"] != owner or row["expires_at"] <= time.time():
                raise Conflict("lease_required")
            return operation()

    def register(self, mission_id, job_id, broker, interrupt):
        if not callable(interrupt):
            raise ValueError("interrupt callback required")
        with self._lock:
            mission = self.store.get(mission_id)
            if mission["state"] not in _ACTIVE or not broker.admission.accepting():
                raise Conflict("dispatch_not_allowed")
            with self.store.session() as connection:
                row = connection.execute("SELECT mission_id,state FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None or row["mission_id"] != mission_id or row["state"] != "running" or job_id in self._sessions:
                raise Conflict("job_not_running")
            self._sessions[job_id] = {"mission": mission_id, "broker": broker,
                                      "interrupt": interrupt, "interrupted": False}

    def unregister(self, job_id):
        with self._lock:
            self._sessions.pop(job_id, None)

    def request_pause(self, mission_id, key, revision, reason):
        if reason not in {"user", "last_viewer_closed", "presence_uncertain", "shutdown", "job_failed"}:
            raise ValueError("invalid pause reason")
        with self._lock:
            def change(connection, mission):
                if mission["state"] not in _ACTIVE:
                    raise Conflict("pause_not_allowed")
                mission["data"]["pause"] = {"from": mission["state"], "reason": reason,
                                            "fence": uuid.uuid4().hex}
                mission["state"] = "pausing"
                return {"reason": reason, "fence": mission["data"]["pause"]["fence"]}
            result = self.store.mutate(mission_id, key, revision, "pause_requested", {"reason": reason}, change)
            current = self.store.get(mission_id)
            if (current["state"] == "pausing" and
                    current["data"]["pause"]["fence"] == result["data"]["pause"]["fence"]):
                for entry in self._sessions.values():
                    if entry["mission"] == mission_id:
                        entry["broker"].admission.request_pause()
            return result

    def progress(self, mission_id):
        """Interrupt after drain; declare paused only once jobs have actually ended."""
        with self._lock:
            mission = self.store.get(mission_id)
            if mission["state"] != "pausing":
                return mission
            sessions = [entry for entry in self._sessions.values() if entry["mission"] == mission_id]
            for entry in sessions:
                if not entry["broker"].admission.drained():
                    return mission
            for entry in sessions:
                if not entry["interrupted"]:
                    entry["interrupt"]()
                    entry["interrupted"] = True
            with self.store.session() as connection:
                active = connection.execute("SELECT 1 FROM jobs WHERE mission_id=? AND state IN "
                                            "('running','tool_active','draining') LIMIT 1", (mission_id,)).fetchone()
            if active:
                return mission
            def change(connection, current):
                if current["state"] != "pausing":
                    raise Conflict("pause_not_allowed")
                current["state"] = "awaiting_user" if current["data"]["pause"]["reason"] == "job_failed" else "paused"
                return {"reason": current["data"]["pause"]["reason"]}
            return self.store.mutate(mission_id, "pause-complete:" + mission["data"]["pause"]["fence"],
                                     mission["revision"], "paused", {}, change)

    def resume(self, mission_id, key, revision):
        with self._lock:
            def change(connection, mission):
                if mission["state"] != "paused":
                    raise Conflict("resume_not_allowed")
                unknown = connection.execute("SELECT 1 FROM jobs WHERE mission_id=? AND state='unknown' LIMIT 1",
                                             (mission_id,)).fetchone()
                if unknown:
                    raise Conflict("recovery_required")
                mission["state"] = mission["data"]["pause"]["from"]
                return {"resumed_to": mission["state"]}
            return self.store.mutate(mission_id, key, revision, "resumed", {}, change)
