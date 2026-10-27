"""Claude Code CLI installation and subscription discovery, without inference."""

from dataclasses import replace
import json
import re
import subprocess
import queue
import threading
import time
import uuid
from pathlib import Path

from .base import Discovery, DiscoveryError, DiscoveryRpc, Model, discovery_environment, run_status, safe_name


def turn_error_code(result):
    """Expose only a closed category of a failed stream-json result, never its message."""
    if not isinstance(result, dict):
        return "unknown"
    subtype = result.get("subtype")
    if isinstance(subtype, str) and subtype in {"error_max_turns", "error_during_execution",
                                                 "error_max_budget_usd", "error_max_structured_output_retries"}:
        return subtype
    status = result.get("api_error_status")
    if type(status) is int and 100 <= status <= 599:
        return "api_error_" + str(status)
    return "unknown"


# Oldest release whose model-only session was proven; newer releases must still expose
# every isolation flag (checked without inference, once per installed version).
_MIN_VERSION = (2, 1, 289)
# Aliases that always resolve to the newest model of each family; others stay hidden.
_MODELS = ("opus", "sonnet", "haiku")
_flag_proofs = {}


def flags_supported(command, version, timeout):
    """True only when the installed help lists every flag the model-only session needs."""
    if version not in _flag_proofs:
        try:
            text = run_status(command, ["--help"], timeout)
        except DiscoveryError:
            return False
        flags = [arg for arg in model_only_arguments() if arg.startswith("--")] + ["--model", "--effort"]
        _flag_proofs[version] = all(re.search(r"(?m)(^|[\s,])" + re.escape(flag) + r"([\s,=]|$)", text)
                                    for flag in flags)
    return _flag_proofs[version]


def model_only_arguments():
    """Build the tested no-native-tools candidate, without starting a prompt."""
    return ["--print", "--safe-mode", "--input-format", "stream-json", "--output-format", "stream-json",
            "--verbose", "--tools", "", "--strict-mcp-config", "--mcp-config",
            '{"mcpServers":{}}', "--setting-sources", "", "--no-chrome",
            "--disable-slash-commands", "--no-session-persistence"]


def model_only_environment():
    env = discovery_environment()
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    return env


