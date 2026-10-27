"""Shared, sanitized discovery data and no-inference JSON-RPC transport."""

from dataclasses import dataclass
import json
import os
import queue
import re
import subprocess
import threading
import time


_SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
_EXCLUDED_ENV = {
    "OPENAI_API_KEY", "CODEX_API_KEY", "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",
    "OPENAI_BASE_URL", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    "HUB_VAULT", "VOICE_HUB", "HUB_GUARD_STATE", "HUB_GUARD_OWNER", "HUB_GUARD_PID",
}


def discovery_environment():
    """Keep provider-managed login while excluding API/provider overrides."""
    return {key: value for key, value in os.environ.items()
            if key.upper() not in _EXCLUDED_ENV}


def safe_name(value):
    return value if isinstance(value, str) and _SAFE_NAME.fullmatch(value) else None


@dataclass(frozen=True)
class Model:
    name: str
    efforts: tuple[str, ...]


@dataclass(frozen=True)
class Discovery:
    provider: str
    version: str | None = None
    installed: bool = False
    authenticated: bool = False
    compatible: bool = False
    account_kind: str | None = None
    models: tuple[Model, ...] | None = None
    ordinary_usage_allowed: bool | None = None
    has_credits: bool | None = None
    extra_usage_enabled: bool | None = None
    policy_customizations_absent: bool | None = None
    errors: tuple[str, ...] = ()


class DiscoveryError(Exception):
    """A fixed diagnostic code, never a raw CLI or server error."""


def run_status(command, args, timeout):
    try:
        result = subprocess.run([*command, *args], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout,
                                env=discovery_environment(), check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiscoveryError("process_unavailable") from exc
    if result.returncode != 0:
        raise DiscoveryError("command_failed")
    return result.stdout


def _kill_on_close_job(process):
    """Windows Job Object holding the launcher and every descendant; closing it kills them all."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class Extended(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", ctypes.c_uint64 * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        return None
    info = Extended()
    info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    try:
        if (kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
                and kernel.AssignProcessToJobObject(job, int(process._handle))):
            return lambda: kernel.CloseHandle(job)
    except (AttributeError, OSError, TypeError, ValueError):
        pass  # best effort: close() still has taskkill
    kernel.CloseHandle(job)
    return None


def _kill_tree(process):
    """Kill the launcher and the CLI it started; killing only the launcher orphans the CLI."""
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    process.kill()


class DiscoveryRpc:
    """Only the read-only app-server methods needed for P0 are admitted."""

    _METHODS = {"initialize", "account/read", "model/list", "account/rateLimits/read", "config/read"}

    def __init__(self, command, timeout=20, experimental=False):
        self.experimental = experimental
        self.command = tuple(command)
        self.timeout = timeout
        self.process = None
        self.messages = queue.Queue()
        self.next_id = 0
        self._send_lock = threading.Lock()
        self._reader = self._close_job = None

    def __enter__(self):
        try:
            self.process = subprocess.Popen(
                [*self.command, "app-server", "--stdio"], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                encoding="utf-8", errors="replace", env=discovery_environment())
        except OSError as exc:
            raise DiscoveryError("process_unavailable") from exc
        self._track()
        try:
            self.request("initialize", {
                "clientInfo": {"name": "hivemind_discovery", "version": "1"},
                "capabilities": {"experimentalApi": self.experimental},
            })
            self._send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
            return self
        except Exception:
            self.close()
            raise

    def _track(self):
        """Own the new process: a kill-on-close job for its descendants and the stdout reader."""
        self._close_job = _kill_on_close_job(self.process)
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self):
        for line in self.process.stdout:
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    self.messages.put(item)
            except (ValueError, TypeError):
                self.messages.put({"invalid": True})
        self.messages.put({"closed": True})

    def _send(self, message):
        try:
            with self._send_lock:
                self.process.stdin.write(json.dumps(message) + "\n")
                self.process.stdin.flush()
        except (OSError, ValueError) as exc:
            raise DiscoveryError("protocol_closed") from exc

    def request(self, method, params):
        if method not in self._METHODS:
            raise DiscoveryError("method_not_allowed")
        self.next_id += 1
        request_id = self.next_id
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = None if self.timeout is None else time.monotonic() + self.timeout
        while True:
            try:
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise queue.Empty
                item = self.messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise DiscoveryError("protocol_timeout") from exc
            if item.get("invalid") or item.get("closed"):
                raise DiscoveryError("protocol_invalid_or_closed")
            if item.get("id") == request_id:
                if "error" in item or not isinstance(item.get("result"), dict):
                    error = item.get("error")
                    code = error.get("code") if isinstance(error, dict) else None
                    suffix = str(code) if type(code) is int else "unknown"
                    message = error.get("message", "") if isinstance(error, dict) else ""
                    category = ("reload_config" if isinstance(message, str) and "failed to reload config" in message
                                else "read_mcp" if isinstance(message, str) and "failed to read MCP server status" in message
                                else "other")
                    raise DiscoveryError("protocol_request_failed:" + method + ":" + suffix + ":" + category)
                return item["result"]
            if "id" in item and "method" in item:
                raise DiscoveryError("unexpected_server_request")

    def close(self):
        if self.process is None:
            return
        try:
            if self.process.stdin:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _kill_tree(self.process)
                self.process.wait(timeout=5)
        finally:
            # A CLI that outlived the launcher keeps the pipe open; closing it under the reader deadlocks.
            if self._close_job is not None:
                self._close_job()
                self._close_job = None
        if self._reader is not None:
            self._reader.join(timeout=5)
        if self.process.stdout and not (self._reader and self._reader.is_alive()):
            self.process.stdout.close()
        self.process = None

    def __exit__(self, exc_type, exc, traceback):
        self.close()
