"""Lazy single service owner; import does not start processes or missions."""

import importlib
from pathlib import Path
import threading

from .workspaces import load_runtime_generation


_lock = threading.Lock()
_service = None


def get_service():
    global _service
    with _lock:
        if _service is None:
            project = Path(__file__).resolve().parents[2]
            state = project / "HiveMind" / "state"
            (state / "runtime").mkdir(parents=True, exist_ok=True)
            generation, cls = load_runtime_generation(project, state / "runtime")
            launcher = importlib.import_module(cls.__module__.rsplit(".", 1)[0] + ".adapters.launcher")
            _service = cls(state, generation=generation, adapters=launcher.adapters(generation))
            _service.start_watchdog()
        return _service


def hub_exit_ready():
    with _lock:
        service = _service
    return service is None or service.hub_exit_ready()
