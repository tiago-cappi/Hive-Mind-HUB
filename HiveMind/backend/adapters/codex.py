"""Codex CLI account and catalog discovery, without starting a turn."""

from dataclasses import dataclass, field, replace
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import uuid

from .base import Discovery, DiscoveryError, DiscoveryRpc, Model, run_status, safe_name


@dataclass(frozen=True)
class SecurityInventory:
    mcp_names: tuple[str, ...] = field(repr=False)
    fingerprint: str
    reasons: tuple[str, ...]


def security_inventory(config, codex_home):
    """Reduce a config response to the few facts needed for a fail-closed check."""
    if not isinstance(config, dict) or not isinstance(config.get("mcp_servers"), dict):
        raise DiscoveryError("security_config_invalid")
    names = config["mcp_servers"].keys()
    if any(safe_name(name) is None for name in names):
        raise DiscoveryError("mcp_name_invalid")
    names = tuple(sorted(names))
    reasons = []
    home = Path(codex_home)
    try:
        for name in ("AGENTS.md", "AGENTS.override.md"):
            try:
                (home / name).lstat()
            except FileNotFoundError:
                continue
            reasons.append("global_instructions_present")
            break
    except OSError as exc:
        raise DiscoveryError("global_instructions_unknown") from exc
    if any(config.get(key) is not None for key in
           ("instructions", "developer_instructions", "model_instructions_file", "compact_prompt")):
        reasons.append("custom_instructions_present")
    if (config.get("model_catalog_json") is not None or config.get("openai_base_url") is not None
            or config.get("chatgpt_base_url") not in (None, "https://chatgpt.com/backend-api/")):
        reasons.append("custom_provider_configuration")
    digest = hashlib.sha256(json.dumps([names, reasons], separators=(",", ":")).encode()).hexdigest()
    return SecurityInventory(names, digest, tuple(reasons))


def disabled_mcp_roster(items, expected_names):
    """Check an already-paginated thread roster; unknown states fail closed."""
    if not isinstance(items, list):
        return False
    found = []
    for item in items:
        if not isinstance(item, dict) or item.get("runtimeStatus") != "disabled":
            return False
        found.append(item.get("name"))
    return len(found) == len(expected_names) and set(found) == set(expected_names)


def session_params(model, workspace, mcp_server_names, tool_names=("read", "patch", "checks", "progress")):
    """Build the P0 candidate request; starting turns remains disabled.

    The caller must discover every configured MCP server and verify the
    effective configuration and thread roster before use.
    """
    if not safe_name(model) or not isinstance(workspace, str) or not Path(workspace).is_absolute():
        raise ValueError("invalid model or workspace")
    if not isinstance(mcp_server_names, (list, tuple)) or any(
        not isinstance(name, str) or not name for name in mcp_server_names
    ):
        raise ValueError("invalid MCP server names")
    schemas = {
        "read": {"path": {"type": "string"}},
        "patch": {"path": {"type": "string"}, "content": {"type": ["string", "null"]},
                  "expected_sha256": {"type": ["string", "null"]}},
        "checks": {"argv": {"type": "array", "items": {"type": "string"}}},
        "progress": {"done": {"type": "integer"}, "total": {"type": "integer"}, "note": {"type": "string"}},
    }
    tools = [{"type": "function", "name": name, "description": "HiveMind broker operation: " + name,
              "inputSchema": {"type": "object", "properties": fields,
                              "required": list(fields), "additionalProperties": False}}
             for name, fields in schemas.items() if name in tool_names]
    return {
        "model": model,
        "modelProvider": "openai",
        "serviceTier": "default",
        "cwd": workspace,
        "runtimeWorkspaceRoots": [workspace],
        # Built-in profile: Codex 0.160.0 fails every turn of a thread started with a
        # custom profile ("failed to load workspace requirements"). Writes never go
        # through Codex; the broker owns read/patch/checks and native tools are refused.
        "permissions": ":read-only",
        "approvalPolicy": "never",
        "allowProviderModelFallback": False,
        "ephemeral": True,
        "environments": [],
        "dynamicTools": tools,
        "config": {
            "agents": {"enabled": False},
            "features": {"multi_agent_v2": False, "multi_agent": False,
                         "plugins": False, "apps": False, "shell_tool": False,
                         "memories": False, "hooks": False, "code_mode": False,
                         "deferred_executor": False, "prefer_mxc": True},
            "windows": {"sandbox": "unelevated"},
            "mcp_servers": {name: {"enabled": False} for name in mcp_server_names},
            "memories": {"use_memories": False, "generate_memories": False},
            "skills": {"include_instructions": False},
            "project_doc_max_bytes": 0,
            "web_search": "disabled",
        },
    }