def read_controls(command, timeout):
    requests = [
        {"type": "control_request", "request_id": name, "request": request}
        for name, request in (
            ("hivemind-init", {"subtype": "initialize"}),
            ("hivemind-settings", {"subtype": "get_settings"}),
            ("hivemind-usage", {"subtype": "get_usage", "skip_behaviors": True}),
        )
    ]
    try:
        result = subprocess.run([*command, *model_only_arguments()],
                                input="".join(json.dumps(request) + "\n" for request in requests), capture_output=True,
                                text=True, encoding="utf-8", errors="replace",
                                timeout=timeout, env=model_only_environment(), check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiscoveryError("process_unavailable") from exc
    if result.returncode != 0:
        raise DiscoveryError("command_failed")
    try:
        messages = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        replies = {}
        for item in messages:
            response = item.get("response") if isinstance(item, dict) and item.get("type") == "control_response" else None
            if isinstance(response, dict) and response.get("request_id") in {r["request_id"] for r in requests}:
                if response["request_id"] in replies or response.get("subtype") != "success":
                    raise DiscoveryError("control_invalid")
                replies[response["request_id"]] = response.get("response")
        if set(replies) != {r["request_id"] for r in requests}:
            raise DiscoveryError("control_invalid")
        return _parse_controls(replies)
    except (TypeError, ValueError) as exc:
        raise DiscoveryError("catalog_invalid") from exc


def _parse_controls(replies):
    try:
        data = replies["hivemind-init"]
        entries = data.get("models") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            raise DiscoveryError("catalog_invalid")
        models = []
        for item in entries:
            if not isinstance(item, dict) or item.get("value") not in _MODELS:
                continue
            efforts = item.get("supportedEffortLevels")
            if efforts is None:
                efforts = []
            if not isinstance(efforts, list) or any(safe_name(level) is None for level in efforts):
                raise DiscoveryError("catalog_invalid")
            models.append(Model(item["value"], tuple(efforts)))
        settings = replies["hivemind-settings"]
        effective = settings.get("effective") if isinstance(settings, dict) else None
        policy_clear = (not any(effective.get(key) for key in ("hooks", "statusLine", "fileSuggestion", "fallbackModel"))
                        if isinstance(effective, dict) else None)
        usage = replies["hivemind-usage"]
        if not isinstance(usage, dict) or "behaviors" not in usage or usage["behaviors"] is not None:
            raise DiscoveryError("usage_invalid")
        limits = usage.get("rate_limits")
        ordinary = None
        extra = None
        if (usage.get("rate_limits_available") is True
                and usage.get("subscription_type") in {"pro", "max", "team", "enterprise"}
                and isinstance(limits, dict)):
            windows = [limits.get(key) for key in ("five_hour", "seven_day")]
            values = [window.get("utilization") if isinstance(window, dict) else None for window in windows]
            if all(isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100
                   for value in values):
                ordinary = all(value < 100 for value in values)
            extra_data = limits.get("extra_usage")
            if isinstance(extra_data, dict) and isinstance(extra_data.get("is_enabled"), bool):
                extra = extra_data["is_enabled"]
        return tuple(models), ordinary, extra, policy_clear
    except (TypeError, ValueError) as exc:
        raise DiscoveryError("catalog_invalid") from exc


class ClaudeAdapter:
    def __init__(self, command, timeout=20, session_command=None):
        self.command = tuple(command)
        self.session_command = tuple(session_command or command)
        self.timeout = timeout

    def discover(self):
        result = Discovery(provider="claude")
        try:
            output = run_status(self.command, ["--version"], self.timeout).strip()
            result = replace(result, installed=True)
            match = re.fullmatch(r"(\d+\.\d+\.\d+) \(Claude Code\)", output)
            if not match:
                return replace(result, errors=("version_unrecognized",))
            version = match.group(1)
            result = replace(result, installed=True, version=version,
                             compatible=tuple(map(int, version.split("."))) >= _MIN_VERSION
                             and flags_supported(self.command, version, self.timeout))
            raw = run_status(self.command, ["auth", "status", "--json"], self.timeout)
            try:
                status = json.loads(raw)
            except (ValueError, TypeError) as exc:
                raise DiscoveryError("status_invalid") from exc
            if not isinstance(status, dict):
                raise DiscoveryError("status_invalid")
            method = status.get("authMethod")
            kind = method if method in {"claude.ai", "apiKey"} else None
            result = replace(result, account_kind=kind,
                             authenticated=status.get("loggedIn") is True
                             and method == "claude.ai"
                             and status.get("apiProvider") == "firstParty")
            models, ordinary, extra, policy_clear = read_controls(self.command, self.timeout)
            result = replace(result, models=models, ordinary_usage_allowed=ordinary,
                             extra_usage_enabled=extra, policy_customizations_absent=policy_clear)
        except DiscoveryError as exc:
            result = replace(result, errors=result.errors + (str(exc),))
        return result


class _ControlRpc(DiscoveryRpc):
    """Streaming control protocol bound to one CLI process, with no prompt."""

    def __init__(self, command, timeout, model, effort, workspace):
        super().__init__(command, timeout)
        self.model, self.effort, self.workspace = model, effort, workspace

    def __enter__(self):
        try:
            self.process = subprocess.Popen([*self.command, *model_only_arguments(), "--model", self.model, "--effort", self.effort],
                cwd=self.workspace, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace", env=model_only_environment())
        except OSError as exc:
            raise DiscoveryError("process_unavailable") from exc
        self._track()
        return self

    def controls(self):
        replies = {}
        requests = [("hivemind-settings", {"subtype": "get_settings"}),
                    ("hivemind-usage", {"subtype": "get_usage", "skip_behaviors": True})]
        if not hasattr(self, "_initialized"):
            requests.insert(0, ("hivemind-init", {"subtype": "initialize"}))
        else:
            replies["hivemind-init"] = self._initialized
        for name, request in requests:
            self._send({"type": "control_request", "request_id": name, "request": request})
            deadline = time.monotonic() + self.timeout
            while True:
                try:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise queue.Empty
                    item = self.messages.get(timeout=remaining)
                except queue.Empty as exc:
                    raise DiscoveryError("protocol_timeout") from exc
                if item.get("invalid") or item.get("closed"):
                    raise DiscoveryError("protocol_invalid_or_closed")
                response = item.get("response") if item.get("type") == "control_response" else None
                if isinstance(response, dict) and response.get("request_id") == name:
                    if response.get("subtype") != "success":
                        raise DiscoveryError("control_invalid")
                    replies[name] = response.get("response")
                    break
        self._initialized = replies["hivemind-init"]
        return _parse_controls(replies)


class ClaudeProofSession:
    """Keep the authenticated model-only process and its controls together."""

    def __init__(self, adapter, model, effort, workspace, broker):
        from ..capabilities import ToolBroker
        if (type(broker) is not ToolBroker or not safe_name(model) or not safe_name(effort)
                or not Path(workspace).is_absolute()):
            raise ValueError("invalid model, effort or broker")
        self.adapter, self.model, self.effort, self.broker = adapter, model, effort, broker
        self.rpc = _ControlRpc(adapter.session_command, adapter.timeout, model, effort, str(workspace))
        self.initial = self.version = None
        self._turn_lock = threading.Lock()
        self._turn_active = False
        self._pause_pending = False

    def __enter__(self):
        # Evidence binds to the version running now; an update mid-session invalidates it.
        self.version = self.adapter.discover().version
        self.rpc.__enter__()
        try:
            self.initial = self.rpc.controls()
            if not self._valid_controls(self.initial):
                raise DiscoveryError("session_controls_unverified")
            return self
        except Exception:
            self.rpc.close()
            raise

    def _valid_controls(self, controls):
        models, ordinary, extra, policy_clear = controls
        return (ordinary is True and extra is False and policy_clear is True
                and any(m.name == self.model and self.effort in m.efforts for m in models))

    def _validate(self):
        if (self.rpc.process is None or self.rpc.process.poll() is not None
                or not self.broker.admission.accepting()):
            return False
        from ..capabilities import evaluate
        discovery = self.adapter.discover()
        current = evaluate(discovery, self.model, self.effort)
        return (current.reasons == ("enforcement_evidence_unverified",)
                and self._valid_controls(self.rpc.controls()))

    def evidence(self):
        from ..capabilities import _issue_evidence
        return _issue_evidence("claude", self.version, self.model, self.effort, self._validate)

    def interrupt(self):
        if not self.broker.admission.drained():
            raise DiscoveryError("tool_not_drained")
        with self._turn_lock:
            self._pause_pending = True
            if self._turn_active:
                self.rpc._send({"type": "control_request", "request_id": "interrupt-" + uuid.uuid4().hex,
                                "request": {"subtype": "interrupt"}})

    def turn(self, prompt, output_schema=None):
        """Model-only JSON conversation with an explicitly bounded broker loop.

        The outer envelope is this adapter's own protocol, so output_schema only
        describes the JSON text expected inside the final field.
        """
        from ..capabilities import PauseRequested, ToolNotAllowed, evaluate
        if not isinstance(prompt, str) or not prompt or len(prompt) > 100000:
            raise ValueError("invalid prompt")
        if output_schema is not None and not isinstance(output_schema, dict):
            raise ValueError("invalid output schema")
        usage = {"read": "read takes path and returns content and sha256",
                 "patch": "patch takes path, content (null removes) and expected_sha256 (null only for a new file)",
                 "checks": "checks takes argv", "progress": "progress takes done, total and note"}
        message = (prompt + '\nReturn one JSON object: {"final": <text>} when finished, or {"action": '
                   + "|".join('"' + name + '"' for name in self.broker.names) + ', "arguments": {...}} to request the broker. '
                   + "; ".join(usage[name] for name in self.broker.names) + ". No other tools are available.")
        if output_schema is not None:
            message += (' The final text must be valid JSON matching this JSON Schema: '
                        + json.dumps(output_schema, separators=(",", ":")))
        for _ in range(100):
            discovery = self.adapter.discover()
            gate = evaluate(discovery, self.model, self.effort, self.evidence())
            if not gate.execution_allowed:
                raise DiscoveryError("gate:" + gate.reasons[0])
            with self._turn_lock:
                if self._pause_pending or self._turn_active or not self.broker.admission.accepting():
                    raise DiscoveryError("turn_not_available")
                self._turn_active = True
                self.rpc._send({"type": "user", "message": {"role": "user", "content": message},
                                "parent_tool_use_id": None, "session_id": ""})
            while True:
                item = self.rpc.messages.get()
                if item.get("invalid") or item.get("closed"):
                    raise DiscoveryError("protocol_invalid_or_closed")
                if item.get("type") == "assistant":
                    content = item.get("message", {}).get("content", [])
                    if item.get("parent_tool_use_id") is not None or any(
                            isinstance(part, dict) and part.get("type") == "tool_use" for part in content):
                        raise DiscoveryError("native_tool_unexpected")
                if item.get("type") != "result":
                    continue
                with self._turn_lock:
                    self._turn_active = False
                if item.get("is_error") is True or item.get("subtype") != "success":
                    raise DiscoveryError("turn_failed:claude:" + turn_error_code(item))
                text = item.get("result")
                try:
                    response = json.loads(text)
                except (TypeError, ValueError) as exc:
                    raise DiscoveryError("turn_result_invalid") from exc
                break
            if not isinstance(response, dict):
                raise DiscoveryError("turn_result_invalid")
            if set(response) == {"final"} and isinstance(response["final"], str):
                return response["final"]
            if set(response) != {"action", "arguments"}:
                raise DiscoveryError("turn_result_invalid")
            replies = []
            try:
                self.broker.dispatch_and_reply(response["action"], response["arguments"],
                                               lambda ok, value: replies.append({"success": ok, "result": value}))
            except (PauseRequested, ToolNotAllowed, ValueError):
                raise DiscoveryError("tool_not_available")
            message = "Broker result: " + json.dumps(replies[0], ensure_ascii=False) + "\nReturn the next JSON object."
        raise DiscoveryError("tool_limit_reached")

    def __exit__(self, exc_type, exc, traceback):
        self.rpc.close()
