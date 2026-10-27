"""Executa o CLI com instruções locais, autenticação existente e guardas comuns."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

if __package__:
    from .paths import PROJECT_ROOT, RUNTIME_ROOT, vault_root
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from hub_runtime.paths import PROJECT_ROOT, RUNTIME_ROOT, vault_root


def bridge_command(cli_args):
    """Comando compartilhado por persistente e fallback, preservando suas flags."""
    python = PROJECT_ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    args = [str(python), "-m", "hub_runtime.assistant", *cli_args]
    return subprocess.list2cmdline(args)


def settings(vault, state):
    hook = RUNTIME_ROOT / "guards" / "file_guard.py"
    command = subprocess.list2cmdline([sys.executable, str(hook)])
    config = {
        "claudeMdExcludes": ["**/CLAUDE.md", "**/CLAUDE.local.md", "**/AGENTS.md", "**/.claude/rules/**"],
        "pluginConfigs": {
            "cc-plugin-agents-md@builtin": {"options": {"instructionFiles": "managed-only"}},
        },
        "autoMemoryEnabled": False,
        "hooks": {
            event: [{"matcher": ".*", "hooks": [{"type": "command", "command": command, "timeout": 30}]}]
            for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionDenied")
        },
    }
    config["hooks"]["PostToolBatch"] = [{"hooks": [{"type": "command", "command": command, "timeout": 30}]}]
    return config


def operational_prompt(vault):
    text = (RUNTIME_ROOT / "instructions" / "uso-pessoal.md").read_text(encoding="utf-8")
    text = text.replace("{{VAULT}}", str(vault)).replace("{{PROJECT}}", str(PROJECT_ROOT))
    # Uma única linha evita que o cmd.exe interprete quebras como comandos.
    return " ".join(text.split())


def main():
    if sys.argv[1:2] == ["--hivemind"]:
        if __package__:
            from HiveMind.backend.adapters.launcher import main as hivemind_main
        else:
            import importlib
            import importlib.util
            backend = Path(__file__).resolve().parent.parent / "HiveMind" / "backend"
            name = "_hivemind_launcher"
            spec = importlib.util.spec_from_file_location(name, backend / "__init__.py",
                                                          submodule_search_locations=[str(backend)])
            if spec is None or spec.loader is None:
                return 2
            package = importlib.util.module_from_spec(spec)
            sys.modules[name] = package
            spec.loader.exec_module(package)
            hivemind_main = importlib.import_module(name + ".adapters.launcher").main
        return hivemind_main(sys.argv[2:])
    vault = vault_root()
    owner = uuid.uuid4().hex
    state = RUNTIME_ROOT / "state" / "guards"
    config_dir = RUNTIME_ROOT / "state" / "assistant"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = config_dir / (owner + ".json")
    config.write_text(json.dumps(settings(vault, state)), encoding="utf-8")
    env = dict(os.environ, VOICE_HUB="1", HUB_VAULT=str(vault),
               HUB_GUARD_STATE=str(state), HUB_GUARD_OWNER=owner,
               HUB_GUARD_PID=str(os.getpid()), CLAUDE_CODE_DISABLE_AUTO_MEMORY="1",
               PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    env.pop("CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD", None)
    args = ["claude", *sys.argv[1:], "--setting-sources", "", "--settings", str(config),
            "--add-dir", str(vault), "--append-system-prompt", operational_prompt(vault),
            "--system-prompt-snapshot", "off"]
    try:
        # OAuth/instalação do CLI continuam no sistema. Não carregar hooks globais
        # (por exemplo, o Stop que fala fora da fila SPEAK_Q do Hub).
        result = subprocess.run(subprocess.list2cmdline(args) if os.name == "nt" else args,
                                cwd=PROJECT_ROOT, env=env, shell=os.name == "nt")
        return result.returncode
    finally:
        from .guards.file_guard import release_owner
        release_owner(state, owner)
        config.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