# Closed list of thread items a model-only turn may produce; any native tool fails closed.
_TURN_ITEM_TYPES = frozenset({"userMessage", "agentMessage", "reasoning", "plan",
                              "dynamicToolCall", "functionCallOutput", "contextCompaction"})


def turn_error_code(error):
    """Expose only schema-defined error categories, never provider messages or details."""
    if not isinstance(error, dict):
        return "unknown"
    info = error.get("codexErrorInfo")
    allowed = {"contextWindowExceeded", "sessionBudgetExceeded", "usageLimitExceeded", "rateLimitExceeded",
               "flexUnavailable", "serverOverloaded", "cyberPolicy", "misalignmentPolicyViolation",
               "tooManyDenials", "internalServerError", "unauthorized", "badRequest", "threadRollbackFailed",
               "sandboxError", "other"}
    if isinstance(info, str) and info in allowed:
        return info
    network = {"httpConnectionFailed", "responseStreamConnectionFailed", "responseStreamDisconnected",
               "responseTooManyFailedAttempts"}
    if isinstance(info, dict) and len(info) == 1:
        name, details = next(iter(info.items()))
        if name in network and isinstance(details, dict):
            status = details.get("httpStatusCode")
            return name + (":" + str(status) if type(status) is int and 100 <= status <= 599 else "")
    return "unknown"


class CodexAdapter:
    def __init__(self, command, timeout=20, session_command=None):
        self.command = tuple(command)
        self.session_command = tuple(session_command or command)
        self.timeout = timeout

    def discover(self):
        result = Discovery(provider="codex")
        try:
            version_output = run_status(self.command, ["--version"], self.timeout).strip()
            result = replace(result, installed=True)
            match = re.fullmatch(r"codex-cli (\d+\.\d+\.\d+)", version_output)
            if not match:
                return replace(result, errors=("version_unrecognized",))
            version = match.group(1)
            result = replace(result, installed=True, version=version,
                             compatible=version == "0.160.0")
            with DiscoveryRpc(self.command, self.timeout) as rpc:
                account = rpc.request("account/read", {"refreshToken": False}).get("account")
                kind = account.get("type") if isinstance(account, dict) else None
                result = replace(result, account_kind=kind if kind in {"chatgpt", "apiKey", "amazonBedrock"} else None,
                                 authenticated=kind == "chatgpt")
                models = []
                cursor = None
                seen = set()
                for _ in range(100):
                    page = rpc.request("model/list", {"limit": 100, "cursor": cursor, "includeHidden": False})
                    entries = page.get("data")
                    if not isinstance(entries, list):
                        raise DiscoveryError("catalog_invalid")
                    for item in entries:
                        if not isinstance(item, dict) or not safe_name(item.get("model")):
                            raise DiscoveryError("catalog_invalid")
                        efforts = item.get("supportedReasoningEfforts")
                        if not isinstance(efforts, list):
                            raise DiscoveryError("catalog_invalid")
                        names = [safe_name(entry.get("reasoningEffort")) if isinstance(entry, dict) else None
                                 for entry in efforts]
                        if any(name is None for name in names):
                            raise DiscoveryError("catalog_invalid")
                        models.append(Model(item["model"], tuple(names)))
                    cursor = page.get("nextCursor")
                    if cursor is None:
                        break
                    if not isinstance(cursor, str) or cursor in seen:
                        raise DiscoveryError("catalog_pagination_invalid")
                    seen.add(cursor)
                else:
                    raise DiscoveryError("catalog_pagination_limit")
                result = replace(result, models=tuple(models))
                limits = rpc.request("account/rateLimits/read", None)
                ordinary = limits.get("ordinaryUsageAllowed")
                ordinary = ordinary if isinstance(ordinary, bool) else None
                bucket = limits.get("rateLimits")
                credits = bucket.get("credits") if isinstance(bucket, dict) else None
                has_credits = credits.get("hasCredits") if isinstance(credits, dict) else None
                has_credits = has_credits if isinstance(has_credits, bool) else None
                result = replace(result, ordinary_usage_allowed=ordinary, has_credits=has_credits)
        except DiscoveryError as exc:
            result = replace(result, errors=result.errors + (str(exc),))
        return result

    def security_inventory(self, workspace, codex_home):
        with DiscoveryRpc(self.command, self.timeout) as rpc:
            response = rpc.request("config/read", {"cwd": str(workspace), "includeLayers": False})
        return security_inventory(response.get("config"), codex_home)


class _SessionRpc(DiscoveryRpc):
    _METHODS = DiscoveryRpc._METHODS | {"thread/start", "mcpServerStatus/list"}


