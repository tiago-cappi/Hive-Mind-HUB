import json
import os
from pathlib import Path

import pytest

from HiveMind.backend.tools import WorkspaceTools
from HiveMind.backend.workspaces import WorkspaceError, checked_path, load_runtime_generation, manifest, relative_path, runtime_generation, snapshot, validate_runtime_generation


def test_snapshot_excludes_private_and_state_and_detects_changes(tmp_path):
    source = tmp_path / "project"
    state = source / "HiveMind" / "state"
    state.mkdir(parents=True)
    (source / "app.py").write_text("first", encoding="utf-8")
    (source / ".env").write_text("do-not-copy", encoding="utf-8")
    (state / "runtime.txt").write_text("do-not-recurse", encoding="utf-8")
    result = snapshot(source, state, "mission1")
    candidate = Path(result["path"])
    assert result["base"] == {"app.py": manifest(candidate)["app.py"]}
    assert (candidate / "app.py").read_text() == "first"
    assert not (candidate / ".env").exists() and not (candidate / "HiveMind" / "state").exists()
    (source / "app.py").write_text("external", encoding="utf-8")
    assert manifest(source) != result["base"]
    with pytest.raises(WorkspaceError, match="workspace_exists"):
        snapshot(source, state, "mission1")


def test_broker_restricts_read_patch_and_verifier_writes(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "file.py").write_text("original")
    (workspace / ".env").write_text("secret")
    (tmp_path / "outside.txt").write_text("outside")
    tools = WorkspaceTools(workspace, ["file.py"], [["python", "-m", "pytest"]])
    read = tools.broker.dispatch("read", {"path": "file.py"})
    assert read["content"] == "original"
    for path in ("../outside.txt", str(tmp_path / "outside.txt"), ".env"):
        with pytest.raises(WorkspaceError):
            tools.broker.dispatch("read", {"path": path})
    with pytest.raises(WorkspaceError, match="write_not_approved"):
        tools.broker.dispatch("patch", {"path": "other.py", "content": "new", "expected_sha256": None})
    tools.broker.dispatch("patch", {"path": "file.py", "content": "changed", "expected_sha256": read["sha256"]})
    assert (workspace / "file.py").read_text() == "changed"
    with pytest.raises(WorkspaceError, match="stale_patch"):
        tools.broker.dispatch("patch", {"path": "file.py", "content": "stale", "expected_sha256": read["sha256"]})
    verifier = WorkspaceTools(workspace, [], [])
    with pytest.raises(WorkspaceError, match="write_not_approved"):
        verifier.broker.dispatch("patch", {"path": "file.py", "content": "bad", "expected_sha256": None})
    with pytest.raises(WorkspaceError, match="restricted_runner_unavailable"):
        tools.broker.dispatch("checks", {"argv": ["python", "-m", "pytest"]})
    assert (tmp_path / "outside.txt").read_text() == "outside"


