"""Same-origin local API; provider and filesystem operations stay in the service."""

from dataclasses import asdict
from urllib.parse import urlsplit
import uuid

from flask import Blueprint, jsonify, request

from .manager import get_service
from .store import Conflict


blueprint = Blueprint("hivemind_backend", __name__, url_prefix="/hive-api")


@blueprint.before_request
def local_origin():
    hostname = urlsplit("http://" + request.host).hostname
    if hostname not in {"127.0.0.1", "localhost"} or request.remote_addr not in {"127.0.0.1", "::1"}:
        return jsonify(error="local_origin_required"), 403
    site = request.headers.get("Sec-Fetch-Site")
    if site not in (None, "same-origin", "none"):
        return jsonify(error="local_origin_required"), 403
    if request.method != "GET":
        if request.headers.get("Origin") != request.host_url.rstrip("/") or not request.is_json:
            return jsonify(error="local_origin_required"), 403
        if request.content_length is not None and request.content_length > 1024 * 1024:
            return jsonify(error="request_too_large"), 413


@blueprint.errorhandler(Exception)
def error_response(error):
    name = type(error).__name__
    if name == "NotFound":
        return jsonify(error="not_found"), 404
    if name in {"Conflict", "InvalidTransition", "WorkspaceError"}:
        code = str(error)
        if not code or len(code) > 100 or not all(char.isalnum() or char in "_:.-" for char in code):
            code = "conflict"
        return jsonify(error=code, **getattr(error, "detail", {})), 409
    if isinstance(error, (ValueError, KeyError, TypeError)):
        return jsonify(error="invalid_request", **getattr(error, "detail", {})), 400
    return jsonify(error="internal_error"), 500


def body():
    result = request.get_json(silent=True)
    if not isinstance(result, dict):
        raise ValueError("invalid request")
    return result


@blueprint.get("/status")
def status():
    service = get_service()
    return jsonify(settings=service.store.settings(), roster=service.store.configured_bees(),
                   providers=sorted(service.adapters))


@blueprint.get("/catalog")
def catalog():
    service = get_service()
    return jsonify({name: asdict(adapter.discover()) for name, adapter in service.adapters.items()})


@blueprint.route("/settings", methods=["POST"])
def settings():
    data = body()
    service = get_service()
    if data.get("kind") == "worker_limit":
        result = service.store.set_worker_limit(data["value"], data["key"], data["revision"])
    elif data.get("kind") == "roster":
        result = service.store.set_configured_bees(data["bees"], data["key"], data["revision"])
    else:
        raise ValueError("invalid setting")
    return jsonify(result)


@blueprint.post("/presence")
def presence():
    data = body()
    service = get_service()
    if data.get("present") is True:
        service.heartbeat(data["hud"])
    elif data.get("present") is False:
        service.bye(data["hud"])
    else:
        raise ValueError("invalid presence")
    return jsonify(ok=True)


@blueprint.get("/missions")
def list_missions():
    return jsonify(get_service().store.list_missions())


@blueprint.post("/missions")
def create_mission():
    data = body()
    mission_id = data.get("id") or uuid.uuid4().hex
    if not isinstance(mission_id, str) or not mission_id.isalnum() or len(mission_id) > 64:
        raise ValueError("invalid id")
    return jsonify(get_service().missions.create(mission_id, data["key"], data["title"], data.get("cycle_limit", 3)))


@blueprint.get("/missions/<mission_id>")
def mission(mission_id):
    service = get_service()
    cursor = request.args.get("after", "0")
    if not cursor.isdecimal():
        raise ValueError("invalid cursor")
    return jsonify(mission=service.store.get(mission_id), events=service.store.events(mission_id, int(cursor)),
                   roster=service.store.roster(mission_id), jobs=service.store.jobs(mission_id),
                   bees_summary=service.bees_summary(mission_id))


@blueprint.post("/missions/<mission_id>/lease")
def lease(mission_id):
    data = body()
    return jsonify(get_service().lifecycle.acquire_control(mission_id, data["owner"]))


@blueprint.post("/missions/<mission_id>/command")
def command(mission_id):
    data = body()
    service = get_service()
    action, key, revision, owner = data["action"], data["key"], data["revision"], data["owner"]
    def execute():
        if action == "ask":
            return service.ask_queen(mission_id, key, revision, data["source"], data["queen"], data["message"])
        if action == "propose":
            return service.missions.propose(mission_id, key, revision, data["plan"])
        if action == "approve_plan":
            return service.missions.approve_plan(mission_id, key, revision, data["plan_hash"])
        if action == "start":
            return service.start_mission(mission_id, key, revision)
        if action == "pause":
            result = service.lifecycle.request_pause(mission_id, key, revision, "user")
            service.lifecycle.progress(mission_id)
            return result
        if action == "resume":
            return service.resume(mission_id, key, revision)
        if action == "cycle_limit":
            return service.missions.set_cycle_limit(mission_id, key, revision, data["limit"])
        if action == "approve_delivery":
            return service.missions.approve_delivery(mission_id, key, revision, data["candidate_hash"], data["delivery_hash"])
        if action == "apply":
            return service.delivery.apply(mission_id, key, revision, data["delivery_hash"])
        if action == "recover_delivery":
            return service.delivery.recover(mission_id, key, revision)
        if action == "reconcile_source":
            return service.reconcile_source(mission_id, key, revision)
        if action == "abandon":
            return service.missions.abandon(mission_id, key, revision, service.delivery.journal_root)
        raise ValueError("invalid action")
    return jsonify(service.lifecycle.controlled(mission_id, owner, execute))
