"""Integration boundaries for the native Hive Mind demonstration frontend."""

import shutil
import subprocess
import hashlib
import re
from pathlib import Path

from flask import Flask

from HiveMind import blueprint


ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
PROVIDERS = (ROOT / "codex_frontend/static/providers.js").read_text(encoding="utf-8")
HIVE_STATIC = ROOT / "HiveMind/frontend/static"


def function_body(name):
    start = INDEX.index("function " + name + "(")
    start = INDEX.index("{", start)
    depth = 1
    for end in range(start + 1, len(INDEX)):
        depth += (INDEX[end] == "{") - (INDEX[end] == "}")
        if depth == 0:
            return INDEX[start + 1:end]
    raise AssertionError(f"função {name} incompleta")


def test_blueprint_serves_only_static_frontend_and_all_native_assets():
    app = Flask("test-hive-ui")
    app.register_blueprint(blueprint)
    client = app.test_client()
    for name in (
        "app.js", "demo-data.js", "simulation.js", "geometry.js", "hive.js",
        "drawers.js", "hive.css", "bee-animation/bee.js", "bee-animation/bee.css",
        "assets/hive-mind-logo.png",
        "assets/operaria-animacao/asa-esquerda.png",
        "assets/operaria-animacao/asa-direita.png",
        "assets/operaria-animacao/corpo-sem-asas.png",
        "assets/rainha-animacao/asa-esquerda.png",
        "assets/rainha-animacao/asa-direita.png",
        "assets/rainha-animacao/corpo-sem-asas.png",
    ):
        assert client.get("/hive-ui/static/" + name).status_code == 200
    for route in ("ask", "stt", "session_start", "session_reset", "abort", "speak"):
        assert client.post("/hive-ui/" + route).status_code == 404
    assert client.get("/hive-ui/static/../routes.py").status_code == 404


def test_prototype_was_moved_whole_and_runtime_does_not_load_editor():
    prototype = ROOT / "HiveMind/prototipo"
    assert prototype.is_dir()
    assert not (ROOT / "Protótipo Hive Mind Desktop").exists()
    expected = {
        ".thumbnail": "2DBD762F0EA4E45D3B2BBB8FEBC2788E5A8C39DF798E1AF39DEADB87871D3ACC",
        "assets/hive-mind-logo.png": "6A5399F3055504ADFA2E416D8F88C35EB481FA579BACD6377FAAB6D1A44BFBA4",
        "Hive Mind v1.dc.html": "EB983AE65F4AB649BA078374B3C0A10DDA79BCEE87B8615FB1D70E781E62E7D0",
        "Hive Mind.dc.html": "03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6",
        "support.js": "8FE7DF74405F3C55F49B7249C74EA1397E65D07DEA2B1BD3B4A489BEC2E28CBE",
        "uploads/Hive Mind Logo.webp": "7BAAC77F807A8C572D35D99AF339E73C299ACE75CDE75A9615BD249764AEB22E",
    }
    files = {path.relative_to(prototype).as_posix() for path in prototype.rglob("*") if path.is_file()}
    assert files == set(expected)
    for relative, digest in expected.items():
        assert hashlib.sha256((prototype / relative).read_bytes()).hexdigest().upper() == digest
    runtime = "\n".join(path.read_text(encoding="utf-8") for path in HIVE_STATIC.rglob("*.js"))
    assert "support.js" not in runtime
    assert "DCLogic" not in runtime
    assert "React" not in runtime
    assert "sc-for" not in runtime
    assert "iframe" not in runtime
    assert not (HIVE_STATIC / "layout.css").exists()
    assert "layout.css" not in (HIVE_STATIC / "app.js").read_text(encoding="utf-8")


def test_hive_page_is_separate_from_provider_and_never_creates_a_session():
    assert "selectedPage" in PROVIDERS and "preferredPage" in PROVIDERS
    assert "function canUseAssistantUI()" in PROVIDERS
    select_page = PROVIDERS[PROVIDERS.index("function selectPage("):PROVIDERS.index("window.hubProviders")]
    assert "hub.createSession()" not in select_page
    assert "hub.selectSession(" not in select_page
    assert "localStorage.setItem('core.page'" in select_page
    assert "localStorage.setItem('core.assistant'" in PROVIDERS
    assert "provider !== 'claude' && provider !== 'codex'" in PROVIDERS


def test_all_six_authorized_page_guards_are_present_without_guarding_stt_continuation():
    for name in ("startListening", "runSkill", "sendTextPrompt"):
        body = function_body(name)
        assert body.index("canUseAssistantUI") < body.index("allowAction")
    start = function_body("startListening")
    assert "acquired.getTracks().forEach(track=>track.stop())" in start
    assert start.count("canUseAssistantUI") == 2
    keydown = INDEX[INDEX.index("document.addEventListener('keydown'"):]
    keydown = keydown[:keydown.index("});") + 3]
    assert "canUseAssistantUI" in keydown
    mobile = function_body("mobileTurnStart")
    assert "canUseAssistantUI?.() !== false" in mobile
    assert "canUseAssistantUI" not in function_body("askAndSpeak")
    assert "canUseAssistantUI" not in function_body("onRecStop")