def test_shared_or_linked_files_are_not_followed(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = tmp_path / "original.txt"
    source.write_text("private")
    link = workspace / "linked.txt"
    try:
        os.link(source, link)
    except OSError:
        pytest.skip("fixture hardlinks unavailable")
    with pytest.raises(WorkspaceError, match="link_or_shared_file"):
        checked_path(workspace, "linked.txt")
    with pytest.raises(WorkspaceError, match="link_or_shared_file"):
        manifest(workspace)


@pytest.mark.parametrize("path", ["file.py:secret", "CON.txt", "dir/aux", "file.", "file ", "\\rooted"])
def test_windows_aliases_and_devices_are_rejected(path):
    with pytest.raises(WorkspaceError):
        relative_path(path)


def test_runtime_generation_is_hash_addressed_and_preserves_old_code(tmp_path):
    project = tmp_path / "project"
    backend = project / "HiveMind" / "backend"
    runtime = project / "hub_runtime"
    backend.mkdir(parents=True)
    runtime.mkdir()
    (project / "HiveMind" / "__init__.py").write_text("")
    (backend / "__init__.py").write_text("")
    (backend / "service.py").write_text("class HiveService: version = 1")
    for name in ("__init__.py", "assistant.py", "paths.py"):
        (runtime / name).write_text("")
    generations = tmp_path / "generations"
    generations.mkdir()
    first = runtime_generation(project, generations)
    loaded, first_service = load_runtime_generation(project, generations)
    assert first_service.version == 1 and loaded["hash"] == first["hash"]
    (backend / "service.py").write_text("class HiveService: version = 2")
    second, second_service = load_runtime_generation(project, generations)
    assert first["hash"] != second["hash"]
    assert first_service.version == 1 and second_service.version == 2
    assert (Path(first["path"]) / "HiveMind" / "backend" / "service.py").read_text() == "class HiveService: version = 1"
    cache = Path(first["path"]) / "HiveMind" / "backend" / "__pycache__"
    cache.mkdir()
    (cache / "service.pyc").write_bytes(b"unverified code")
    with pytest.raises(WorkspaceError, match="runtime_generation_changed"):
        validate_runtime_generation(first)


def test_git_project_uses_worktree_and_preserves_dirty_files(tmp_path):
    import shutil
    import subprocess
    git = shutil.which("git")
    if git is None:
        pytest.skip("git unavailable")
    source = tmp_path / "project"
    source.mkdir()
    state = tmp_path / "workspaces"
    state.mkdir()
    def command(*args):
        return subprocess.run([git, "-C", str(source), *args], capture_output=True, check=True)
    command("init")
    (source / "app.py").write_text("tracked")
    command("add", "app.py")
    command("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
    (source / "app.py").write_text("modified")
    (source / "new.py").write_text("untracked")
    result = snapshot(source, state, "mission1")
    candidate = Path(result["path"])
    assert result["kind"] == "git" and (candidate / ".git").is_file()
    assert (candidate / "app.py").read_text() == "modified"
    assert (candidate / "new.py").read_text() == "untracked"
    assert (source / "app.py").read_text() == "modified"
    command("worktree", "remove", "--force", str(candidate))


def _program(folder, name="checktool.exe"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(b"")
    return folder


def test_check_program_read_roots_grant_only_the_install_and_venv_home(tmp_path, monkeypatch):
    # B4 de 24-25/10/2026: Python instalado por usuário fica fora de :minimal e não iniciava.
    from HiveMind.backend.tools import program_read_roots
    root, scratch = tmp_path / "candidate", tmp_path / "scratch"
    root.mkdir(); scratch.mkdir()
    home = tmp_path / "Users" / "me"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATHEXT", ".EXE")
    def on_path(folder):
        monkeypatch.setenv("PATH", str(folder))
        return program_read_roots("checktool", root, scratch)
    install = _program(home / "AppData" / "Local" / "Programs" / "Python" / "Python313", "python.exe")
    _program(install)
    assert on_path(install) == (install.resolve(),)
    assert program_read_roots("missing", root, scratch) == ()
    venv = tmp_path / "tools" / "venv"
    scripts = _program(venv / "Scripts")
    config = venv / "pyvenv.cfg"
    config.write_text(f"home = {install}\nversion = 3.13\n", encoding="utf-8")
    assert on_path(scripts) == (scripts.resolve(), venv.resolve(), install.resolve())
    # Só nome puro e só pasta do PATH: caminho, relativo ou pasta atual não valem (verificação de 25/10/2026).
    for named in (str(scripts / "checktool.exe"), "Scripts\\checktool.exe", "venv/Scripts/checktool", "C:checktool"):
        assert program_read_roots(named, root, scratch) == ()
    _program(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "nowhere"))
    assert program_read_roots("checktool", root, scratch) == ()
    # Um homônimo no cwd não deve ocultar a versão autorizada no PATH.
    monkeypatch.setenv("PATH", str(scripts))
    from HiveMind.backend.tools import program_path
    assert program_path("checktool") == (scripts / "checktool.exe").resolve()
    monkeypatch.setenv("PATH", str(tmp_path))
    assert program_path("checktool") is None
    # home do pyvenv.cfg: absoluta, com python.exe e concedível.
    _program(tmp_path / "rel" / "Python313", "python.exe")
    tools_py = _program(home / "Tools" / "Py", "python.exe")
    for line in (f"home = {install.parent / 'missing'}", "home = rel\\Python313",
                 f"home = {_program(home / 'Desktop', 'python.exe')}", f"home = {_program(root / 'py', 'python.exe')}"):
        config.write_text(line + "\n", encoding="utf-8")
        assert on_path(scripts) == (scripts.resolve(), venv.resolve()), line
    config.write_text(f"home = {tools_py}\n", encoding="utf-8")
    assert on_path(scripts) == (scripts.resolve(), venv.resolve(), tools_py.resolve())
    # venv barrado (filho direto da pasta do usuário): só a pasta do executável, sem seguir o pyvenv.cfg.
    home_venv = home / ".venv"
    _program(home_venv / "Scripts")
    (home_venv / "pyvenv.cfg").write_text(f"home = {install}\n", encoding="utf-8")
    assert on_path(home_venv / "Scripts") == ((home_venv / "Scripts").resolve(),)
    inner = root / ".venv"
    _program(inner / "Scripts")
    (inner / "pyvenv.cfg").write_text(f"home = {tools_py}\n", encoding="utf-8")
    assert on_path(inner / "Scripts") == ()
    for unsafe in (root / "bin", scratch / "bin", home, home / "Documents", home / "AppData" / "Local",
                   home / "AppData" / "Roaming", home / "AppData" / "Local" / "Programs", home / "OneDrive" / "Tools",
                   tmp_path / "Users" / "other" / "Tools", tmp_path / "Users" / "Public" / "Tools"):
        assert on_path(_program(unsafe)) == (), unsafe


def test_check_profile_must_list_exactly_the_granted_reads(tmp_path):
    from HiveMind.backend.tools import RestrictedCheckRunner
    root, scratch, extra = tmp_path / "candidate", tmp_path / "scratch", tmp_path / "Python313"
    filesystem = {":root": "deny", ":minimal": "read", ":tmpdir": "deny", ":slash_tmp": "deny",
                  str(root): "read", str(scratch): "write"}
    def config(entries):
        return {"permissions": {"hive-verify": {"extends": ":read-only", "filesystem": entries,
                                                "network": {"enabled": False}}},
                "default_permissions": "hive-verify", "features": {"prefer_mxc": True},
                "windows": {"sandbox": "unelevated"}}
    verified = RestrictedCheckRunner._verified_profile
    assert verified(config(filesystem), root, scratch)
    assert not verified(config(filesystem), root, scratch, (extra,))
    assert verified(config({**filesystem, str(extra): "read"}), root, scratch, (extra,))
    assert not verified(config({**filesystem, str(extra): "write"}), root, scratch, (extra,))
    assert not verified(config({**filesystem, str(extra): "read"}), root, scratch)


def test_check_runner_sends_time_limit_extra_reads_and_pytest_cache_in_scratch(tmp_path, monkeypatch):
    # B4 de 25/10/2026: sem teto o check travava para sempre; o cache do pytest no candidato travava o Python.
    import HiveMind.backend.adapters.base as base
    import HiveMind.backend.tools as tools
    root, scratch, extra = tmp_path / "candidate", tmp_path / "scratch area", tmp_path / "Python313"
    root.mkdir(); scratch.mkdir()
    seen = {}
    class FakeRpc:
        _METHODS = frozenset()
        def __init__(self, command, timeout=20, experimental=False):
            seen["command"], self.timeout = list(command), timeout
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def request(self, method, params):
            if method == "config/read":
                return {"config": {}}
            seen["rpc_timeout"], seen["params"] = self.timeout, params
            return {"exitCode": 0, "stdout": "ok", "stderr": ""}
    monkeypatch.setattr(base, "DiscoveryRpc", FakeRpc)
    monkeypatch.setattr(base, "run_status", lambda *args: "codex-cli 0.160.0\n")
    monkeypatch.setattr(tools, "program_read_roots", lambda program, *args: (extra,) if program == "python" else ())
    monkeypatch.setattr(tools, "program_path", lambda program: extra / "python.exe" if program == "python" else None)
    monkeypatch.setattr(tools.RestrictedCheckRunner, "_verified_profile",
                        staticmethod(lambda config, r, s, extra_reads=(): seen.setdefault("verified", extra_reads) == (extra,)))
    runner = tools.RestrictedCheckRunner(("C:/node/node.exe", "codex.js"), scratch, timeout=7)
    assert runner.run(root, ("python", "-m", "pytest")) == {"exit_code": 0, "stdout": "ok", "stderr": ""}
    params = seen["params"]
    assert params["timeoutMs"] == 7000 and "disableTimeout" not in params and seen["rpc_timeout"] == 67
    profile = next(item for item in seen["command"] if item.startswith("permissions.hive-verify="))
    assert json.dumps(str(extra)) + '="read"' in profile
    assert params["command"][4:] == [str(extra / "python.exe"), "-m", "pytest"]
    wrapper = params["command"][2]
    addopts = json.dumps('-o "cache_dir=' + (scratch.resolve() / ".pytest_cache").as_posix() + '"')
    assert "PYTEST_ADDOPTS:" + addopts in wrapper
