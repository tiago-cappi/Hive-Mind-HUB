"""The model-visible broker surface for an approved isolated workspace."""

import os
import json
from pathlib import Path
import shutil
import tempfile
import threading

from .capabilities import ToolBroker
from .workspaces import WorkspaceError, checked_path, checked_root, file_digest, path_key, relative_path


_WORKSPACE_LOCKS = {}
_LOCKS_LOCK = threading.Lock()


class WorkspaceTools:
    def __init__(self, root, editable_paths, approved_checks, check_runner=None):
        self.root = checked_root(root)
        self.editable = {path_key(path): relative_path(path).as_posix() for path in editable_paths}
        with _LOCKS_LOCK:
            self._lock = _WORKSPACE_LOCKS.setdefault(os.path.normcase(str(self.root)), threading.RLock())
        self.approved_checks = tuple(tuple(check) for check in approved_checks)
        self.check_runner = check_runner
        self.broker = ToolBroker({"read": self.read, "patch": self.patch, "checks": self.checks})

    def read(self, arguments):
        if set(arguments) != {"path"}:
            raise WorkspaceError("invalid_read")
        with self._lock:
            path = checked_path(self.root, arguments["path"])
            if not path.is_file() or path.stat().st_size > 1024 * 1024:
                raise WorkspaceError("invalid_read_target")
            return {"content": path.read_text(encoding="utf-8"), "sha256": file_digest(path)}

    def patch(self, arguments):
        if set(arguments) != {"path", "content", "expected_sha256"} or not (isinstance(arguments["content"], str) or arguments["content"] is None):
            raise WorkspaceError("invalid_patch")
        relative = self.editable.get(path_key(arguments["path"]))
        if relative is None or (arguments["content"] is not None and len(arguments["content"].encode("utf-8")) > 1024 * 1024):
            raise WorkspaceError("write_not_approved")
        with self._lock:
            target = checked_path(self.root, relative, allow_missing=True)
            parent = target.parent
            if not parent.is_dir():
                raise WorkspaceError("missing_parent")
            current = file_digest(target) if target.is_file() else None
            if current != arguments["expected_sha256"]:
                raise WorkspaceError("stale_patch")
            if arguments["content"] is None:
                if current is None:
                    raise WorkspaceError("missing_path")
                target.unlink()
                return {"removed": relative}
            descriptor, temp_name = tempfile.mkstemp(prefix=".hive-write-", dir=parent)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(arguments["content"].encode("utf-8"))
                    stream.flush()
                    os.fsync(stream.fileno())
                checked_path(self.root, relative, allow_missing=True)
                if (file_digest(target) if target.is_file() else None) != current:
                    raise WorkspaceError("stale_patch")
                os.replace(temp_name, target)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        return {"written": relative}

    def checks(self, arguments):
        if set(arguments) != {"argv"} or not isinstance(arguments["argv"], list):
            raise WorkspaceError("invalid_check")
        argv = tuple(arguments["argv"])
        if argv not in self.approved_checks:
            raise WorkspaceError("check_not_approved")
        if self.check_runner is None:
            raise WorkspaceError("restricted_runner_unavailable")
        return self.check_runner.run(self.root, argv)


def program_path(program):
    """Resolved executable of a bare program name, found in a PATH folder (never the current one)."""
    if not isinstance(program, str) or not program or any(mark in program for mark in "/\\:"):
        return None
    key = lambda value: os.path.normcase(os.path.abspath(value))
    try:
        current = key(os.getcwd())
        for entry in os.environ.get("PATH", "").split(os.pathsep):
            if not entry.strip() or key(entry) == current:
                continue
            # A fully qualified candidate prevents Windows which() from probing cwd first.
            found = shutil.which(os.path.join(os.path.abspath(entry), program))
            if found:
                return Path(found).resolve()
        return None
    except (OSError, ValueError):
        return None


