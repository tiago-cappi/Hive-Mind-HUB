import json
import queue
import threading
from types import SimpleNamespace
import pytest

from HiveMind.backend.adapters.claude import ClaudeProofSession
from HiveMind.backend.adapters.codex import CodexProofSession
from HiveMind.backend.capabilities import ToolBroker


class FakeRpc:
    def __init__(self, events):
        self.messages = queue.Queue()
        for event in events:
            self.messages.put(event)
        self.sent = []
        self.next_id = 0

    def _send(self, item):
        self.sent.append(item)


def session(cls, broker, rpc):
    item = object.__new__(cls)
    item.model, item.effort, item.broker, item.rpc = "fixture-model", "high", broker, rpc
    item.adapter = SimpleNamespace(discover=lambda: object())
    item.evidence = lambda: object()
    item._turn_lock = threading.Lock()
    item._pause_pending = False
    return item


def test_codex_turn_uses_pinned_thread_and_broker(monkeypatch):
    import HiveMind.backend.capabilities as capabilities
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    broker = ToolBroker({"read": lambda args: {"content": "fixture"}, "patch": lambda a: None,
                         "checks": lambda a: None})
    rpc = FakeRpc([
        {"id": 1, "result": {"turn": {"id": "t"}}},
        {"id": "call", "method": "item/tool/call", "params": {"threadId": "thread", "turnId": "t",
                                                                    "tool": "read", "arguments": {"path": "a"}}},
        {"method": "item/completed", "params": {"threadId": "thread", "turnId": "old", "item": {"type": "agentMessage", "text": "stale"}}},
        {"method": "item/completed", "params": {"threadId": "thread", "turnId": "t", "item": {"type": "agentMessage", "text": "done"}}},
        {"method": "turn/completed", "params": {"threadId": "thread", "turn": {"id": "t", "status": "completed"}}},
    ])
    codex = session(CodexProofSession, broker, rpc)
    codex.thread_id, codex._turn_id, codex._turn_starting = "thread", None, False
    assert codex.turn("fixture") == "done"
    assert rpc.sent[0]["params"]["threadId"] == "thread"
    assert rpc.sent[0]["params"]["effort"] == "high"
    assert json.loads(rpc.sent[1]["result"]["contentItems"][0]["text"]) == {"content": "fixture"}


def test_codex_server_request_id_collision_before_and_after_start(monkeypatch):
    import HiveMind.backend.capabilities as capabilities
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    calls = []
    broker = ToolBroker({"read": lambda args: calls.append(args) or {"content": "ok"}})
    request = lambda turn: {"id": 9, "method": "item/tool/call", "params": {
        "threadId": "thread", "turnId": turn, "tool": "read", "arguments": {"path": "a"}}}
    rpc = FakeRpc([request(None), {"id": 9, "result": {"turn": {"id": "t"}}}, request("t"),
                   {"method": "turn/completed", "params": {"threadId": "thread", "turn": {"id": "t", "status": "completed"}}}])
    rpc.next_id = 8
    codex = session(CodexProofSession, broker, rpc)
    codex.thread_id, codex._turn_id, codex._turn_starting = "thread", None, False
    assert codex.turn("fixture") == ""
    assert calls == [{"path": "a"}]
    assert json.loads(rpc.sent[1]["result"]["contentItems"][0]["text"]) == {"error": "tool_request_invalid"}
    assert rpc.sent[2]["id"] == 9 and rpc.sent[2]["result"]["success"] is True


def test_codex_invalid_start_response_still_fails(monkeypatch):
    import HiveMind.backend.capabilities as capabilities
    from HiveMind.backend.adapters.base import DiscoveryError
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    codex = session(CodexProofSession, ToolBroker({"read": lambda args: None}), FakeRpc([{"id": 1, "error": {"code": -1}}]))
    codex.thread_id, codex._turn_id, codex._turn_starting = "thread", None, False
    with pytest.raises(DiscoveryError, match="^turn_start_failed$"):
        codex.turn("fixture")


