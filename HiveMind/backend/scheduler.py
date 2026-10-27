"""Transactional job admission for one Hive service instance."""

import json

from .store import Conflict, canonical
from .workspaces import path_key


class Scheduler:
    def __init__(self, store):
        self.store = store

    def reserve_planning(self, mission_id, job_id):
        """Queen's read-only preparation uses its own slot before approval."""
        with self.store.transaction() as connection:
            mission = self.store._decode(connection.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone())
            if mission["state"] != "planning":
                raise Conflict("dispatch_not_allowed")
            if connection.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone():
                raise Conflict("job_exists")
            if connection.execute("SELECT 1 FROM jobs WHERE mission_id=? AND role='queen' AND state IN "
                                  "('running','tool_active','draining')", (mission_id,)).fetchone():
                raise Conflict("queen_busy")
            bee = mission["data"]["planning"]["queen"]
            job = {"task_id": None, "files": [], "cycle": mission["cycle"], "planning": True,
                   "plan_attempt": mission["data"].get("plan_attempt")}
            connection.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?)",
                               (job_id, mission_id, bee["id"], "queen", "running", canonical(job)))
            self.store.event(connection, mission_id, "job_started", {"job_id": job_id, "bee_id": bee["id"], "role": "queen"})
            return job

    def reserve(self, mission_id, job_id, bee_id, task_id=None):
        """Reserve a documented role; worker, subagent and verifier share two slots."""
        if not all(isinstance(value, str) and value for value in (mission_id, job_id, bee_id)):
            raise ValueError("invalid job")
        with self.store.transaction() as connection:
            mission = self.store._decode(connection.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone())
            data = mission["data"]
            if (not data.get("plan_hash") or data.get("plan_hash") != data.get("approved_plan_hash")
                    or data.get("plan_attempt") != data.get("approved_plan_attempt")):
                raise Conflict("plan_not_approved")
            if not data.get("workspace"):
                raise Conflict("workspace_required")
            bees = data["plan"]["bees"]
            bee = next((item for item in bees if item["id"] == bee_id), None)
            if bee is None:
                raise Conflict("unknown_bee")
            role = bee["role"]
            valid_state = {"worker": ("running", "correcting"), "subagent": ("running", "correcting"),
                           "verifier": ("verifying",), "queen": ("running", "correcting")}
            if mission["state"] not in valid_state[role]:
                raise Conflict("dispatch_not_allowed")
            if mission["state"] == "correcting" and role in {"worker", "subagent"}:
                correction = data.get("correction") or {}
                if (correction.get("status") != "coordinated" or correction.get("plan_hash") != data["plan_hash"]
                        or correction.get("cycle") != mission["cycle"]):
                    raise Conflict("correction_not_ready")
            if connection.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone():
                raise Conflict("job_exists")
            active = connection.execute("SELECT * FROM jobs WHERE state IN ('running','tool_active','draining')").fetchall()
            if role == "queen":
                if any(row["mission_id"] == mission_id and row["role"] == "queen" for row in active):
                    raise Conflict("queen_busy")
            elif sum(row["role"] != "queen" for row in active) >= connection.execute(
                    "SELECT worker_limit FROM settings WHERE id=1").fetchone()["worker_limit"]:
                raise Conflict("worker_slots_full")
            if any(row["mission_id"] == mission_id and row["bee_id"] == bee_id for row in active):
                raise Conflict("bee_busy")
            files = []
            if role in {"worker", "subagent"}:
                task = next((item for item in data["plan"]["tasks"] if item["id"] == task_id), None)
                if task is None or task["bee_id"] != bee_id:
                    raise Conflict("task_not_assigned")
                done = connection.execute("SELECT data FROM jobs WHERE mission_id=? AND state='succeeded'", (mission_id,)).fetchall()
                completed = {json.loads(row["data"]).get("task_id") for row in done
                             if (json.loads(row["data"]).get("cycle") == mission["cycle"]
                                 and json.loads(row["data"]).get("plan_hash") == data["plan_hash"]
                                 and json.loads(row["data"]).get("plan_attempt") == data.get("plan_attempt"))}
                if not set(task["depends_on"]) <= completed:
                    raise Conflict("dependencies_incomplete")
                files = [path_key(path) for path in task["files"]]
                for row in active:
                    if row["mission_id"] == mission_id and set(files) & set(json.loads(row["data"]).get("files", [])):
                        raise Conflict("files_busy")
                if any(row["state"] != "paused" and json.loads(row["data"]).get("task_id") == task_id and
                       json.loads(row["data"]).get("cycle") == mission["cycle"] and
                       json.loads(row["data"]).get("plan_hash") == data["plan_hash"]
                       and json.loads(row["data"]).get("plan_attempt") == data.get("plan_attempt")
                       for row in connection.execute("SELECT state,data FROM jobs WHERE mission_id=?", (mission_id,))):
                    raise Conflict("task_already_attempted")
            elif task_id is not None:
                raise Conflict("task_not_assigned")
            job = {"task_id": task_id, "files": files, "cycle": mission["cycle"],
                   "plan_hash": data["plan_hash"], "plan_attempt": data.get("plan_attempt"),
                   "candidate_hash": data.get("candidate_hash")}
            connection.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?)", (job_id, mission_id, bee_id, role, "running", canonical(job)))
            self.store.event(connection, mission_id, "job_started", {"job_id": job_id, "bee_id": bee_id, "role": role})
            return job

    def finish(self, job_id, success, *, paused=False):
        if type(success) is not bool or type(paused) is not bool or success and paused:
            raise ValueError("invalid job result")
        with self.store.transaction() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None or row["state"] not in {"running", "tool_active", "draining"}:
                raise Conflict("job_not_running")
            state = "paused" if paused else "succeeded" if success else "failed"
            connection.execute("UPDATE jobs SET state=? WHERE id=?", (state, job_id))
            self.store.event(connection, row["mission_id"], "job_finished", {"job_id": job_id, "state": state})
