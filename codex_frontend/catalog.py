"""Metadados públicos do catálogo local do Codex, sem ler credenciais."""

import json
import os
import re
from pathlib import Path

EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
FALLBACK = Path(__file__).with_name("models.json")


def normalize_models(data):
    result = []
    seen = set()
    for model in data.get("models", []):
        slug = model.get("slug", "")
        if not re.fullmatch(r"gpt-[\w.-]+", slug) or model.get("visibility") != "list" or slug in seen:
            continue
        efforts = list(dict.fromkeys(
            item.get("effort") for item in model.get("supported_reasoning_levels", [])
            if isinstance(item, dict) and item.get("effort") in EFFORTS
        ))
        if not efforts:
            continue
        default = model.get("default_reasoning_level")
        name = model.get("display_name")
        seen.add(slug)
        result.append({
            "id": slug,
            "name": name if isinstance(name, str) and name else slug,
            "efforts": efforts,
            "defaultEffort": default if default in efforts else efforts[0],
        })
    return result


def get_catalog(cache_path=None):
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    path = Path(cache_path) if cache_path is not None else home / "models_cache.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        models = normalize_models(data)
        if models:
            return {"models": models, "source": "local", "backendReady": False}
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return {
        "models": json.loads(FALLBACK.read_text(encoding="utf-8")),
        "source": "snapshot", "backendReady": False,
    }