def test_claude_model_only_loop_has_no_native_tools(monkeypatch):
    import HiveMind.backend.capabilities as capabilities
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    broker = ToolBroker({"read": lambda args: {"content": "fixture"}, "patch": lambda a: None,
                         "checks": lambda a: None})
    rpc = FakeRpc([
        {"type": "result", "subtype": "success", "is_error": False,
         "result": '{"action":"read","arguments":{"path":"a"}}'},
        {"type": "result", "subtype": "success", "is_error": False, "result": '{"final":"done"}'},
    ])
    claude = session(ClaudeProofSession, broker, rpc)
    claude._turn_active = False
    assert claude.turn("fixture") == "done"
    assert len(rpc.sent) == 2 and "fixture" in rpc.sent[1]["message"]["content"]


def test_codex_failure_retains_only_safe_error_category(monkeypatch):
    import HiveMind.backend.capabilities as capabilities
    from HiveMind.backend.adapters.base import DiscoveryError
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    broker = ToolBroker({"read": lambda args: None, "patch": lambda args: None, "checks": lambda args: None})
    rpc = FakeRpc([
        {"id": 1, "result": {"turn": {"id": "t"}}},
        {"method": "turn/completed", "params": {"threadId": "thread", "turn": {"id": "t", "status": "failed",
            "error": {"message": "private fixture", "codexErrorInfo": "usageLimitExceeded"}}}},
    ])
    codex = session(CodexProofSession, broker, rpc)
    codex.thread_id, codex._turn_id, codex._turn_starting = "thread", None, False
    with pytest.raises(DiscoveryError, match="^turn_failed:usageLimitExceeded$"):
        codex.turn("fixture")


def test_tool_result_reply_is_inside_pause_drain():
    entered, release = threading.Event(), threading.Event()
    broker = ToolBroker({"read": lambda a: "ok", "patch": lambda a: None, "checks": lambda a: None})
    def reply(ok, result):
        entered.set()
        release.wait(5)
    thread = threading.Thread(target=lambda: broker.dispatch_and_reply("read", {}, reply))
    thread.start()
    assert entered.wait(2)
    assert broker.admission.request_pause() is False and not broker.admission.drained()
    release.set()
    thread.join(5)
    assert broker.admission.drained()


def test_opt_in_launcher_validates_commands_and_skips_personal_profile(monkeypatch):
    import sys
    import hub_runtime.assistant as assistant
    from HiveMind.backend.adapters import launcher
    calls = []
    monkeypatch.setattr(launcher, "provider_command", lambda provider: ("fixture-node", "fixture-cli"))
    monkeypatch.setattr(launcher.subprocess, "run", lambda command, **kwargs: calls.append(command) or SimpleNamespace(returncode=0))
    assert launcher.main(["codex", "app-server", "--stdio"]) == 0
    assert launcher.main(["codex", "app-server", "--stdio", "--unsafe"]) == 2
    assert calls == [["fixture-node", "fixture-cli", "app-server", "--stdio"]]
    monkeypatch.setattr(assistant, "vault_root", lambda: (_ for _ in ()).throw(AssertionError("personal profile used")))
    monkeypatch.setattr(launcher, "main", lambda args: 17 if args == ["codex", "app-server", "--stdio"] else 1)
    monkeypatch.setattr(sys, "argv", ["assistant", "--hivemind", "codex", "app-server", "--stdio"])
    assert assistant.main() == 17


def test_hive_environment_excludes_personal_vault_and_guard(monkeypatch):
    from HiveMind.backend.adapters.base import discovery_environment
    monkeypatch.setenv("HUB_VAULT", "private")
    monkeypatch.setenv("HUB_GUARD_STATE", "private")
    monkeypatch.setenv("VOICE_HUB", "1")
    environment = discovery_environment()
    assert not {"HUB_VAULT", "HUB_GUARD_STATE", "VOICE_HUB"} & set(environment)


@pytest.mark.parametrize("result, expected", [
    ({"subtype": "error_max_turns", "is_error": True, "result": "private fixture text"}, "error_max_turns"),
    ({"subtype": "error_during_execution", "is_error": True, "errors": ["private fixture text"]},
     "error_during_execution"),
    ({"subtype": "success", "is_error": True, "api_error_status": 429, "result": "private fixture text"},
     "api_error_429"),
    ({"subtype": "success", "is_error": True, "api_error_status": 99, "result": "private fixture text"}, "unknown"),
    ({"subtype": "private fixture text", "is_error": True, "api_error_status": None}, "unknown"),
    ({"subtype": "error_max_turns", "is_error": False}, "error_max_turns"),
])
def test_claude_failure_retains_only_closed_error_category(monkeypatch, result, expected):
    import HiveMind.backend.capabilities as capabilities
    from HiveMind.backend.adapters.base import DiscoveryError
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    broker = ToolBroker({"read": lambda args: None, "patch": lambda args: None, "checks": lambda args: None})
    claude = session(ClaudeProofSession, broker, FakeRpc([{"type": "result", **result}]))
    claude._turn_active = False
    with pytest.raises(DiscoveryError) as caught:
        claude.turn("fixture")
    assert str(caught.value) == "turn_failed:claude:" + expected


