"""Owned Hive service and explicitly started presence watchdog."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import threading
import time
import uuid

from .bees import incomplete, job_tools, prompt_profile, same_bee, validate_progress
from .delivery import Delivery
from .lifecycle import Lifecycle
from .missions import Missions, require_reauthorization_cycle
from .scheduler import Scheduler
from .store import Conflict, Store, canonical, digest
from .summary import bees_summary
from .workspaces import WorkspaceError, manifest, relative_path, validate_runtime_generation


def _strict(properties):
    """Closed JSON Schema object: every property required, nothing else allowed."""
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


_TEXT, _TEXTS = {"type": "string"}, {"type": "array", "items": {"type": "string"}}
# Structured output for the Queen; validate_plan still enforces every local rule.
_QUEEN_OUTPUT = _strict({
    "clarification": {"type": ["string", "null"]},
    "plan": {"anyOf": [{"type": "null"}, _strict({
        "objective": _TEXT,
        "project": _strict({"path": _TEXT}),
        "bees": {"type": "array", "items": _strict({
            "id": _TEXT, "role": {"type": "string", "enum": ["queen", "worker", "subagent", "verifier"]},
            "provider": {"type": "string", "enum": ["codex", "claude"]},
            "model": _TEXT, "effort": _TEXT, "temporary": {"type": "boolean"}, "description": _TEXT,
            "skills": _strict({"tags": _TEXTS, "instructions": _TEXT}), "tools": _TEXTS})},
        "tasks": {"type": "array", "items": _strict({
            "id": _TEXT, "description": _TEXT, "bee_id": _TEXT, "files": _TEXTS, "depends_on": _TEXTS})},
        "acceptance": {"type": "array", "items": _strict({"id": _TEXT, "description": _TEXT})},
        "checks": {"type": "array", "items": _TEXTS},
    })]},
})


def _verdict_output(acceptance):
    status = {"type": "string", "enum": ["passed", "failed", "unverifiable"]}
    return _strict({"criteria": _strict({item["id"]: status for item in acceptance}), "evidence": _TEXT})


_GATE_FAILURES = frozenset({
    "cli_unavailable", "version_unverified", "subscription_unverified", "discovery_incomplete",
    "selection_unknown", "selection_model_unlisted", "selection_effort_unlisted",
    "ordinary_quota_unavailable", "billing_path_unverified", "managed_policy_unverified",
    "enforcement_evidence_unverified",
})
_TURN_FAILURES = frozenset({
    "native_tool_unexpected", "process_unavailable", "protocol_invalid_or_closed", "protocol_timeout",
    "session_controls_unverified", "tool_limit_reached", "tool_not_available", "tool_not_drained",
    "turn_not_available", "turn_result_invalid", "turn_start_failed",
})
# Fixed adapter codes beyond the turn ones (tests compare both sets with every literal in adapters/*.py).
_ADAPTER_FAILURES = frozenset({
    "command_failed", "protocol_closed", "method_not_allowed", "unexpected_server_request",
    "control_invalid", "catalog_invalid", "usage_invalid", "status_invalid", "security_config_invalid",
    "mcp_name_invalid", "mcp_roster_invalid", "global_instructions_unknown", "catalog_pagination_invalid",
    "catalog_pagination_limit", "context_unverified",
})
# Codes whose variable suffix is dropped: only the prefix is recorded.
_PREFIXED_FAILURES = ("thread_controls_unverified", "protocol_request_failed")
_PLANNING_FAILURES = frozenset({
    "planning_result_invalid", "planning_scope_mismatch", "project_too_large_to_plan", "planning_read_required",
    "runtime_generation_changed", "process_identity_unverified", "job_result_invalid", "verdict_invalid",
})


def _failure_reason(error):
    """Return a stable local code without recording provider text or model output."""
    from .adapters.base import DiscoveryError
    if isinstance(error, DiscoveryError):
        text = str(error)
        if text.startswith("gate:") and text[5:] in _GATE_FAILURES:
            return text[5:]
        if text in _TURN_FAILURES or text in _ADAPTER_FAILURES:
            return text
        for prefix in _PREFIXED_FAILURES:
            if text.startswith(prefix + ":"):
                return prefix
        if text.startswith("turn_failed:claude:"):
            from .adapters.claude import turn_error_code
            code = text[len("turn_failed:claude:"):]
            status = code[len("api_error_"):]
            result = ({"api_error_status": int(status)} if code.startswith("api_error_") and len(status) == 3
                      and status.isascii() and status.isdecimal() else {"subtype": code})
            if turn_error_code(result) == code:
                return text
        elif text.startswith("turn_failed:"):
            from .adapters.codex import turn_error_code
            category = text[len("turn_failed:"):]
            name, _, status = category.partition(":")
            if not status:
                infos = [category, {category: {}}]
            elif len(status) == 3 and status.isascii() and status.isdecimal():
                infos = [{name: {"httpStatusCode": int(status)}}]
            else:
                infos = []
            if any(turn_error_code({"codexErrorInfo": info}) == category for info in infos):
                return text
    if isinstance(error, Conflict) and str(error) in _PLANNING_FAILURES:
        return str(error)
    return "job_failed"


class HiveService:
    def __init__(self, state_root, hud_snapshot=None, clock=time.time, presence_grace=10, generation=None, adapters=None):
        self.state_root = Path(state_root).absolute()
        self.state_root.mkdir(parents=True, exist_ok=True)
        self._owner = open(self.state_root / "service.lock", "a+b")
        self._lock_owner()
        try:
            self.store = Store(self.state_root / "hive.sqlite3")
            self.store.recover_interrupted()
            self.missions = Missions(self.store)
            self.scheduler = Scheduler(self.store)
            self.lifecycle = Lifecycle(self.store)
            for name in ("workspaces", "verification", "deliveries", "runtime"):
                (self.state_root / name).mkdir(exist_ok=True)
            self.delivery = Delivery(self.store, self.state_root / "deliveries")
        except BaseException:
            self._owner.close()
            raise
        self._presence_lock = threading.Lock()
        self._huds = {}
        self._hud_ever = False
        self.hud_snapshot = hud_snapshot or self._own_hud_snapshot
        self.clock, self.presence_grace = clock, presence_grace
        self.generation = generation
        self.adapters = adapters
        self._drive_lock = threading.Lock()
        self._pending = {}
        self._reconcile_lock = threading.RLock()
        self._closing = False
        self._seen_hud = False
        self._missing_since = None
        self._presence_reason = None
        self._stop = threading.Event()
        self._watcher = None

    def _lock_owner(self):
        try:
            self._owner.seek(0)
            if not self._owner.read(1):
                self._owner.write(b"0")
                self._owner.flush()
            self._owner.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._owner.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._owner.close()
            raise Conflict("service_already_owned") from exc

    def start_watchdog(self):
        if self._watcher is not None:
            return
        self._watcher = threading.Thread(target=self._watch, name="hivemind-presence", daemon=True)
        self._watcher.start()

    def _watch(self):
        while not self._stop.wait(2):
            try:
                self.check_presence()
                self.progress_pauses()
                self.advance()
            except Exception:
                # Subsequent ticks retry; no exception permits automatic resume.
                continue

    def active_missions(self):
        with self.store.session() as connection:
            active = [row[0] for row in connection.execute("SELECT id FROM missions WHERE state IN "
                      "('planning','preparing','running','verifying','correcting','pausing','applying')")]
            waiting = connection.execute("SELECT id,data FROM missions WHERE state='awaiting_user'").fetchall()
        for row in waiting:
            operation = json.loads(row["data"]).get("reconciliation_operation") or {}
            if operation.get("status") == "pending":
                active.append(row["id"])
        return active

    def request_pause_all(self, reason="shutdown"):
        with self._reconcile_lock:
            self._closing = True
        for mission_id in self.active_missions():
            mission = self.store.get(mission_id)
            if mission["state"] in {"pausing", "preparing", "applying"}:
                continue
            try:
                self.lifecycle.request_pause(mission_id, "automatic-pause:" + str(mission["revision"]),
                                             mission["revision"], reason)
            except Conflict:
                pass
        self.progress_pauses()

    def progress_pauses(self):
        for mission_id in self.active_missions():
            if self.store.get(mission_id)["state"] == "pausing":
                self.lifecycle.progress(mission_id)

    def ready_to_exit(self):
        self.request_pause_all("shutdown")
        return not self.active_missions()

    def hub_exit_ready(self):
        """Honor live Hive heartbeats and a reload grace before draining on Hub exit."""
        if not self.active_missions():
            return True
        self.check_presence()
        if self._can_dispatch():
            return False
        if self._missing_since is None:
            self._missing_since = self.clock()
            self._presence_reason = "presence_uncertain"
            return False
        if self.clock() - self._missing_since < self.presence_grace:
            return False
        self.request_pause_all(self._presence_reason or "presence_uncertain")
        return not self.active_missions()

    def check_presence(self):
        """A brief absence handles navigation; TTL expiry stays explicitly uncertain."""
        if self.hud_snapshot is None:
            return
        state = self.hud_snapshot()
        if not isinstance(state, dict) or type(state.get("ever")) is not bool or not isinstance(state.get("huds"), dict):
            return
        now = self.clock()
        ttl = state.get("ttl")
        if not isinstance(ttl, (int, float)) or ttl <= 0:
            return
        live = any(isinstance(value, (int, float)) and now - value <= ttl for value in state["huds"].values())
        if live:
            self._seen_hud = True
            self._missing_since = self._presence_reason = None
            return
        if not self._seen_hud and not state["ever"]:
            return
        if self._missing_since is None:
            self._missing_since = now
            self._presence_reason = "presence_uncertain" if state["huds"] else "last_viewer_closed"
        elif now - self._missing_since >= self.presence_grace:
            self.request_pause_all(self._presence_reason)

    def _own_hud_snapshot(self):
        with self._presence_lock:
            return {"ever": self._hud_ever, "huds": dict(self._huds), "ttl": 120}

    def heartbeat(self, hud):
        from .adapters.base import safe_name
        if not safe_name(hud):
            raise ValueError("invalid hud")
        with self._presence_lock:
            self._hud_ever = True
            self._huds[hud] = self.clock()
        self._closing = False

    def bye(self, hud):
        from .adapters.base import safe_name
        if not safe_name(hud):
            raise ValueError("invalid hud")
        with self._presence_lock:
            self._huds.pop(hud, None)

    def _can_dispatch(self):
        state = self.hud_snapshot()
        if not isinstance(state, dict) or not isinstance(state.get("huds"), dict):
            return False
        ttl = state.get("ttl")
        if not isinstance(ttl, (int, float)) or ttl <= 0:
            return False
        now = self.clock()
        return any(isinstance(value, (int, float)) and now - value <= ttl for value in state["huds"].values())

    def advance(self):
        """Advance only approved work; a missing viewer never starts another job."""
        if self.adapters is None or not self._can_dispatch():
            return
        with self._drive_lock:
            with self.store.session() as connection:
                rows = connection.execute("SELECT id FROM missions WHERE state IN "
                    "('running','correcting','verifying','awaiting_delivery_approval') ORDER BY created_at").fetchall()
                active_rows = connection.execute("SELECT id,mission_id,bee_id,role,data FROM jobs WHERE state IN "
                    "('running','tool_active','draining')").fetchall()
            active = [dict(row) for row in active_rows]
            for row in active:
                row["data"] = json.loads(row["data"])
            active_ids = {row["id"] for row in active}
            slots = (self.store.settings()["worker_limit"] - sum(row["role"] != "queen" for row in active)
                     - sum(item["job"] not in active_ids for item in self._pending.values()))
            for row in rows:
                mission_id = row["id"]
                mission = self.store.get(mission_id)
                data = mission["data"]
                if mission["state"] == "awaiting_delivery_approval":
                    if not data.get("delivery_hash"):
                        workspace = data["workspace"]
                        try:
                            self.delivery.prepare(mission_id, "prepare:" + data["candidate_hash"], mission["revision"],
                                                  workspace["source"], workspace["path"], workspace["base"])
                        except Conflict:
                            pass
                    continue
                with self.store.session() as connection:
                    completed = connection.execute("SELECT data FROM jobs WHERE mission_id=? AND state='succeeded'", (mission_id,)).fetchall()
                plan_hash, plan_attempt = data["plan_hash"], data.get("plan_attempt")
                done = {item.get("task_id") for item in (json.loads(record["data"]) for record in completed)
                        if (item.get("cycle") == mission["cycle"] and item.get("plan_hash") == plan_hash
                            and item.get("plan_attempt") == plan_attempt
                            and item.get("task_id"))}
                busy = {item["bee_id"] for item in active if item["mission_id"] == mission_id}
                busy.update(item["bee"] for item in self._pending.values() if item["mission"] == mission_id)
                if mission["state"] in {"running", "correcting"}:
                    tasks = data["plan"]["tasks"]
                    if mission["state"] == "correcting":
                        correction = data.get("correction") or {}
                        if (correction.get("plan_hash") != plan_hash or correction.get("cycle") != mission["cycle"]):
                            continue
                        if correction.get("status") == "pending":
                            queen = next(bee for bee in data["plan"]["bees"] if bee["role"] == "queen")
                            key = (mission_id, plan_hash, plan_attempt, mission["cycle"], "coordination")
                            if queen["id"] not in busy and key not in self._pending:
                                self._launch(key, mission_id, queen["id"], None)
                            continue
                        if correction.get("status") != "coordinated":
                            continue
                    if len(done) == len(tasks) and not any(item["mission_id"] == mission_id for item in active) and not any(
                            item["mission"] == mission_id for item in self._pending.values()):
                        candidate = digest(manifest(data["workspace"]["path"]))
                        try:
                            self.missions.begin_verification(mission_id, "verify:" + plan_hash + ":" + str(plan_attempt) + ":" + str(mission["cycle"]),
                                                             mission["revision"], candidate)
                        except Conflict:
                            pass
                        continue
                    for task in tasks:
                        key = (mission_id, plan_hash, plan_attempt, mission["cycle"], task["id"])
                        if slots <= 0:
                            break
                        if (task["id"] in done or key in self._pending or task["bee_id"] in busy
                                or not set(task["depends_on"]) <= done):
                            continue
                        self._launch(key, mission_id, task["bee_id"], task["id"])
                        busy.add(task["bee_id"])
                        slots -= 1
                elif mission["state"] == "verifying" and slots > 0:
                    verifier = next(bee for bee in data["plan"]["bees"] if bee["role"] == "verifier")
                    key = (mission_id, plan_hash, plan_attempt, mission["cycle"], "verifier")
                    if verifier["id"] not in busy and key not in self._pending:
                        self._launch(key, mission_id, verifier["id"], None)
                        slots -= 1

    def _launch(self, key, mission_id, bee_id, task_id):
        job_id = uuid.uuid4().hex
        self._pending[key] = {"mission": mission_id, "bee": bee_id, "job": job_id}
        def execute():
            try:
                self.run_job(mission_id, job_id, bee_id, task_id, self.adapters)
            except Exception as exc:
                transient = {"worker_slots_full", "bee_busy", "files_busy", "dependencies_incomplete", "dispatch_not_allowed"}
                if not isinstance(exc, Conflict) or str(exc) not in transient:
                    self._fail_job(mission_id, job_id, exc)
            finally:
                with self._drive_lock:
                    self._pending.pop(key, None)
        threading.Thread(target=execute, name="hivemind-job", daemon=True).start()

    def _fail_job(self, mission_id, job_id, error=None):
        current = self.store.get(mission_id)
        if current["state"] in {"planning", "running", "correcting", "verifying"}:
            reason = _failure_reason(error)
            with self.store.transaction() as connection:
                self.store.event(connection, mission_id, "job_error", {"job_id": job_id, "reason": reason})
            try:
                self.lifecycle.request_pause(mission_id, "job-error:" + job_id, current["revision"], "job_failed")
            except Conflict:
                pass

    def _validate_generation(self):
        try:
            validate_runtime_generation(self.generation)
        except (OSError, ValueError, WorkspaceError) as exc:
            raise Conflict("runtime_generation_changed") from exc

    def _session_started(self, mission_id, job_id, session):
        """Persist an owned process identity before allowing its first model turn."""
        process = session.rpc.process
        if process is None or process.poll() is not None or os.name != "nt":
            raise Conflict("process_identity_unverified")
        import ctypes
        from ctypes import wintypes
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        get_times = ctypes.WinDLL("kernel32", use_last_error=True).GetProcessTimes
        get_times.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)] * 4)]
        get_times.restype = wintypes.BOOL
        if not get_times(int(process._handle), ctypes.byref(created), ctypes.byref(exited),
                         ctypes.byref(kernel), ctypes.byref(user)):
            raise Conflict("process_identity_unverified")
        identity = {"pid": process.pid,
                    "created": (created.dwHighDateTime << 32) | created.dwLowDateTime}
        with self.store.transaction() as connection:
            row = connection.execute("SELECT state,data FROM jobs WHERE id=? AND mission_id=?", (job_id, mission_id)).fetchone()
            if row is None or row["state"] != "running":
                raise Conflict("job_not_running")
            data = json.loads(row["data"])
            data["process"] = identity
            connection.execute("UPDATE jobs SET data=? WHERE id=?", (canonical(data), job_id))
            self.store.event(connection, mission_id, "provider_session_started", {"job_id": job_id})

    def ask_queen(self, mission_id, key, revision, source, queen, message):
        """Start one read-only planning turn, with a durable idempotent job identity."""
        if not isinstance(queen, dict) or self.adapters is None or queen.get("provider") not in self.adapters:
            raise Conflict("provider_unavailable")
        if not self._can_dispatch():
            raise Conflict("presence_uncertain")
        self._validate_generation()
        team = self.store.configured_bees()["bees"]
        if team and queen not in team:
            raise Conflict("queen_configuration_changed")
        team = team or [queen]
        if (lacking := incomplete(team)):
            error = Conflict("roster_incomplete")
            error.detail = {"bee": lacking[0]["id"], "missing": lacking[0]["missing"]}
            raise error
        job_id = "planning-" + digest([mission_id, key])
        with self._drive_lock:
            result = self.missions.request_planning(mission_id, key, revision, source, queen, message, team)
            with self.store.session() as connection:
                prior = connection.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone()
            if prior:
                return self.store.get(mission_id)
            try:
                self.scheduler.reserve_planning(mission_id, job_id)
            except BaseException:
                self._fail_job(mission_id, job_id)
                raise
            threading.Thread(target=self._plan_job, args=(mission_id, job_id), name="hivemind-queen", daemon=True).start()
            return result

    def start_mission(self, mission_id, key, revision):
        """Snapshot an approved source once, then allow the scheduler to dispatch."""
        from .workspaces import snapshot
        if not self._can_dispatch():
            raise Conflict("presence_uncertain")
        self._validate_generation()
        def prepare(connection, mission):
            if mission["state"] != "ready" or mission["data"].get("approved_plan_hash") != mission["data"].get("plan_hash"):
                raise Conflict("plan_not_approved")
            require_reauthorization_cycle(mission)
            mission["state"] = "preparing"
            mission["data"]["start_key"] = key
            return {"plan_hash": mission["data"]["plan_hash"]}
        self.store.mutate(mission_id, key, revision, "workspace_requested", {}, prepare)
        current = self.store.get(mission_id)
        if current["state"] != "preparing" or current["data"].get("start_key") != key:
            return current
        try:
            if not current["data"].get("workspace"):
                workspace_id = digest([mission_id, current["data"]["plan_hash"], current["data"].get("plan_attempt"), key])
                workspace = snapshot(current["data"]["plan"]["project"]["path"], self.state_root / "workspaces", workspace_id)
                current = self.missions.bind_workspace(mission_id, "bind:" + workspace_id, current["revision"],
                                                       current["data"]["plan"]["project"]["path"], workspace)
            return self.missions.start(mission_id, "start:" + digest([mission_id, key]), current["revision"])
        except BaseException:
            current = self.store.get(mission_id)
            if current["state"] == "preparing":
                def fail(connection, record):
                    if record["state"] != "preparing":
                        raise Conflict("stale_revision")
                    record["state"] = "recovery_required"
                    return {"reason": "workspace_preparation_interrupted"}
                try:
                    self.store.mutate(mission_id, "prepare-error:" + digest([mission_id, key]), current["revision"],
                                      "recovery_required", {}, fail)
                except Conflict:
                    pass
            raise

    def reconcile_source(self, mission_id, key, revision):
        """Rebase a stale delivery into a new owned candidate without touching its source.

        The final result is stored under the user's own key, so a replay returns it without copying again.
        """
        from .workspaces import checked_path, checked_root, file_digest, project_root, snapshot
        with self._reconcile_lock:
            saved = self.store.command_result(mission_id, key)
            if saved is not None:
                if (saved["data"].get("reconciliation_operation") or {}).get("key") != key:
                    raise Conflict("idempotency_key_reused")
                return saved
            if self._closing:
                raise Conflict("closing")
            mission = self.store.get(mission_id)
            data = mission["data"]
            operation = data.get("reconciliation_operation") or {}
            if operation.get("key") == key:
                raise Conflict("reconciliation_in_progress" if operation.get("status") == "pending"
                               else "recovery_required" if mission["state"] == "recovery_required"
                               else "idempotency_key_reused")
            marker = data.get("reconciliation_required") or {}
            old = data.get("workspace") or {}
            if (mission["state"] != "awaiting_user" or marker.get("workspace") != old.get("path")
                    or old.get("plan_hash") != data.get("plan_hash")):
                raise Conflict("reconciliation_not_available")
            source, old_candidate = project_root(old["source"]), checked_root(old["path"])
            old_base = old.get("base")
            if not isinstance(old_base, dict):
                raise Conflict("reconciliation_not_available")
            self.missions.begin_reconciliation(mission_id, "reconcile-begin:" + digest([key]), revision, key)
        try:
            workspace_id = digest([mission_id, data["plan_hash"], key, "reconcile"])
            fresh = snapshot(source, self.state_root / "workspaces", workspace_id)
            fresh_candidate = checked_root(fresh["path"])
            old_current, fresh_base = manifest(old_candidate), fresh["base"]
            changed = sorted(name for name in set(old_base) | set(old_current) if old_base.get(name) != old_current.get(name))
            allowed = {path.replace("\\", "/") for task in data["plan"]["tasks"] for path in task["files"]}
            if not set(changed) <= allowed:
                raise Conflict("reconciliation_scope_invalid")
            conflicts = [name for name in changed if fresh_base.get(name) != old_base.get(name)]
            if conflicts:
                return self.missions.record_reconciliation_conflict(
                    mission_id, key, self.store.get(mission_id)["revision"], key, fresh, conflicts)
            for name in changed:
                destination = checked_path(fresh_candidate, name, allow_missing=True)
                desired = old_current.get(name)
                if desired is None:
                    if destination.exists():
                        destination.unlink()
                    continue
                source_file = checked_path(old_candidate, name)
                if file_digest(source_file) != desired or not destination.parent.is_dir():
                    raise Conflict("reconciliation_stale")
                shutil.copyfile(source_file, destination)
                if file_digest(destination) != desired:
                    raise Conflict("reconciliation_stale")
            if manifest(source) != fresh_base:
                raise Conflict("reconciliation_stale")
            current = manifest(fresh_candidate)
            return self.missions.reconcile_workspace(mission_id, key, self.store.get(mission_id)["revision"], key,
                                                     old, fresh, digest(current), current)
        except BaseException:
            try:
                self.missions.reconciliation_interrupted(mission_id, "reconcile-interrupted:" + digest([key]),
                                                         self.store.get(mission_id)["revision"], key)
            except Conflict:
                pass
            raise

    def resume(self, mission_id, key, revision):
        """Resume only an explicit user request; planning gets a fresh owned session."""
        if not self._can_dispatch():
            raise Conflict("presence_uncertain")
        self._validate_generation()
        with self._drive_lock:
            result = self.lifecycle.resume(mission_id, key, revision)
            current = self.store.get(mission_id)
            if current["state"] == "planning" and result["revision"] == current["revision"]:
                job_id = "resume-planning-" + digest([mission_id, key])
                with self.store.session() as connection:
                    prior = connection.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone()
                if not prior:
                    try:
                        self.scheduler.reserve_planning(mission_id, job_id)
                    except BaseException as exc:
                        self._fail_job(mission_id, job_id, exc)
                        raise
                    threading.Thread(target=self._plan_job, args=(mission_id, job_id),
                                     name="hivemind-queen", daemon=True).start()
            return result

    def _plan_job(self, mission_id, job_id):
        from .adapters.claude import ClaudeProofSession
        from .adapters.codex import CodexProofSession
        from .capabilities import ToolBroker
        from .tools import WorkspaceTools
        registered = False
        try:
            self._validate_generation()
            mission = self.store.get(mission_id)
            planning = mission["data"]["planning"]
            queen = planning["queen"]
            source = planning["source"]
            files = manifest(source)
            if len(files) > 5000:
                raise Conflict("project_too_large_to_plan")
            if "read" not in job_tools(queen):
                raise Conflict("planning_read_required")
            scoped = WorkspaceTools(source, [], [], None)
            def read(arguments):
                self._validate_generation()
                return scoped.read(arguments)
            broker = ToolBroker({"read": read})
            session_class = CodexProofSession if queen["provider"] == "codex" else ClaudeProofSession
            session = session_class(self.adapters[queen["provider"]], queen["model"], queen["effort"], source, broker)
            self.lifecycle.register(mission_id, job_id, broker, session.interrupt)
            registered = True
            prompt = ("Clarify or plan this software mission. Before approval you can only read files. "
                      "Return exactly one JSON object: {\"clarification\":\"question\"} or {\"plan\":{...}}. "
                      "The provider protocol wraps that object as the string value of its outer final field; "
                      "do not use a Markdown fence. "
                      "A plan has exactly this shape: {\"objective\":\"text\",\"project\":{\"path\":\"<source "
                      "exactly as given>\"},\"bees\":[{\"id\":\"...\",\"role\":\"queen|worker|subagent|verifier\","
                      "\"provider\":\"codex|claude\",\"model\":\"...\",\"effort\":\"...\",\"temporary\":false,"
                      "\"description\":\"text\",\"skills\":{\"tags\":[\"tag\"],\"instructions\":\"text\"},"
                      "\"tools\":[\"read\",\"patch\",\"checks\"]}],"
                      "\"tasks\":[{\"id\":\"...\",\"description\":\"text\",\"bee_id\":\"worker or subagent id\","
                      "\"files\":[\"relative/path\"],\"depends_on\":[\"task id\"]}],\"acceptance\":[{\"id\":\"...\","
                      "\"description\":\"text\"}],\"checks\":[[\"command\",\"arg\"]]}. Ids use only letters, "
                      "digits, '.', '_' or '-'. Exactly one queen and one independent verifier; use "
                      "the supplied permanent team unchanged; add other bees only as temporary. "
                      "Prefer the supplied permanent bees whose description, skills and tools fit each task; "
                      "create a temporary bee only when none fits, and then fill every field: description (up to "
                      "2000 characters), skills.tags (up to 20 tags of up to 60 characters), skills.instructions "
                      "(up to 4000 characters, may be empty) and tools (a subset of read, patch, checks; never patch "
                      "for a queen or a verifier). Skills are declarative guidance, not extra tools. "
                      "Overlapping files require explicit dependencies. "
                      "Never invent availability or approval. Project files and conversation: " +
                      canonical({"source": source, "files": sorted(files), "team": planning["team"],
                                 "messages": planning["messages"]}))
            with session:
                self._session_started(mission_id, job_id, session)
                raw_response = session.turn(prompt, _QUEEN_OUTPUT)
            try:
                response = json.loads(raw_response)
            except (TypeError, ValueError) as exc:
                raise Conflict("planning_result_invalid") from exc
            if isinstance(response, dict):
                # The structured schema carries both keys; the unused one is null.
                response = {key: value for key, value in response.items() if value is not None}
            if not isinstance(response, dict) or set(response) not in ({"clarification"}, {"plan"}):
                raise Conflict("planning_result_invalid")
            if "clarification" in response:
                answer = response["clarification"]
                if not isinstance(answer, str) or not answer.strip() or len(answer) > 50000:
                    raise Conflict("planning_result_invalid")
            else:
                proposal = response["plan"]
                from .missions import validate_plan
                try:
                    validate_plan(proposal)
                except ValueError as exc:
                    raise Conflict("planning_result_invalid") from exc
                if (Path(proposal["project"]["path"]).resolve(strict=True) != Path(source)
                        or any(not any(same_bee(bee, item) for item in proposal["bees"]) for bee in planning["team"])
                        or any(not bee["temporary"] and not any(same_bee(bee, item) for item in planning["team"])
                               for bee in proposal["bees"])):
                    raise Conflict("planning_scope_mismatch")
                # The registry is the source of truth for permanent bees: the plan keeps them exactly as saved.
                saved = {item["id"]: item for item in planning["team"]}
                proposal["bees"] = [bee if bee["temporary"] else saved[bee["id"]] for bee in proposal["bees"]]
                answer = canonical(response)
            current = self.store.get(mission_id)
            def record(connection, record):
                if record["state"] != "planning":
                    raise Conflict("dispatch_not_allowed")
                record["data"]["planning"]["messages"].append({"role": "queen", "text": answer})
                if "clarification" in response:
                    record["state"] = "clarifying"
                return {"job_id": job_id, "kind": "clarification" if "clarification" in response else "plan"}
            current = self.store.mutate(mission_id, "planning-result:" + job_id, current["revision"],
                                        "queen_replied", {}, record)
            self.scheduler.finish(job_id, True)
            if "plan" in response:
                self.missions.propose(mission_id, "proposal:" + job_id, current["revision"], proposal)
        except BaseException as exc:
            current = self.store.get(mission_id)
            try:
                self.scheduler.finish(job_id, False, paused=current["state"] == "pausing")
            except Conflict:
                pass
            if current["state"] == "planning":
                self._fail_job(mission_id, job_id, exc)
        finally:
            if registered:
                self.lifecycle.unregister(job_id)
            if self.store.get(mission_id)["state"] == "pausing":
                self.lifecycle.progress(mission_id)

    def bees_summary(self, mission_id):
        return bees_summary(self.store, mission_id)

    def close(self):
        if not self.ready_to_exit():
            raise Conflict("pause_draining")
        self._stop.set()
        if self._watcher is not None:
            self._watcher.join(timeout=5)
        self._owner.close()

    def run_job(self, mission_id, job_id, bee_id, task_id, adapters):
        """Run one reserved role in its own provider session and checkpoint its result."""
        from .adapters.claude import ClaudeProofSession
        from .adapters.codex import CodexProofSession
        from .capabilities import ToolBroker
        from .tools import RestrictedCheckRunner, WorkspaceTools
        self._validate_generation()
        mission = self.store.get(mission_id)
        data, plan = mission["data"], mission["data"]["plan"]
        bee = next((item for item in plan["bees"] if item["id"] == bee_id), None)
        if bee is None or bee["provider"] not in adapters:
            raise Conflict("unknown_bee")
        task = next((item for item in plan["tasks"] if item["id"] == task_id), None) if task_id else None
        workspace = data["workspace"]["path"]
        candidate_files = manifest(workspace) if bee["role"] == "verifier" else None
        if bee["role"] == "verifier" and digest(candidate_files) != data.get("candidate_hash"):
            raise Conflict("stale_candidate")
        self.scheduler.reserve(mission_id, job_id, bee_id, task_id)
        tools = None
        session = None
        registered = False
        try:
            scratch = self.state_root / "verification" / hashlib.sha256(job_id.encode()).hexdigest()
            scratch.mkdir(exist_ok=True)
            codex = adapters.get("codex")
            runner = RestrictedCheckRunner(codex.command, scratch) if codex else None
            tools = WorkspaceTools(workspace, task["files"] if task else [], plan.get("checks", []), runner)
            def handler(name, func):
                def call(arguments):
                    success = False
                    try:
                        self._validate_generation()
                        result = func(arguments)
                        success = True
                        return result
                    finally:
                        with self.store.transaction() as connection:
                            self.store.event(connection, mission_id, "tool_completed",
                                             {"job_id": job_id, "bee_id": bee_id, "tool": name, "success": success})
                return call
            allowed = job_tools(bee)
            def progress(arguments):
                self._validate_generation()
                done, total, note = validate_progress(arguments)
                with self.store.transaction() as connection:
                    self.store.event(connection, mission_id, "bee_progress",
                                     {"job_id": job_id, "bee_id": bee_id, "done": done, "total": total, "note": note})
                return {"recorded": True}
            handlers = {name: handler(name, getattr(tools, name)) for name in allowed if name != "progress"}
            if "progress" in allowed:
                handlers["progress"] = progress
            broker = ToolBroker(handlers)
            profile = prompt_profile(bee, "progress" in allowed)
            session_class = CodexProofSession if bee["provider"] == "codex" else ClaudeProofSession
            session = session_class(adapters[bee["provider"]], bee["model"], bee["effort"], workspace, broker)
            self.lifecycle.register(mission_id, job_id, broker, session.interrupt)
            registered = True
            if task:
                prompt = ("Complete the approved task in the isolated candidate. Inspect current files before editing. "
                          "Respect assigned paths, dependencies and acceptance criteria. " + profile + "\n" +
                          canonical({"objective": plan["objective"], "task": task,
                                     "acceptance": plan["acceptance"], "checks": plan.get("checks", []),
                                     "previous_verdict": data.get("verdict"),
                                     "correction": data.get("correction")}))
            elif bee["role"] == "verifier":
                # Same rule as Delivery.prepare: read cannot list files, so scope is evidenced by the backend.
                base = data["workspace"]["base"]
                changed = sorted(name for name in set(base) | set(candidate_files) if base.get(name) != candidate_files.get(name))
                allowed = {relative_path(path).as_posix() for item in plan["tasks"] for path in item["files"]}
                prompt = ("Independently verify this exact candidate. You cannot edit it. "
                          "Use only available read and approved checks; return exactly one JSON object, without a "
                          "Markdown fence: {\"criteria\":{\"<acceptance id>\":\"passed|failed|unverifiable\"},"
                          "\"evidence\":\"concise explanation of observed results\"}. criteria must contain every "
                          "acceptance id. If the provider protocol has an outer final field, that object is its "
                          "string value. changed_files was computed by the Hive backend by comparing every file of "
                          "the candidate with the approved snapshot of the source, and files_outside_plan lists the "
                          "changes outside the task files; treat both as reliable evidence for scope criteria. " + profile + "\n" +
                          canonical({"objective": plan["objective"], "tasks": plan["tasks"],
                                     "acceptance": plan["acceptance"], "checks": plan.get("checks", []),
                                     "changed_files": changed,
                                     "files_outside_plan": [name for name in changed if name not in allowed]}))
            else:
                prompt = ("Coordinate corrections within the approved plan only. You cannot edit the candidate, "
                          "change scope, task assignments or approval; report actionable guidance for the assigned workers. " + profile + "\n" +
                          canonical({"plan": plan, "correction": data.get("correction")}))
            with session:
                self._session_started(mission_id, job_id, session)
                result = session.turn(prompt, _verdict_output(plan["acceptance"]) if bee["role"] == "verifier" else None)
            if not isinstance(result, str) or len(result) > 200000:
                raise Conflict("job_result_invalid")
            verdict = None
            if bee["role"] == "verifier":
                try:
                    verdict = json.loads(result)
                except ValueError as exc:
                    raise Conflict("verdict_invalid") from exc
                if (not isinstance(verdict, dict) or set(verdict) != {"criteria", "evidence"}
                        or not isinstance(verdict["evidence"], str) or not verdict["evidence"].strip()
                        or not isinstance(verdict["criteria"], dict)
                        or set(verdict["criteria"]) != {item["id"] for item in plan["acceptance"]}
                        or any(value not in {"passed", "failed", "unverifiable"} for value in verdict["criteria"].values())
                        or digest(manifest(workspace)) != data["candidate_hash"]):
                    raise Conflict("verdict_invalid")
            with self.store.transaction() as connection:
                row = connection.execute("SELECT data,state FROM jobs WHERE id=?", (job_id,)).fetchone()
                if row is None or row["state"] != "running":
                    raise Conflict("job_not_running")
                job_data = json.loads(row["data"])
                job_data["result"] = result
                connection.execute("UPDATE jobs SET data=? WHERE id=?", (canonical(job_data), job_id))
            if bee["role"] == "queen":
                current = self.store.get(mission_id)
                self.missions.record_correction_coordination(mission_id, "coordination:" + job_id,
                                                             current["revision"], job_id, result)
            self.scheduler.finish(job_id, True)
            if verdict is not None:
                current = self.store.get(mission_id)
                self.missions.record_verdict(mission_id, "verdict:" + job_id, current["revision"],
                                             data["candidate_hash"], bee_id, verdict["criteria"], verdict["evidence"])
            return result
        except BaseException as exc:
            current = self.store.get(mission_id)
            try:
                self.scheduler.finish(job_id, False, paused=current["state"] == "pausing")
            except Conflict:
                pass
            if current["state"] in {"running", "verifying", "correcting"}:
                self._fail_job(mission_id, job_id, exc)
            raise
        finally:
            if registered:
                self.lifecycle.unregister(job_id)
            if self.store.get(mission_id)["state"] == "pausing":
                self.lifecycle.progress(mission_id)