def program_read_roots(program, root, scratch):
    """Read-only folders a check program needs outside :minimal (its install and, for a venv, its home).

    Only a bare program name is resolved, through the Hub PATH. Never granted: a drive root,
    the user's home, its ancestors and direct children, the AppData roots, OneDrive folders,
    other profiles under the users folder, and folders containing or inside the candidate or
    scratch; such a program simply fails to start. A venv home is followed only when the venv
    itself was granted.
    """
    executable = program_path(program)
    if executable is None:
        return ()
    try:
        home = Path.home().resolve()
        users = home.parent
        barred = {(home / "AppData" / name).resolve() for name in ("Local", "Roaming", "LocalLow")}
        barred.add((home / "AppData" / "Local" / "Programs").resolve())
        def allowed(item):
            inside_home = home in item.parents
            return not (item.parent == item or item == home or item in home.parents or item.parent == home
                        or item in barred
                        or (inside_home and item.relative_to(home).parts[0].casefold().startswith("onedrive"))
                        or (users.parent != users and users in item.parents and not inside_home)
                        or any(item == other or item in other.parents or other in item.parents
                               for other in (root, scratch)))
        folder = executable.parent
        if not allowed(folder):
            return ()
        granted = [folder]
        venv, config = folder.parent, folder.parent / "pyvenv.cfg"
        if config.is_file() and allowed(venv):
            granted.append(venv)
            for line in config.read_text(encoding="utf-8", errors="replace").splitlines():
                key, _, value = line.partition("=")
                base = Path(value.strip())
                if (key.strip().casefold() == "home" and base.is_absolute()
                        and (base / "python.exe").is_file()):
                    base = base.resolve()
                    if allowed(base) and base not in granted:
                        granted.append(base)
    except (OSError, ValueError):
        return ()
    return tuple(granted)