@pytest.mark.parametrize("kind", ["commandExecution", "fileChange", "mcpToolCall", "webSearch", "unknownFuture"])
def test_codex_native_tool_item_fails_closed(monkeypatch, kind):
    import HiveMind.backend.capabilities as capabilities
    from HiveMind.backend.adapters.base import DiscoveryError
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    broker = ToolBroker({"read": lambda args: None, "patch": lambda args: None, "checks": lambda args: None})
    rpc = FakeRpc([
        {"id": 1, "result": {"turn": {"id": "t"}}},
        {"method": "item/started", "params": {"threadId": "thread", "turnId": "t", "item": {"type": kind}}},
        {"method": "turn/completed", "params": {"threadId": "thread", "turn": {"id": "t", "status": "completed"}}},
    ])
    codex = session(CodexProofSession, broker, rpc)
    codex.thread_id, codex._turn_id, codex._turn_starting = "thread", None, False
    with pytest.raises(DiscoveryError, match="^native_tool_unexpected$"):
        codex.turn("fixture")


def test_codex_turn_forwards_output_schema_only_when_given(monkeypatch):
    import HiveMind.backend.capabilities as capabilities
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    broker = ToolBroker({"read": lambda args: None, "patch": lambda args: None, "checks": lambda args: None})
    for schema in (None, {"type": "object", "properties": {}, "required": [], "additionalProperties": False}):
        rpc = FakeRpc([
            {"id": 1, "result": {"turn": {"id": "t"}}},
            {"method": "turn/completed", "params": {"threadId": "thread", "turn": {"id": "t", "status": "completed"}}},
        ])
        codex = session(CodexProofSession, broker, rpc)
        codex.thread_id, codex._turn_id, codex._turn_starting = "thread", None, False
        codex.turn("fixture", schema)
        assert rpc.sent[0]["params"].get("outputSchema") == schema


def test_codex_turn_returns_only_final_answer_after_commentary(monkeypatch):
    # Teste no navegador de 24/10/2026: comentário + resposta final juntados quebravam o JSON do veredito.
    import HiveMind.backend.capabilities as capabilities
    monkeypatch.setattr(capabilities, "evaluate", lambda *args: SimpleNamespace(execution_allowed=True))
    broker = ToolBroker({"read": lambda args: None, "patch": lambda args: None, "checks": lambda args: None})
    message = lambda text, phase: {"method": "item/completed", "params": {
        "threadId": "thread", "turnId": "t", "item": {"type": "agentMessage", "text": text, "phase": phase}}}
    rpc = FakeRpc([
        {"id": 1, "result": {"turn": {"id": "t"}}},
        message('{"criteria":{"a":"unverifiable"},"evidence":"checking"}', "commentary"),
        message('{"criteria":{"a":"passed"},"evidence":"read"}', "final_answer"),
        {"method": "turn/completed", "params": {"threadId": "thread", "turn": {"id": "t", "status": "completed"}}},
    ])
    codex = session(CodexProofSession, broker, rpc)
    codex.thread_id, codex._turn_id, codex._turn_starting = "thread", None, False
    assert json.loads(codex.turn("fixture")) == {"criteria": {"a": "passed"}, "evidence": "read"}
    rpc = FakeRpc([
        {"id": 1, "result": {"turn": {"id": "t"}}},
        message("checking", "commentary"),
        message('{"ok":true}', None),
        {"method": "turn/completed", "params": {"threadId": "thread", "turn": {"id": "t", "status": "completed"}}},
    ])
    codex = session(CodexProofSession, broker, rpc)
    codex.thread_id, codex._turn_id, codex._turn_starting = "thread", None, False
    assert codex.turn("fixture") == '{"ok":true}'
