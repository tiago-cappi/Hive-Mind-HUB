"""Validated opt-in launcher, separate from the personal assistant profile."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

from .base import discovery_environment, safe_name
from .claude import model_only_arguments


def provider_command(provider):
    node = shutil.which("node")
    appdata = os.environ.get("APPDATA")
    if provider not in {"codex", "claude"} or not appdata or provider == "codex" and not node:
        raise ValueError("provider_unavailable")
    package = ("@openai/codex/bin/codex.js" if provider == "codex"
               else "@anthropic-ai/claude-code/bin/claude.exe")
    script = Path(appdata) / "npm" / "node_modules" / package
    if not script.is_file():
        raise ValueError("provider_unavailable")
    return (node, str(script)) if provider == "codex" else (str(script),)


def main(argv):
    if not argv or argv[0] not in {"codex", "claude"}:
        return 2
    provider, arguments = argv[0], argv[1:]
    if provider == "codex":
        valid = arguments == ["app-server", "--stdio"]
    else:
        prefix = model_only_arguments()
        valid = (arguments[:len(prefix)] == prefix and len(arguments) == len(prefix) + 4
                 and arguments[-4] == "--model" and safe_name(arguments[-3])
                 and arguments[-2] == "--effort" and safe_name(arguments[-1]))
    if not valid:
        return 2
    try:
        command = provider_command(provider)
        # Explicit stdio: under pythonw (no console) inherited handles never reach the CLI.
        return subprocess.run([*command, *arguments], stdin=0, stdout=1, stderr=subprocess.DEVNULL,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                              env=discovery_environment(), check=False).returncode
    except (OSError, ValueError):
        return 2


def adapters(generation):
    """Build discovery commands and generation-pinned launch commands internally."""
    from .claude import ClaudeAdapter
    from .codex import CodexAdapter
    assistant = Path(generation["path"]) / "hub_runtime" / "assistant.py"
    result = {}
    for name, cls in (("codex", CodexAdapter), ("claude", ClaudeAdapter)):
        try:
            command = provider_command(name)
        except ValueError:
            continue
        result[name] = cls(command, session_command=(sys.executable, "-B", str(assistant), "--hivemind", name))
    return result
