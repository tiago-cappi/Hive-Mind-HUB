"""Mission transitions and immutable, hash-addressed human approvals."""

from pathlib import Path
import json
import time

from .adapters.base import safe_name
from .bees import require_profile
from .store import Conflict, canonical, digest
from .workspaces import WorkspaceError, path_key


class InvalidTransition(Conflict):
    pass


def _require(mission, *states):
    if mission["state"] not in states:
        raise InvalidTransition("invalid_state:" + mission["state"])


def require_reauthorization_cycle(mission):
    """A plan reauthorized after a ceiling rejection needs a new cycle, so the limit must be raised first."""
    if mission["data"].get("pending_reauthorization") is not None and mission["cycle"] >= mission["cycle_limit"]:
        raise Conflict("cycle_limit_reached")


def _journal_touched(path):
    """True when the journal may mean the source was changed: unreadable, oversized or any item attempted."""
    if not path.exists():
        return False
    try:
        if path.stat().st_size > 10 * 1024 * 1024:
            return True
        items = json.loads(path.read_text(encoding="utf-8"))["items"]
        if not isinstance(items, list):
            return True
        return any(item["attempted"] is not False for item in items)
    except (OSError, ValueError, KeyError, TypeError):
        return True


def _relative_path(value):
    try:
        path_key(value)
    except WorkspaceError:
        return False
    return True


def validate_plan(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get("project"), dict):
        raise ValueError("invalid plan project")
    if not isinstance(plan.get("objective"), str) or not plan["objective"].strip():
        raise ValueError("plan objective required")
    project = plan["project"]
    if not isinstance(project.get("path"), str) or not project["path"]:
        raise ValueError("project path required")
    bees, tasks = plan.get("bees"), plan.get("tasks")
    if not isinstance(bees, list) or not bees or not isinstance(tasks, list) or not tasks:
        raise ValueError("plan needs bees and tasks")
    roster = {}
    for bee in bees:
        if not isinstance(bee, dict) or not safe_name(bee.get("id")) or bee["id"] in roster:
            raise ValueError("invalid bee")
        if (bee.get("role") not in {"queen", "worker", "subagent", "verifier"}
                or bee.get("provider") not in {"codex", "claude"}
                or not safe_name(bee.get("model")) or not safe_name(bee.get("effort"))
                or type(bee.get("temporary")) is not bool):
            raise ValueError("invalid bee configuration")
        require_profile(bee)
        roster[bee["id"]] = bee
    if sum(b["role"] == "queen" for b in bees) != 1 or sum(b["role"] == "verifier" for b in bees) != 1:
        raise ValueError("exactly one queen and independent verifier required")
    tasks_by_id = {}
    for task in tasks:
        if not isinstance(task, dict) or not safe_name(task.get("id")) or task["id"] in tasks_by_id:
            raise ValueError("invalid task")
        if not isinstance(task.get("description"), str) or not task["description"].strip():
            raise ValueError("task description required")
        bee = roster.get(task.get("bee_id"))
        if not bee or bee["role"] not in {"worker", "subagent"}:
            raise ValueError("task must use a worker")
        files, depends = task.get("files"), task.get("depends_on")
        if not isinstance(files, list) or not files or not all(_relative_path(path) for path in files):
            raise ValueError("invalid task files")
        if len({path_key(path) for path in files}) != len(files):
            raise ValueError("duplicate task files")
        if not isinstance(depends, list) or any(not safe_name(dep) for dep in depends):
            raise ValueError("invalid dependencies")
        tasks_by_id[task["id"]] = task
    visiting, visited = set(), set()
    def visit(name):
        if name in visiting:
            raise ValueError("dependency cycle")
        if name not in tasks_by_id:
            raise ValueError("unknown dependency")
        if name not in visited:
            visiting.add(name)
            for dependency in tasks_by_id[name]["depends_on"]:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
    for task_id in tasks_by_id:
        visit(task_id)
    def ancestors(name):
        result = set(tasks_by_id[name]["depends_on"])
        for dependency in tuple(result):
            result.update(ancestors(dependency))
        return result
    prior = list(tasks_by_id.values())
    for index, task in enumerate(prior):
        for other in prior[index + 1:]:
            overlap = {path_key(path) for path in task["files"]} & {path_key(path) for path in other["files"]}
            if overlap and task["id"] not in ancestors(other["id"]) and other["id"] not in ancestors(task["id"]):
                raise ValueError("overlapping tasks require dependency")
    acceptance = plan.get("acceptance")
    if (not isinstance(acceptance, list) or not acceptance or any(
            not isinstance(item, dict) or not safe_name(item.get("id"))
            or not isinstance(item.get("description"), str) or not item["description"].strip()
            for item in acceptance)):
        raise ValueError("invalid acceptance criteria")
    if len({item["id"] for item in acceptance}) != len(acceptance):
        raise ValueError("duplicate acceptance criterion")
    checks = plan.get("checks", [])
    if not isinstance(checks, list) or any(not isinstance(check, list) or not check
            or any(not isinstance(arg, str) or not arg for arg in check) for check in checks):
        raise ValueError("invalid checks")
    return digest(plan)


