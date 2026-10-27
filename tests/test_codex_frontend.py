"""Fronteiras do frontend Codex: catálogo, assets e isolamento sem CLI real."""
import json
import shutil
import subprocess
from pathlib import Path

from flask import Flask

from codex_frontend import blueprint
from codex_frontend.catalog import get_catalog, normalize_models

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


def catalog_model(slug="gpt-test", efforts=("low", "high", "ultra"), **extra):
    return {"slug":slug, "visibility":"list", "display_name":"GPT Test",
            "default_reasoning_level":"low",
            "supported_reasoning_levels":[{"effort":e} for e in efforts], **extra}


def test_catalog_returns_only_public_metadata_and_valid_efforts(tmp_path):
    path = tmp_path / "models_cache.json"
    path.write_text(json.dumps({"models":[catalog_model(efforts=("low", "ultra", "bogus", "low"),
        api_key="secret", internal_prompt="private", provider_credentials="private"),
        catalog_model("gpt-hidden", visibility="hide"), catalog_model("other-provider")]}))
    result = get_catalog(path)
    assert result["source"] == "local"
    assert result["backendReady"] is False
    assert result["models"] == [{"id":"gpt-test", "name":"GPT Test",
        "efforts":["low", "ultra"], "defaultEffort":"low"}]
    assert "secret" not in json.dumps(result)


def test_catalog_replaces_invalid_default_and_deduplicates():
    model = catalog_model(default_reasoning_level="unsupported")
    models = normalize_models({"models":[model, model]})
    assert len(models) == 1
    assert models[0]["defaultEffort"] == "low"


def test_missing_corrupt_or_empty_catalog_uses_explicit_snapshot(tmp_path):
    path = tmp_path / "cache.json"
    for value in (None, "{invalid", '{"models":[]}', '[]'):
        if value is not None:
            path.write_text(value)
        result = get_catalog(path)
        assert result["source"] == "snapshot"
        assert result["models"][0]["id"] == "gpt-6.1-sol"
        assert "ultra" in result["models"][0]["efforts"]


def test_blueprint_serves_modules_and_catalog_without_assistant_endpoints(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    app = Flask("test-codex-ui")
    app.register_blueprint(blueprint)
    client = app.test_client()
    for name in ("providers.js", "models.js", "galaxy.js", "codex.css"):
        assert client.get("/codex-ui/static/" + name).status_code == 200
    response = client.get("/codex-ui/models")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    for route in ("ask", "stt", "session_start", "session_reset", "abort", "speak"):
        assert client.post("/codex-ui/" + route).status_code == 404
    assert client.get("/codex-ui/static/../models.json").status_code == 404


def function_body(name):
    # Captura o corpo por chaves, sem depender de quantas linhas tem a função.
    start = INDEX.index("function " + name + "(")
    start = INDEX.index("{", start)
    depth = 1
    for end in range(start + 1, len(INDEX)):
        depth += (INDEX[end] == "{") - (INDEX[end] == "}")
        if depth == 0:
            return INDEX[start + 1:end]
    raise AssertionError("função incompleta")


def test_codex_entry_points_guard_before_capturing_audio_or_recording_turns():
    for function, side_effect in (("startListening", "getMic("),
                                  ("sendTextPrompt", "recordTurn("),
                                  ("runSkill", "recordTurn("),
                                  ("askAndSpeak", "streamAsk(")):
        body = function_body(function)
        assert body.index("allowAction(") < body.index(side_effect)


def test_codex_local_sessions_never_warm_reset_end_or_abort_claude():
    for function, endpoint in (("addTab", "'/session_start'"),
                               ("closeTab", "'/session_end'"),
                               ("onNewConv", "'/session_reset'"),
                               ("onStop", "'/abort'")):
        body = function_body(function)
        assert body.index("tab.provider === 'codex'") < body.index(endpoint)
        assert "return;" in body[body.index("tab.provider === 'codex'"):body.index(endpoint)]
    unload = INDEX[INDEX.index("window.addEventListener('beforeunload'"):]
    assert "if (t.mirror) return;" in unload
    assert unload.index("if (t.provider === 'codex') return;") < unload.index("sendBeacon('/session_end'")


def test_mobile_cannot_focus_codex_and_session_limits_stay_in_sync():
    assert "window.hubProviders?.current() !== 'codex'" in function_body("mobileTurnStart")
    assert "const MAX_TABS = 6;" in INDEX
    assert "accepts(t)" in function_body("renderTabBar")
    assert "accepts(c)" in function_body("renderConvList")


def test_runtime_does_not_load_prototype_editor_or_fake_conversations():
    runtime = "\n".join(p.read_text(encoding="utf-8") for p in
        (ROOT / "codex_frontend" / "static").glob("*.js"))
    assert "support.js" not in INDEX
    assert "initSessions" not in runtime
    assert "this.forced()" not in runtime
    assert "Component.REVIEW" not in runtime
    assert "10500" in runtime and "7800" in runtime


def test_javascript_behavior_without_real_services():
    node = shutil.which("node")
    if node is None:
        import pytest
        pytest.skip("Node não está instalado para a verificação JS")
    result = subprocess.run([node, str(ROOT / "tests" / "codex_frontend_behavior.mjs")],
                            cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