def test_simulation_content_and_accessibility_contract_are_explicit():
    data = (HIVE_STATIC / "demo-data.js").read_text(encoding="utf-8")
    app = (HIVE_STATIC / "app.js").read_text(encoding="utf-8")
    drawers = (HIVE_STATIC / "drawers.js").read_text(encoding="utf-8")
    simulation = (HIVE_STATIC / "simulation.js").read_text(encoding="utf-8")
    hive = (HIVE_STATIC / "hive.js").read_text(encoding="utf-8")
    for phrase in ("não controla missões reais", "Demonstração simulada", "Nenhum agente", "23 pedidos"):
        assert phrase in data + app + drawers + simulation
    for tab in ("Visão geral", "Tarefas", "Skills", "Ferramentas", "Relações"):
        assert tab in drawers
    for action in ("Simular missão", "Solicitar ajuste", "Tentar novamente", "Avançar etapa", "Reiniciar"):
        assert action in drawers
    assert "textContent" in drawers
    assert "innerHTML" not in drawers or "<strong>Nova operária" in drawers
    assert "send.type='submit'" in drawers
    assert "connections(state)" in drawers
    assert "stepProgress()" in simulation
    assert "Math.floor" in hive
    assert ".hm-hud-alert[hidden]{display:none}" in (HIVE_STATIC / "hive.css").read_text(encoding="utf-8")


def test_javascript_state_machine_without_browser_or_services():
    node = shutil.which("node")
    if node is None:
        import pytest
        pytest.skip("Node não está instalado para a verificação JS")
    result = subprocess.run(
        [node, str(ROOT / "tests/hivemind_frontend_behavior.mjs")],
        cwd=ROOT, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_selected_mission_exposes_audited_cycle_limit_and_source_reconciliation_controls():
    drawers = (HIVE_STATIC / "live-mission.js").read_text(encoding="utf-8")
    assert "Máximo de ciclos desta missão" in drawers
    assert "live.command('cycle_limit'" in drawers
    assert "Reconciliar origem em área isolada" in drawers
    assert "solicite um novo plano consciente" in drawers


def test_live_state_uses_event_cursor_and_bounded_history():
    state = (HIVE_STATIC / "mission-state.js").read_text(encoding="utf-8")
    assert "?after=${this.eventSeq}" in state
    assert ".slice(-500)" in state
    assert "this.eventMission!==wanted" in state


def test_team_validation_and_chat_queen_follow_current_configuration():
    team = (HIVE_STATIC / "live-team.js").read_text(encoding="utf-8")
    chat = (HIVE_STATIC / "live-chat.js").read_text(encoding="utf-8")
    drawers = (HIVE_STATIC / "live-drawers.js").read_text(encoding="utf-8")
    assert "export function validateTeam" in team
    assert "validateTeam(rows)" in team
    assert "chatQueen(last.status,planning)" in chat
    assert "queen:planning.queen" not in chat + drawers
    assert "export {validateTeam,chatQueen}" in drawers
    assert "queen_configuration_changed" in (HIVE_STATIC / "messages.js").read_text(encoding="utf-8")


def test_demo_texts_state_that_a_real_backend_exists_and_demo_is_separate():
    demo = (HIVE_STATIC / "demo-data.js").read_text(encoding="utf-8")
    package = (ROOT / "HiveMind/__init__.py").read_text(encoding="utf-8")
    assert "backend Hive Mind pendente" not in demo
    assert "não controla missões reais" in demo
    assert "intentionally absent" not in package


def _documented_codes():
    text = (ROOT / "docs/hivemind/backend.md").read_text(encoding="utf-8")
    section = text[text.index("## Códigos de erro e conflito"):text.index("## Armadilhas")]
    codes = set()
    table = None
    for line in section.splitlines():
        if line.startswith("| Código |"):
            table = 1
        elif line.startswith("| Grupo |"):
            table = 2
        elif not line.startswith("|"):
            table = None
        elif table and not line.startswith("|---"):
            cells = line.split("|")
            if cells[1].strip() == "Resto":
                codes.add("job_failed")
                continue
            codes.update(re.findall(r"`([a-z_]+)(?::<[^`]*>)?`", cells[table]))
    paragraph = section[section.index("Códigos de `WorkspaceError`"):].split("\n\n")[0]
    codes.update(re.findall(r"`([a-z_]+)`", paragraph.split(".", 1)[0]))
    return codes


def test_every_documented_code_and_adapter_reason_has_a_portuguese_message():
    messages = (HIVE_STATIC / "messages.js").read_text(encoding="utf-8")
    adapters = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "HiveMind/backend/adapters").glob("*.py"))
    adapter_codes = set(re.findall(r'DiscoveryError\("([a-z_]+)"\)', adapters))
    documented = _documented_codes()
    assert {"stale_revision", "delivery_recovery_required", "restricted_check_failed", "job_failed"} <= documented
    missing = sorted(code for code in documented | adapter_codes if f"{code}:'" not in messages)
    assert not missing, missing
    assert "abandoned:'" in messages