class Missions:
    def __init__(self, store):
        self.store = store

    def create(self, mission_id, key, title, cycle_limit=3):
        return self.store.create(mission_id, key, title, cycle_limit)

    def request_planning(self, mission_id, key, revision, source, queen, message, team=None):
        from .workspaces import project_root
        source = str(project_root(source))
        if (not isinstance(queen, dict) or queen.get("role") != "queen" or not safe_name(queen.get("id"))
                or queen.get("provider") not in {"codex", "claude"} or not safe_name(queen.get("model"))
                or not safe_name(queen.get("effort")) or type(queen.get("temporary")) is not bool
                or not isinstance(message, str) or not message.strip() or len(message) > 50000):
            raise ValueError("invalid planning request")
        def change(connection, mission):
            _require(mission, "draft", "clarifying", "awaiting_plan_approval", "awaiting_user")
            previous = mission["data"].get("planning")
            if previous and previous["source"] != source:
                raise Conflict("project_mismatch")
            planning = previous or {"source": source, "messages": []}
            planning["queen"] = queen
            planning["team"] = team or [queen]
            planning["messages"].append({"role": "user", "text": message})
            mission["data"]["planning"] = planning
            mission["data"]["approved_plan_hash"] = None
            mission["state"] = "planning"
            return {"queen_id": queen["id"]}
        return self.store.mutate(mission_id, key, revision, "planning_requested",
                                 {"source": source, "queen": queen, "message": message, "team": team}, change)

    def propose(self, mission_id, key, revision, plan):
        plan_hash = validate_plan(plan)
        def change(connection, mission):
            _require(mission, "draft", "clarifying", "planning", "awaiting_plan_approval", "ready", "awaiting_user")
            data = mission["data"]
            if connection.execute("SELECT 1 FROM jobs WHERE mission_id=? AND state='unknown' LIMIT 1", (mission_id,)).fetchone():
                raise Conflict("recovery_required")
            attempt = data.get("plan_attempt", 0) + 1
            if type(attempt) is not int or attempt < 1:
                raise Conflict("attempt_unverified")
            history = data.setdefault("plan_history", [])
            history.append({"hash": plan_hash, "attempt": attempt, "plan": plan})
            previous_workspace = data.get("workspace")
            if previous_workspace:
                data.setdefault("workspace_history", []).append({"reason": "plan_reauthorized"
                                                                     if data.get("plan_hash") == plan_hash else "plan_replaced",
                                                                     "plan_hash": data.get("plan_hash"),
                                                                     "plan_attempt": data.get("plan_attempt"),
                                                                     "workspace": previous_workspace})
                data.pop("workspace", None)
            if data.get("reconciliation_required"):
                data.setdefault("reconciliation_history", []).append(data["reconciliation_required"])
            prior_outcome = data.get("attempt_outcome")
            data.update({"plan": plan, "plan_hash": plan_hash, "plan_attempt": attempt,
                         "approved_plan_hash": None, "approved_plan_attempt": None,
                         "candidate_hash": None, "delivery": None, "delivery_hash": None,
                         "approved_delivery_hash": None, "verdict": None,
                         "verification_generation": None, "correction": None,
                         "reconciliation_required": None})
            if isinstance(prior_outcome, dict):
                data["pending_reauthorization"] = prior_outcome
            else:
                data.pop("pending_reauthorization", None)
            mission["state"] = "awaiting_plan_approval"
            connection.execute("UPDATE bees SET active=0 WHERE mission_id=?", (mission_id,))
            return {"plan_hash": plan_hash, "plan_attempt": attempt}
        return self.store.mutate(mission_id, key, revision, "plan_proposed", {"plan": plan}, change)

    def approve_plan(self, mission_id, key, revision, plan_hash):
        def change(connection, mission):
            _require(mission, "awaiting_plan_approval")
            data = mission["data"]
            if not isinstance(plan_hash, str) or plan_hash != data.get("plan_hash"):
                raise Conflict("stale_plan")
            require_reauthorization_cycle(mission)
            data["approved_plan_hash"] = plan_hash
            data["approved_plan_attempt"] = data.get("plan_attempt")
            mission["state"] = "ready"
            for bee in data["plan"]["bees"]:
                connection.execute("INSERT INTO bees VALUES(?,?,?,?,?,?) ON CONFLICT(mission_id,id) "
                    "DO UPDATE SET role=excluded.role,temporary=excluded.temporary,active=1,data=excluded.data",
                    (mission_id, bee["id"], bee["role"], int(bee["temporary"]), 1, canonical(bee)))
            return {"plan_hash": plan_hash, "plan_attempt": data["plan_attempt"]}
        return self.store.mutate(mission_id, key, revision, "plan_approved", {"plan_hash": plan_hash}, change)

    def bind_workspace(self, mission_id, key, revision, source, workspace):
        # Internal service operation: the UI cannot submit or select snapshot metadata.
        from pathlib import Path
        from .workspaces import _excluded, checked_root, manifest, project_root
        source, candidate = project_root(source), checked_root(workspace["path"])
        if (source == candidate or candidate in source.parents or
                source in candidate.parents and not _excluded(candidate.relative_to(source).parts)):
            raise Conflict("invalid_workspace_location")
        base = workspace.get("base")
        if not isinstance(base, dict) or digest(base) != workspace.get("base_hash"):
            raise Conflict("invalid_workspace_base")
        if manifest(source) != base or manifest(candidate) != base:
            raise Conflict("source_changed")
        def change(connection, mission):
            _require(mission, "ready", "preparing")
            data = mission["data"]
            if Path(data["plan"]["project"]["path"]).resolve(strict=True) != source:
                raise Conflict("project_mismatch")
            data["workspace"] = {"source": str(source), "path": str(candidate),
                                 "base": base, "base_hash": digest(base),
                                 "kind": workspace.get("kind"), "head": workspace.get("head"),
                                 "plan_hash": data["plan_hash"], "plan_attempt": data.get("plan_attempt")}
            return {"base_hash": digest(base), "kind": workspace.get("kind")}
        return self.store.mutate(mission_id, key, revision, "workspace_bound",
                                 {"base_hash": digest(base), "candidate": str(candidate)}, change)

    def start(self, mission_id, key, revision):
        def change(connection, mission):
            _require(mission, "ready", "preparing")
            data = mission["data"]
            if (not data.get("plan_hash") or data.get("approved_plan_hash") != data["plan_hash"]
                    or data.get("approved_plan_attempt") != data.get("plan_attempt")):
                raise Conflict("plan_not_approved")
            if (not data.get("workspace") or data["workspace"].get("plan_hash") != data["plan_hash"]
                    or data["workspace"].get("plan_attempt") != data.get("plan_attempt")):
                raise Conflict("workspace_required")
            outcome = data.get("pending_reauthorization")
            if outcome is not None:
                require_reauthorization_cycle(mission)
                data.setdefault("attempt_history", []).append(outcome)
                data.pop("pending_reauthorization", None)
                data.pop("attempt_outcome", None)
                mission["cycle"] += 1
            mission["state"] = "running"
            return {"plan_hash": data["plan_hash"], "plan_attempt": data["plan_attempt"], "cycle": mission["cycle"]}
        return self.store.mutate(mission_id, key, revision, "mission_started", {}, change)

    def begin_verification(self, mission_id, key, revision, candidate_hash):
        if not isinstance(candidate_hash, str) or len(candidate_hash) != 64 or any(c not in "0123456789abcdef" for c in candidate_hash):
            raise ValueError("invalid candidate hash")
        def change(connection, mission):
            _require(mission, "running", "correcting")
            data = mission["data"]
            if connection.execute("SELECT 1 FROM jobs WHERE mission_id=? AND state IN "
                                  "('running','tool_active','draining') LIMIT 1", (mission_id,)).fetchone():
                raise Conflict("jobs_still_running")
            workspace = data.get("workspace") or {}
            if (workspace.get("plan_hash") != data.get("plan_hash")
                    or workspace.get("plan_attempt") != data.get("plan_attempt")):
                raise Conflict("workspace_generation_mismatch")
            mission["state"] = "verifying"
            mission["data"].update({"candidate_hash": candidate_hash, "verdict": None,
                                    "delivery": None, "delivery_hash": None, "approved_delivery_hash": None,
                                    "verification_generation": {"plan_hash": data["plan_hash"], "plan_attempt": data["plan_attempt"],
                                                              "candidate_hash": candidate_hash,
                                                              "cycle": mission["cycle"]}})
            return {"candidate_hash": candidate_hash, "plan_attempt": data["plan_attempt"], "cycle": mission["cycle"]}
        return self.store.mutate(mission_id, key, revision, "verification_started", {"candidate_hash": candidate_hash}, change)

    def record_verdict(self, mission_id, key, revision, candidate_hash, verifier_id, criteria, evidence=None):
        if not isinstance(criteria, dict) or not criteria or any(
                not isinstance(name, str) or not name or status not in {"passed", "failed", "unverifiable"}
                for name, status in criteria.items()):
            raise ValueError("invalid verification criteria")
        def change(connection, mission):
            _require(mission, "verifying")
            data = mission["data"]
            generation = data.get("verification_generation") or {}
            if (data.get("candidate_hash") != candidate_hash or generation.get("candidate_hash") != candidate_hash
                    or generation.get("plan_hash") != data.get("plan_hash")
                    or generation.get("plan_attempt") != data.get("plan_attempt")
                    or generation.get("cycle") != mission["cycle"]):
                raise Conflict("stale_candidate")
            bees = data["plan"]["bees"]
            if not any(b["id"] == verifier_id and b["role"] == "verifier" for b in bees):
                raise Conflict("independent_verifier_required")
            if set(criteria) != {item["id"] for item in data["plan"]["acceptance"]}:
                raise Conflict("verification_criteria_incomplete")
            passed = all(status == "passed" for status in criteria.values())
            verdict = {"candidate_hash": candidate_hash, "plan_hash": data["plan_hash"], "plan_attempt": data["plan_attempt"], "verifier_id": verifier_id,
                       "criteria": criteria, "evidence": evidence if isinstance(evidence, str) else "",
                       "passed": passed, "cycle": mission["cycle"]}
            data.setdefault("verification_history", []).append(verdict)
            data["verdict"] = verdict
            if passed:
                mission["state"] = "awaiting_delivery_approval"
            elif mission["cycle"] >= mission["cycle_limit"]:
                mission["state"] = "awaiting_user"
                data["attempt_outcome"] = {"plan_hash": data["plan_hash"], "plan_attempt": data["plan_attempt"],
                                           "cycle": mission["cycle"], "status": "cycle_limit"}
            else:
                mission["cycle"] += 1
                mission["state"] = "correcting"
                data["correction"] = {"plan_hash": data["plan_hash"], "cycle": mission["cycle"],
                                      "verdict": verdict, "status": "pending"}
            return {"passed": passed, "cycle": verdict["cycle"], "candidate_hash": candidate_hash}
        return self.store.mutate(mission_id, key, revision, "verification_recorded",
                                 {"candidate_hash": candidate_hash, "verifier_id": verifier_id, "criteria": criteria}, change)

    def approve_delivery(self, mission_id, key, revision, candidate_hash, delivery_hash):
        if not isinstance(delivery_hash, str) or len(delivery_hash) != 64 or any(c not in "0123456789abcdef" for c in delivery_hash):
            raise ValueError("invalid delivery hash")
        def change(connection, mission):
            _require(mission, "awaiting_delivery_approval")
            data = mission["data"]
            verdict = data.get("verdict") or {}
            if (verdict.get("passed") is not True or candidate_hash != data.get("candidate_hash")
                    or verdict.get("candidate_hash") != candidate_hash or delivery_hash != data.get("delivery_hash")):
                raise Conflict("stale_delivery")
            data["approved_delivery_hash"] = delivery_hash
            mission["state"] = "delivery_approved"
            return {"candidate_hash": candidate_hash, "delivery_hash": delivery_hash}
        return self.store.mutate(mission_id, key, revision, "delivery_approved",
                                 {"candidate_hash": candidate_hash, "delivery_hash": delivery_hash}, change)

    def abandon(self, mission_id, key, revision, journal_root):
        """Close a stuck recovery_required mission for good; history, jobs and files stay untouched."""
        def change(connection, mission):
            _require(mission, "recovery_required")
            data = mission["data"]
            delivery_hash = data.get("delivery_hash")
            last = connection.execute("SELECT kind FROM events WHERE mission_id=? AND kind IN "
                                      "('delivery_applying','delivery_recovered') ORDER BY seq DESC LIMIT 1",
                                      (mission_id,)).fetchone()
            # A journal is pending only if an apply started after the last recovery and the source may have been touched.
            if delivery_hash and last and last["kind"] == "delivery_applying" and _journal_touched(
                    Path(journal_root) / ("delivery-" + digest([mission_id, delivery_hash])) / "journal.json"):
                raise Conflict("delivery_recovery_required")
            data["abandoned"] = {"previous_state": mission["state"], "at": time.time()}
            mission["state"] = "abandoned"
            return {"previous_state": data["abandoned"]["previous_state"]}
        return self.store.mutate(mission_id, key, revision, "mission_abandoned", {}, change)

    def set_cycle_limit(self, mission_id, key, revision, limit):
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("invalid cycle limit")
        def change(connection, mission):
            if mission["state"] == "abandoned":
                raise InvalidTransition("invalid_state:abandoned")
            if limit < mission["cycle"]:
                raise Conflict("limit_below_current_cycle")
            mission["cycle_limit"] = limit
            return {"limit": limit, "cycle": mission["cycle"]}
        return self.store.mutate(mission_id, key, revision, "cycle_limit_changed", {"limit": limit}, change)

    def begin_reconciliation(self, mission_id, key, revision, operation_key):
        """Persist a request before any fresh candidate is created."""
        def change(connection, mission):
            _require(mission, "awaiting_user")
            data = mission["data"]
            marker, workspace = data.get("reconciliation_required") or {}, data.get("workspace") or {}
            if (marker.get("workspace") != workspace.get("path") or workspace.get("plan_hash") != data.get("plan_hash")
                    or workspace.get("plan_attempt") != data.get("plan_attempt")):
                raise Conflict("reconciliation_not_available")
            if (data.get("reconciliation_operation") or {}).get("status") == "pending":
                raise Conflict("reconciliation_in_progress")
            data["reconciliation_operation"] = {"key": operation_key, "status": "pending", "workspace": workspace["path"],
                                                  "plan_hash": data["plan_hash"], "plan_attempt": data["plan_attempt"]}
            return {"workspace": workspace["path"], "plan_hash": data["plan_hash"], "plan_attempt": data["plan_attempt"]}
        return self.store.mutate(mission_id, key, revision, "source_reconciliation_requested",
                                 {"operation": operation_key}, change)

    def reconciliation_interrupted(self, mission_id, key, revision, operation_key):
        def change(connection, mission):
            data = mission["data"]
            operation = data.get("reconciliation_operation") or {}
            if operation.get("key") != operation_key or operation.get("status") != "pending":
                raise Conflict("reconciliation_not_available")
            operation["status"] = "recovery_required"
            data["reconciliation_operation"] = operation
            mission["state"] = "recovery_required"
            return {"operation": operation_key}
        return self.store.mutate(mission_id, key, revision, "source_reconciliation_interrupted",
                                 {"operation": operation_key}, change)

    def reconcile_workspace(self, mission_id, key, revision, operation_key, old_workspace, workspace, candidate_hash, changes):
        """Bind a separately rebased candidate and force a fresh independent verification."""
        from .workspaces import checked_root, manifest, project_root
        source, old_candidate = project_root(old_workspace["source"]), checked_root(old_workspace["path"])
        candidate = checked_root(workspace["path"])
        base = workspace.get("base")
        if (not isinstance(base, dict) or digest(base) != workspace.get("base_hash")
                or manifest(source) != base or manifest(candidate) != changes):
            raise Conflict("reconciliation_stale")
        def change(connection, mission):
            _require(mission, "awaiting_user")
            data = mission["data"]
            marker = data.get("reconciliation_required") or {}
            current = data.get("workspace") or {}
            operation = data.get("reconciliation_operation") or {}
            if (marker.get("workspace") != current.get("path") or current != old_workspace
                    or current.get("plan_hash") != data.get("plan_hash") or current.get("source") != str(source)
                    or operation.get("key") != operation_key or operation.get("status") != "pending"):
                raise Conflict("reconciliation_not_available")
            data.setdefault("workspace_history", []).append({"reason": "source_stale", "workspace": current,
                                                                 "delivery_hash": marker.get("delivery_hash")})
            if data.get("delivery"):
                data.setdefault("delivery_history", []).append({"reason": "source_stale",
                                                                   "delivery_hash": data.get("delivery_hash"),
                                                                   "delivery": data["delivery"]})
            data.update({"workspace": {"source": str(source), "path": str(candidate), "base": base,
                                        "base_hash": digest(base), "kind": workspace.get("kind"),
                         "head": workspace.get("head"), "plan_hash": data["plan_hash"], "plan_attempt": data.get("plan_attempt")},
                         "candidate_hash": candidate_hash, "verdict": None, "verification_generation": {
                             "plan_hash": data["plan_hash"], "plan_attempt": data.get("plan_attempt"), "candidate_hash": candidate_hash,
                             "cycle": mission["cycle"]}, "delivery": None, "delivery_hash": None,
                         "approved_delivery_hash": None, "reconciliation_required": None, "correction": None,
                         "reconciliation_operation": {**operation, "status": "completed"}})
            mission["state"] = "verifying"
            return {"base_hash": digest(base), "candidate_hash": candidate_hash,
                    "preserved_workspace": str(old_candidate)}
        return self.store.mutate(mission_id, key, revision, "source_reconciled",
                                 {"base_hash": digest(base), "candidate_hash": candidate_hash}, change)

    def record_reconciliation_conflict(self, mission_id, key, revision, operation_key, workspace, conflicts):
        if not isinstance(conflicts, list) or not conflicts or any(not isinstance(path, str) for path in conflicts):
            raise ValueError("invalid reconciliation conflicts")
        def change(connection, mission):
            _require(mission, "awaiting_user")
            data = mission["data"]
            marker = data.get("reconciliation_required") or {}
            current = data.get("workspace") or {}
            operation = data.get("reconciliation_operation") or {}
            if (marker.get("workspace") != current.get("path") or operation.get("key") != operation_key
                    or operation.get("status") != "pending"):
                raise Conflict("reconciliation_not_available")
            marker["candidate"] = workspace
            marker["conflicts"] = sorted(conflicts)
            data["reconciliation_required"] = marker
            data["reconciliation_operation"] = {**operation, "status": "conflict"}
            return {"conflicts": sorted(conflicts), "candidate": workspace["path"]}
        return self.store.mutate(mission_id, key, revision, "source_reconciliation_conflict",
                                 {"conflicts": sorted(conflicts)}, change)

    def record_correction_coordination(self, mission_id, key, revision, job_id, feedback):
        if not isinstance(feedback, str) or not feedback.strip() or len(feedback) > 200000:
            raise ValueError("invalid correction feedback")
        def change(connection, mission):
            _require(mission, "correcting")
            data = mission["data"]
            correction = data.get("correction") or {}
            if (correction.get("status") != "pending" or correction.get("plan_hash") != data.get("plan_hash")
                    or correction.get("cycle") != mission["cycle"]):
                raise Conflict("correction_not_pending")
            correction["status"] = "coordinated"
            correction["job_id"] = job_id
            correction["feedback"] = feedback
            data["correction"] = correction
            return {"cycle": mission["cycle"], "plan_hash": data["plan_hash"]}
        return self.store.mutate(mission_id, key, revision, "correction_coordinated", {"job_id": job_id}, change)
