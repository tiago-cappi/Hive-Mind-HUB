"""Finite fake CLI for exercising discovery without real accounts or models."""

import json
import os
from pathlib import Path
import sys


provider, *args = sys.argv[1:]
log = os.environ.get("HIVEMIND_FIXTURE_LOG")


def record(value):
    if log:
        with Path(log).open("a", encoding="utf-8") as output:
            output.write(json.dumps(value) + "\n")


if args == ["--version"]:
    print("codex-cli 0.160.0" if provider == "codex" else "2.1.289 (Claude Code)")
elif provider == "claude" and args == ["--help"]:
    print("  --print --safe-mode --input-format --output-format --verbose --tools <tools...>")
    print("  --strict-mcp-config --mcp-config --setting-sources --no-chrome --disable-slash-commands")
    print("  --no-session-persistence --model <model> --effort <level>")
elif provider == "claude" and args == ["auth", "status", "--json"]:
    record({"api_key_present": bool(os.environ.get("ANTHROPIC_API_KEY"))})
    print(json.dumps({"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty",
                      "email": "private-fixture@example.invalid"}))
elif provider == "claude" and "--print" in args:
    for line in sys.stdin:
        request = json.loads(line)
        control = request.get("request", {})
        record({"claude_request_type": request.get("type"), "request": control})
        if control.get("subtype") == "initialize":
            data = {"account": {"email": "private-fixture@example.invalid"},
                    "models": [{"value": "sonnet", "supportedEffortLevels": ["medium", "high"]},
                               {"value": "fable", "supportedEffortLevels": ["high"]}]}
        elif control.get("subtype") == "get_settings":
            data = {"effective": {}}
        elif control.get("subtype") == "get_usage":
            data = {"behaviors": None, "subscription_type": "team", "rate_limits_available": True,
                    "rate_limits": {"five_hour": {"utilization": 10}, "seven_day": {"utilization": 20},
                                    "extra_usage": {"is_enabled": False}}}
        else:
            sys.exit(3)
        print(json.dumps({"type": "control_response", "response": {"subtype": "success",
            "request_id": request["request_id"], "response": data}}), flush=True)
elif provider == "codex" and args == ["app-server", "--stdio"]:
    record({"api_key_present": bool(os.environ.get("OPENAI_API_KEY"))})
    thread_params = None
    for line in sys.stdin:
        request = json.loads(line)
        record(request)
        method = request.get("method")
        if method == "initialized":
            continue
        if os.environ.get("HIVEMIND_FIXTURE_SERVER_REQUEST") and method == "account/read":
            print(json.dumps({"id": "server", "method": "unexpected", "params": {}}), flush=True)
            continue
        if method == "initialize":
            result = {"userAgent": "fixture"}
        elif method == "account/read":
            result = {"account": {"type": "chatgpt", "email": "private-fixture@example.invalid"}}
        elif method == "model/list":
            if request["params"].get("cursor") is None:
                result = {"data": [{"model": "fixture-model", "supportedReasoningEfforts": [
                    {"reasoningEffort": "high"}]}], "nextCursor": "next"}
            else:
                result = {"data": [{"model": "fixture-other", "supportedReasoningEfforts": [
                    {"reasoningEffort": "low"}]}], "nextCursor": None}
        elif method == "account/rateLimits/read":
            result = {"ordinaryUsageAllowed": True, "rateLimits": {"credits": {"hasCredits": False}}}
        elif method == "config/read":
            names = {"fixture": {"headers": {"secret": "private-fixture"}}}
            marker = os.environ.get("HIVEMIND_FIXTURE_CHANGED")
            if marker and Path(marker).exists():
                names["later"] = {}
            result = {"config": {"mcp_servers": names}}
        elif method == "thread/start":
            thread_params = request["params"]
            result = {"thread": {"id": "fixture-thread", "environments": [], "ephemeral": True}, "instructionSources": [],
                      "model": thread_params["model"], "modelProvider": "openai",
                      "approvalPolicy": "never", "cwd": thread_params["cwd"],
                      "runtimeWorkspaceRoots": thread_params["runtimeWorkspaceRoots"],
                      "activePermissionProfile": {"id": ":read-only"}}
            if os.environ.get("HIVEMIND_FIXTURE_BAD_THREAD"):
                result["thread"]["environments"] = [{"id": "external"}]
        elif method == "mcpServerStatus/list" and thread_params:
            names = thread_params["config"]["mcp_servers"]
            result = {"data": [{"name": name, "runtimeStatus": "connected" if os.environ.get("HIVEMIND_FIXTURE_BAD_MCP") else "disabled"} for name in names],
                      "nextCursor": None}
        else:
            print(json.dumps({"id": request.get("id"), "error": {"code": -32601}}), flush=True)
            continue
        print(json.dumps({"id": request["id"], "result": result}), flush=True)
else:
    sys.exit(2)
