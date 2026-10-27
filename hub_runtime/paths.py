"""Resolve os caminhos do projeto e valida o acervo explicitamente."""
import os
import hashlib
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_ROOT = PROJECT_ROOT / "hub_runtime"


def vault_root():
    configured = os.environ.get("HUB_VAULT")
    target = Path(configured) if configured else Path.home() / "Documents" / "Obsidian Vault"
    if not target.is_absolute():
        raise ValueError("HUB_VAULT precisa ser um caminho absoluto")
    target = target.resolve()
    if not target.is_dir():
        raise ValueError(f"Acervo Obsidian não encontrado: {target}. Configure HUB_VAULT.")
    if target == PROJECT_ROOT or PROJECT_ROOT in target.parents or target in PROJECT_ROOT.parents:
        raise ValueError("O acervo e o projeto precisam ser pastas separadas")
    return target


def voice_python():
    return RUNTIME_ROOT / "voice" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def speech_temp():
    """Canal por instalação: não disputa sentinelas com ferramentas globais."""
    key = hashlib.sha256(os.path.normcase(str(PROJECT_ROOT)).encode()).hexdigest()[:12]
    return Path(os.environ.get("HUB_SPEAK_TEMP", str(Path(tempfile.gettempdir()) / ("core_hub_" + key))))
