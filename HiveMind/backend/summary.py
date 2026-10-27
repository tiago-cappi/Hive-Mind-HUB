"""Per-bee mission summary (`bees_summary`), computed from the plan, jobs and events in the database."""

from .bees import view

_ACTIVE = {"running", "tool_active", "draining"}
_JOB_STATE = {"running": "running", "tool_active": "running", "draining": "running",
              "succeeded": "completed", "failed": "failed", "unknown": "failed"}
_TOOLS = ("read", "patch", "checks", "progress")


def bees_summary(store, mission_id):
    """One entry per active bee: the plan's bees, or the planning team for a mission without a plan."""
    mission = store.get(mission_id)
    data = mission["data"]
    plan = data.get("plan") if isinstance(data.get("plan"), dict) else {}
    bees = plan.get("bees") or (data.get("planning") or {}).get("team") or []
    tasks = plan.get("tasks") or []
    generation = lambda job: (job["data"].get("plan_hash") == data.get("plan_hash")
                              and job["data"].get("plan_attempt") == data.get("plan_attempt"))
    jobs = [job for job in store.jobs(mission_id) if job["data"].get("planning") or generation(job)]
    # Cycle of the plan in force: only these jobs decide the status of a task.
    now = [job for job in jobs if generation(job) and job["data"].get("cycle") == mission["cycle"]
           and job["data"].get("task_id")]
    done = {job["data"]["task_id"] for job in now if job["state"] == "succeeded"}
    used, progress = {}, {}
    for event in store.bee_events(mission_id):
        bee_id = event["data"].get("bee_id")
        if event["kind"] == "bee_progress":
            used.setdefault(bee_id, {}).setdefault("progress", 0)
            used[bee_id]["progress"] += 1
            progress[(bee_id, event["data"].get("job_id"))] = {
                "done": event["data"].get("done"), "total": event["data"].get("total"),
                "note": event["data"].get("note"), "seq": event["seq"]}
        elif event["data"].get("success") is True and event["data"].get("tool") in _TOOLS:
            used.setdefault(bee_id, {}).setdefault(event["data"]["tool"], 0)
            used[bee_id][event["data"]["tool"]] += 1

    def status(task):
        mine = [job for job in now if job["data"]["task_id"] == task["id"]]
        if task["id"] in done:
            return "done"
        if any(job["state"] in _ACTIVE for job in mine):
            return "running"
        if mine and mine[-1]["state"] in {"failed", "unknown"}:
            return "failed"
        return "waiting" if not set(task.get("depends_on", [])) <= done else "pending"

    result = []
    for bee in bees:
        items = [{"id": task["id"], "description": task.get("description", ""), "status": status(task),
                  "depends_on": list(task.get("depends_on", [])), "files": list(task.get("files", []))}
                 for task in tasks if task.get("bee_id") == bee["id"]]
        open_items = [item for item in items if item["status"] != "done"]
        running = [item for item in open_items if item["status"] == "running"]
        last = next((job for job in reversed(jobs) if job["bee_id"] == bee["id"]), None)
        own = view(bee)
        result.append({
            "id": bee["id"], "role": bee["role"], "temporary": bool(bee.get("temporary")), "active": True,
            **own, "provider": bee.get("provider"), "model": bee.get("model"), "effort": bee.get("effort"),
            "tasks": {"total": len(items), "done": len(items) - len(open_items),
                      "current": (running or open_items or [{"id": None}])[0]["id"], "items": items},
            "progress": progress.get((bee["id"], last["id"])) if last else None,
            "tools_used": {name: used.get(bee["id"], {}).get(name, 0) for name in _TOOLS},
            "job": {"state": _JOB_STATE.get(last["state"]) if last else None,
                    "cycle": last["data"].get("cycle") if last else None, "started": last is not None}})
    return result
