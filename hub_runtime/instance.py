"""Identifica a instalação local antes de reutilizar ou encerrar a ponte."""
import json
import os
from pathlib import Path
from urllib.request import urlopen

from flask import Blueprint, jsonify

from .paths import PROJECT_ROOT, RUNTIME_ROOT

PROTOCOL = "hub-runtime-v1"
blueprint = Blueprint("hub_instance", __name__)


@blueprint.get("/hub_identity")
def identity():
    return jsonify(protocol=PROTOCOL, project_root=str(PROJECT_ROOT), pid=os.getpid())


def verify(url, root=PROJECT_ROOT):
    try:
        with urlopen(url + "/hub_identity", timeout=2) as response:
            data = json.load(response)
        source = data.get("project_root")
        if data.get("protocol") != PROTOCOL or not isinstance(source, str) or not source or Path(source).resolve() != Path(root).resolve():
            raise ValueError("origem diferente")
        if not isinstance(data.get("pid"), int) or data["pid"] <= 0:
            raise ValueError("PID inválido")
        return data
    except Exception as error:
        raise RuntimeError("Porta ocupada por uma instância não identificada deste projeto; não reutilizar nem encerrar automaticamente.") from error


def record(speech_pid):
    state = RUNTIME_ROOT / "state"
    state.mkdir(parents=True, exist_ok=True)
    data = {"protocol": PROTOCOL, "project_root": str(PROJECT_ROOT), "pid": os.getpid(), "speech_pid": speech_pid}
    tmp = state / "instance.json.tmp"
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, state / "instance.json")