class RestrictedCheckRunner:
    """Run an approved argv under a Windows MXC read-only candidate profile.

    This runner has no fallback: failed sandbox setup is a failed check. The
    service must provision scratch outside the candidate and supply a pinned
    Codex CLI; results remain untrusted until the verifier evaluates them.
    """

    def __init__(self, codex_command, scratch, timeout=600):
        self.command = tuple(codex_command)
        self.scratch = checked_root(scratch)
        self.timeout = timeout

    @staticmethod
    def _verified_profile(config, root, scratch, extra_reads=()):
        if not isinstance(config, dict):
            return False
        profile = config.get("permissions", {}).get("hive-verify")
        if not isinstance(profile, dict) or profile.get("extends") != ":read-only" or profile.get("workspace_roots") is not None:
            return False
        filesystem = profile.get("filesystem")
        network = profile.get("network")
        if not isinstance(filesystem, dict) or not isinstance(network, dict):
            return False
        normalized = {os.path.normcase(key.replace("\\\\", "\\")): value
                      for key, value in filesystem.items() if key != "glob_scan_max_depth"}
        expected = {":root": "deny", ":minimal": "read", ":tmpdir": "deny", ":slash_tmp": "deny",
                    os.path.normcase(str(root)): "read", os.path.normcase(str(scratch)): "write"}
        expected.update({os.path.normcase(str(path)): "read" for path in extra_reads})
        return (normalized == expected and filesystem.get("glob_scan_max_depth") is None
                and network.get("enabled") is False
                and all(value is None for key, value in network.items() if key != "enabled")
                and config.get("default_permissions") == "hive-verify"
                and config.get("features", {}).get("prefer_mxc") is True
                and config.get("windows", {}).get("sandbox") == "unelevated")

    def run(self, root, argv):
        from .adapters.base import DiscoveryRpc, DiscoveryError, run_status
        root = checked_root(root)
        if root == self.scratch or root in self.scratch.parents or self.scratch in root.parents:
            raise WorkspaceError("scratch_not_separate")
        if run_status(self.command, ["--version"], 20).strip() != "codex-cli 0.160.0":
            raise WorkspaceError("check_cli_unverified")
        if not isinstance(argv, tuple) or not argv or any(not isinstance(arg, str) or not arg for arg in argv):
            raise WorkspaceError("invalid_check")
        if not self.command or Path(self.command[0]).name.casefold() != "node.exe":
            raise WorkspaceError("check_launcher_unverified")
        class CheckRpc(DiscoveryRpc):
            _METHODS = DiscoveryRpc._METHODS | {"command/exec"}
        # A per-user interpreter lives outside :minimal; without reading it the program never starts.
        extra_reads = program_read_roots(argv[0], root, self.scratch)
        # Run the very file the grant was computed for; spawnSync would search the candidate first.
        executable = program_path(argv[0])
        launch = (str(executable), *argv[1:]) if executable else argv
        # Keep the whole profile in one TOML value: dotted override keys split
        # quoted path segments and corrupt the filesystem permission table.
        profile = ('{extends=":read-only",filesystem={":root"="deny",'
                   '":minimal"="read",":tmpdir"="deny",":slash_tmp"="deny",' +
                   json.dumps(str(root)) + '="read",' +
                   "".join(json.dumps(str(path)) + '="read",' for path in extra_reads) +
                   json.dumps(str(self.scratch)) + '="write"},network={enabled=false}}')
        settings = {
            "features.prefer_mxc": "true", "windows.sandbox": '"unelevated"',
            "default_permissions": '"hive-verify"',
            "permissions.hive-verify": profile,
        }
        command = list(self.command)
        for setting, value in settings.items():
            command.extend(["-c", setting + "=" + value])
        keep = {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "PATH", "SYSTEMDRIVE",
                "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "PROGRAMDATA",
                "USERPROFILE", "USERNAME", "USERDOMAIN", "USERDOMAIN_ROAMINGPROFILE",
                "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "APPDATA", "ALLUSERSPROFILE",
                "OS", "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER", "NUMBER_OF_PROCESSORS"}
        environment = {key: None for key in os.environ if key.upper() not in keep}
        environment.update({"HOME": str(self.scratch),
                            "PYTHONDONTWRITEBYTECODE": "1"})
        # MXC needs its own bootstrap environment. A fixed wrapper then creates
        # the check child with only runtime variables and a private temp/home.
        wrapper = ('const p=require("child_process"),[scratch,...args]=process.argv.slice(1);'
                   'const allow=new Set(' + json.dumps(sorted(keep)) + ');const env={};'
                   'for(const [k,v] of Object.entries(process.env))if(allow.has(k.toUpperCase()))env[k]=v;'
                   'Object.assign(env,{TEMP:scratch,TMP:scratch,HOME:scratch,PYTHONDONTWRITEBYTECODE:"1",'
                   # pytest would create .pytest_cache in the read-only candidate; on Windows
                   # tempfile.mkdtemp then retries PermissionError forever.
                   'PYTEST_ADDOPTS:' + json.dumps('-o "cache_dir=' + (self.scratch / ".pytest_cache").as_posix() + '"') + '});'
                   'const r=p.spawnSync(args[0],args.slice(1),{env,stdio:"inherit",windowsHide:true});'
                   'if(r.error)process.exit(127);process.exit(r.status===null?128:r.status)')
        try:
            # Checks own only scratch writes, so the time limit can kill one without touching the candidate.
            with CheckRpc(command, timeout=20, experimental=True) as rpc:
                config = rpc.request("config/read", {"cwd": str(root), "includeLayers": False}).get("config")
                if not self._verified_profile(config, root, self.scratch, extra_reads):
                    raise WorkspaceError("check_profile_unverified")
                rpc.timeout = self.timeout + 60
                response = rpc.request("command/exec", {"command": [self.command[0], "-e", wrapper,
                    str(self.scratch), *launch], "cwd": str(root),
                    "permissionProfile": "hive-verify", "env": environment,
                    "timeoutMs": self.timeout * 1000, "outputBytesCap": 262144})
        except DiscoveryError as exc:
            raise WorkspaceError("restricted_check_failed") from exc
        if type(response.get("exitCode")) is not int:
            raise WorkspaceError("check_result_invalid")
        return {"exit_code": response["exitCode"], "stdout": response.get("stdout", ""),
                "stderr": response.get("stderr", "")}