class CodexProofSession:
    """Own a no-turn session; proof expires with it or changed controls.

    P3 must retain this exact session and run this gate before every turn.
    This class deliberately exposes no turn-start operation in P0.
    """

    def __init__(self, adapter, model, effort, workspace, broker):
        from ..capabilities import ToolBroker
        if type(broker) is not ToolBroker or not safe_name(effort):
            raise ValueError("invalid broker or effort")
        self.adapter, self.model, self.effort = adapter, model, effort
        self.workspace, self.broker = str(workspace), broker
        self.codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").resolve()
        self.rpc = _SessionRpc(adapter.session_command, adapter.timeout, experimental=True)
        self.inventory = self.thread_id = None
        self._turn_lock = threading.Lock()
        self._turn_id = None
        self._pause_pending = False
        self._turn_starting = False

    def __enter__(self):
        self.rpc.__enter__()
        try:
            self.inventory = self._inventory()
            if self.inventory.reasons:
                raise DiscoveryError("context_unverified")
            params = session_params(self.model, self.workspace, self.inventory.mcp_names, self.broker.names)
            response = self.rpc.request("thread/start", params)
            thread = response.get("thread")
            checks = {
                "thread": isinstance(thread, dict) and isinstance(thread.get("id"), str) and bool(thread["id"]),
                "instructions": response.get("instructionSources") == [],
                "environments": isinstance(thread, dict) and thread.get("environments") == [],
                "ephemeral": isinstance(thread, dict) and thread.get("ephemeral") is True,
                "model": response.get("model") == self.model,
                "provider": response.get("modelProvider") == "openai",
                "approval": response.get("approvalPolicy") == "never",
                "profile": isinstance(response.get("activePermissionProfile"), dict)
                    and response["activePermissionProfile"].get("id") == ":read-only",
                "roots": isinstance(response.get("runtimeWorkspaceRoots"), list)
                    and len(response["runtimeWorkspaceRoots"]) <= 1
                    and all(isinstance(root, str) and Path(root) == Path(self.workspace)
                            for root in response["runtimeWorkspaceRoots"]),
                "cwd": Path(response.get("cwd", "")) == Path(self.workspace),
            }
            failed = tuple(name for name, valid in checks.items() if not valid)
            if failed:
                roots = response.get("runtimeWorkspaceRoots")
                root_shape = ("missing" if roots is None else "count_" + str(len(roots))
                              if isinstance(roots, list) else "invalid")
                raise DiscoveryError("thread_controls_unverified:" + ",".join(failed) + ":roots_" + root_shape)
            self.thread_id = thread["id"]
            if not self._validate():
                raise DiscoveryError("session_controls_unverified")
            return self
        except Exception:
            self.rpc.close()
            raise

    def _inventory(self):
        response = self.rpc.request("config/read", {"cwd": self.workspace, "includeLayers": False})
        return security_inventory(response.get("config"), self.codex_home)

    def _roster(self):
        items = []
        for name in self.inventory.mcp_names:
            cursor, seen = None, set()
            for _ in range(100):
                page = self.rpc.request("mcpServerStatus/list", {
                    "threadId": self.thread_id, "serverName": name, "cursor": cursor, "limit": 100})
                if not isinstance(page.get("data"), list):
                    raise DiscoveryError("mcp_roster_invalid")
                items.extend(page["data"])
                cursor = page.get("nextCursor")
                if cursor is None:
                    break
                if not isinstance(cursor, str) or cursor in seen:
                    raise DiscoveryError("mcp_roster_invalid")
                seen.add(cursor)
            else:
                raise DiscoveryError("mcp_roster_invalid")
        return disabled_mcp_roster(items, self.inventory.mcp_names)

    def _validate(self):
        if (self.rpc.process is None or self.rpc.process.poll() is not None or self.thread_id is None
                or not self.broker.admission.accepting()):
            return False
        from ..capabilities import evaluate
        discovery = self.adapter.discover()
        gate = evaluate(discovery, self.model, self.effort)
        current_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").resolve()
        current = self._inventory()
        return (current_home == self.codex_home and gate.reasons == ("enforcement_evidence_unverified",)
                and current == self.inventory and not current.reasons and self._roster())

    def evidence(self):
        from ..capabilities import _issue_evidence
        return _issue_evidence("codex", "0.160.0", self.model, self.effort, self._validate)

    def interrupt(self):
        """Request interruption only after the broker admission has drained."""
        if not self.broker.admission.drained():
            raise DiscoveryError("tool_not_drained")
        with self._turn_lock:
            self._pause_pending = True
            if self._turn_id:
                self.rpc._send({"jsonrpc": "2.0", "id": "interrupt-" + uuid.uuid4().hex,
                                "method": "turn/interrupt",
                                "params": {"threadId": self.thread_id, "turnId": self._turn_id}})

    def turn(self, prompt, output_schema=None):
        """Execute one gated turn; the caller owns scheduling and persistence.

        output_schema, when given, constrains the final message to that JSON Schema.
        """
        from ..capabilities import PauseRequested, ToolNotAllowed, evaluate
        if not isinstance(prompt, str) or not prompt or len(prompt) > 100000:
            raise ValueError("invalid prompt")
        if output_schema is not None and not isinstance(output_schema, dict):
            raise ValueError("invalid output schema")
        discovery = self.adapter.discover()
        gate = evaluate(discovery, self.model, self.effort, self.evidence())
        if not gate.execution_allowed:
            raise DiscoveryError("gate:" + gate.reasons[0])
        with self._turn_lock:
            if self._turn_id is not None or self._turn_starting or self._pause_pending or not self.broker.admission.accepting():
                raise DiscoveryError("turn_not_available")
            self._turn_starting = True
            self.rpc.next_id += 1
            request_id = self.rpc.next_id
            params = {"threadId": self.thread_id, "input": [{"type": "text", "text": prompt}],
                      "model": self.model, "effort": self.effort, "serviceTierForTurn": "default"}
            if output_schema is not None:
                params["outputSchema"] = output_schema
            self.rpc._send({"jsonrpc": "2.0", "id": request_id, "method": "turn/start", "params": params})
        output = []
        calls = 0
        awaiting_start = True
        while True:
            item = self.rpc.messages.get()
            if item.get("invalid") or item.get("closed"):
                raise DiscoveryError("protocol_invalid_or_closed")
            if awaiting_start and "method" not in item and item.get("id") == request_id:
                turn = item.get("result", {}).get("turn") if isinstance(item.get("result"), dict) else None
                turn_id = turn.get("id") if isinstance(turn, dict) else None
                if not isinstance(turn_id, str) or not turn_id:
                    raise DiscoveryError("turn_start_failed")
                awaiting_start = False
                with self._turn_lock:
                    self._turn_starting = False
                    self._turn_id = turn_id
                    if self._pause_pending:
                        self.rpc._send({"jsonrpc": "2.0", "id": "interrupt-" + uuid.uuid4().hex,
                                        "method": "turn/interrupt",
                                        "params": {"threadId": self.thread_id, "turnId": turn_id}})
                continue
            method, params = item.get("method"), item.get("params")
            if method == "item/tool/call" and "id" in item:
                def reply(success, result):
                    self.rpc._send({"jsonrpc": "2.0", "id": item["id"], "result": {
                        "contentItems": [{"type": "inputText", "text": json.dumps(result, ensure_ascii=False)}],
                        "success": success}})
                if (awaiting_start or not isinstance(params, dict) or params.get("threadId") != self.thread_id
                        or params.get("turnId") != self._turn_id or calls >= 100):
                    reply(False, {"error": "tool_request_invalid"})
                    continue
                calls += 1
                try:
                    self.broker.dispatch_and_reply(params.get("tool"), params.get("arguments"), reply)
                except (PauseRequested, ToolNotAllowed, ValueError):
                    reply(False, {"error": "tool_not_available"})
                continue
            if "id" in item and method:
                self.rpc._send({"jsonrpc": "2.0", "id": item["id"],
                                "error": {"code": -32601, "message": "unsupported"}})
                continue
            if (method in {"item/started", "item/completed"} and isinstance(params, dict)
                    and params.get("threadId") == self.thread_id and isinstance(params.get("item"), dict)
                    and params["item"].get("type") not in _TURN_ITEM_TYPES):
                raise DiscoveryError("native_tool_unexpected")
            if (method == "item/completed" and isinstance(params, dict) and
                    params.get("threadId") == self.thread_id and params.get("turnId") == self._turn_id):
                content = params.get("item")
                if isinstance(content, dict) and content.get("type") == "agentMessage" and isinstance(content.get("text"), str):
                    output.append((content.get("phase"), content["text"]))
            if method == "turn/completed" and isinstance(params, dict) and params.get("threadId") == self.thread_id:
                turn = params.get("turn")
                if not isinstance(turn, dict) or turn.get("id") != self._turn_id:
                    raise DiscoveryError("turn_result_invalid")
                status = turn.get("status")
                with self._turn_lock:
                    self._turn_id = None
                if status != "completed":
                    category = status if status in {"failed", "interrupted"} else "invalid"
                    suffix = ":" + turn_error_code(turn.get("error")) if category == "failed" else ""
                    raise DiscoveryError("turn_" + category + suffix)
                # Commentary before tool calls is not the answer; keep the final one when marked.
                final = [text for phase, text in output if phase == "final_answer"]
                return "\n".join(final or [text for phase, text in output if phase != "commentary"])

    def __exit__(self, exc_type, exc, traceback):
        self.rpc.close()