def test_hive_readout_names_the_real_backend_and_old_demo_text_is_gone():
    assert "HIVE MIND · MISSÕES COM CLAUDE E CODEX" in PROVIDERS
    assert "BACKEND PENDENTE" not in PROVIDERS.split("function updateReadout()")[1].split("}")[0]


def test_recovery_required_has_no_advance_button_and_abandon_asks_inline():
    drawers = (HIVE_STATIC / "live-mission.js").read_text(encoding="utf-8")
    assert "live.command('abandon')" in drawers
    assert "Confirmar encerramento" in drawers
    assert "window.confirm" not in drawers
    assert "data.reconciliation_required&&!recovering&&!abandoned" in drawers


def test_messages_lookup_ignores_prototype_names_and_drawer_notice_is_neutral():
    messages = (HIVE_STATIC / "messages.js").read_text(encoding="utf-8")
    drawers = "\n".join((HIVE_STATIC / name).read_text(encoding="utf-8") for name in ("live-drawers.js", "live-mission.js", "live-team.js", "live-chat.js", "live-delivery.js"))
    assert "Object.hasOwn(messages,code)" in messages and "export const stateLabels" not in messages
    assert "antes de encerrar" not in messages and "Não foi possível encerrar" not in drawers


def test_live_hud_shows_translated_mission_state():
    state = (HIVE_STATIC / "mission-state.js").read_text(encoding="utf-8")
    assert "import {describeCode,stateLabel} from './messages.js';" in state
    assert "${stateLabel(state)} · ciclo" in state
    assert "${state} · ciclo" not in state
    assert "state.hud" in (HIVE_STATIC / "hive.js").read_text(encoding="utf-8")


def test_live_hud_and_hive_use_the_real_snapshot_without_calling_the_api():
    hive = (HIVE_STATIC / "hive.js").read_text(encoding="utf-8")
    state = (HIVE_STATIC / "mission-state.js").read_text(encoding="utf-8")
    assert "hiveApi" not in hive and "fetch(" not in hive
    assert "simulation.hudAction(" in hive and "simulation.requestUi(" in hive
    for name in ("hudAction(id)", "onUiRequest(fn)", "requestUi(target)", "export function deriveRealView", "export function missionStep"):
        assert name in state
    assert "bees_summary" in state
    for step in ("Planejamento", "Aprovação do plano", "Execução", "Verificação", "Aprovação da entrega", "Incorporação", "Concluída"):
        assert f"'{step}'" in state
    assert ".hm-cell-tag" in (HIVE_STATIC / "hive.css").read_text(encoding="utf-8")


def test_live_drawers_are_split_by_purpose_and_reuse_the_demo_components():
    modules = {name: (HIVE_STATIC / name).read_text(encoding="utf-8") for name in (
        "live-drawers.js", "live-team.js", "live-mission.js", "live-chat.js", "live-delivery.js", "live-ui.js")}
    composer = modules["live-drawers.js"]
    for name in ("createLiveTeam", "createLiveMission", "createLiveChat", "createLiveDelivery"):
        assert name in composer
    assert len(composer.splitlines()) < 40
    everything = "\n".join(modules.values())
    css = (HIVE_STATIC / "hive.css").read_text(encoding="utf-8")
    for old in ("hm-live-body", "hm-live-field", "hm-live-bee", "hm-live-details", "hm-live-verdict", "hm-live-chat", "hm-live-notice"):
        assert old not in everything and old not in css
    assert "window.confirm" not in everything and "el('pre'" not in everything
    for cls in ("hm-agent-row-wrap", "hm-tabs", "hm-agent-detail", "hm-tool", "hm-approval", "hm-plan-row", "hm-duty", "hm-connection-row", "hm-chat-log", "hm-chat-user", "hm-chat-event", "hm-chat-form", "hm-delivery", "hm-pull", "hm-worker-form", "hm-form-fields"):
        assert cls in everything, cls
    assert "from './drawers.js'" in modules["live-ui.js"]
    assert "min-height:760px" not in css


def test_live_modules_are_served_and_do_not_call_the_api_directly():
    app = Flask("test-hive-ui-live")
    app.register_blueprint(blueprint)
    client = app.test_client()
    for name in ("live-drawers.js", "live-team.js", "live-mission.js", "live-chat.js", "live-delivery.js", "live-ui.js"):
        assert client.get("/hive-ui/static/" + name).status_code == 200
        source = (HIVE_STATIC / name).read_text(encoding="utf-8")
        assert "hiveApi" not in source and "fetch(" not in source


def test_api_errors_keep_the_extra_fields_of_the_backend():
    api = (HIVE_STATIC / "api.js").read_text(encoding="utf-8")
    assert "detail:data" in api
    messages = (HIVE_STATIC / "messages.js").read_text(encoding="utf-8")
    assert "export function describeError" in messages
