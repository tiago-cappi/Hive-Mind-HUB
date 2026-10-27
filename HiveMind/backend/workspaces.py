"""Isolated snapshots and file manifests; never follow project links."""

import hashlib
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import subprocess
import tempfile

from .store import digest


class WorkspaceError(Exception):
    pass


_EXCLUDED = {".git", ".agents", ".codex", ".aws", ".venv", "venv", "node_modules", "__pycache__",
             ".pytest_cache", ".test-tmp", "vault", "logs", ".env", "auth.json", "credentials.json"}
_EXCLUDED_SUFFIXES = (".pyc", ".log", ".pem", ".key", ".p12", ".pfx")
_DEVICE = re.compile(r"^(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\..*)?$", re.IGNORECASE)


def _excluded(parts):
    lowered = tuple(part.casefold() for part in parts)
    return (any(part in _EXCLUDED or part.startswith(".env.") or part.endswith(_EXCLUDED_SUFFIXES)
                for part in lowered) or lowered[:2] == ("hivemind", "state"))


def _special(path):
    info = path.lstat()
    flags = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(flags & reparse) or (stat.S_ISREG(info.st_mode) and info.st_nlink > 1)


def _inside(root, path):
    try:
        return os.path.normcase(os.path.commonpath((str(root), str(path)))) == os.path.normcase(str(root))
    except ValueError:
        return False


def checked_root(value):
    path = Path(value).absolute()
    for item in (path, *path.parents):
        if not os.path.lexists(item) or _special(item):
            raise WorkspaceError("invalid_root")
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise WorkspaceError("invalid_root")
    return path


def project_root(value):
    """Reject the configured personal vault and its containing directories."""
    project = checked_root(value)
    configured = os.environ.get("HUB_VAULT")
    vault = Path(configured) if configured else Path.home() / "Documents" / "Obsidian Vault"
    if not vault.is_absolute():
        raise WorkspaceError("vault_configuration_invalid")
    vault = vault.resolve(strict=False)
    if _inside(project, vault) or _inside(vault, project):
        raise WorkspaceError("vault_project_forbidden")
    return project


def relative_path(value):
    if not isinstance(value, str) or not value or "\x00" in value:
        raise WorkspaceError("invalid_path")
    windows, posix = PureWindowsPath(value), PurePosixPath(value.replace("\\", "/"))
    if (windows.is_absolute() or windows.drive or windows.root or posix.is_absolute() or not posix.parts or
            any(part in {".", ".."} or part[-1] in {".", " "} or _DEVICE.fullmatch(part)
                or any(ord(char) < 32 or char in '<>:"|?*' for char in part)
                for part in posix.parts)):
        raise WorkspaceError("invalid_path")
    if _excluded(posix.parts):
        raise WorkspaceError("excluded_path")
    return Path(*posix.parts)


def path_key(value):
    """Canonical comparison key for Windows case-insensitive path aliases."""
    return relative_path(value).as_posix().casefold()


def checked_path(root, relative, *, allow_missing=False):
    root = checked_root(root)
    rel = relative_path(relative)
    current = root
    for part in rel.parts:
        current = current / part
        if os.path.lexists(current):
            if _special(current):
                raise WorkspaceError("link_or_shared_file")
        elif not allow_missing:
            raise WorkspaceError("missing_path")
    if not _inside(root, current.resolve(strict=False)):
        raise WorkspaceError("outside_root")
    return current


def file_digest(path):
    result = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def manifest(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or _special(root):
        raise WorkspaceError("invalid_root")
    files = {}
    seen = set()
    def walk(directory, parts):
        with os.scandir(directory) as entries:
            for entry in sorted(entries, key=lambda item: item.name.casefold()):
                child_parts = (*parts, entry.name)
                if _excluded(child_parts):
                    continue
                key = path_key("/".join(child_parts))
                if key in seen:
                    raise WorkspaceError("path_alias")
                seen.add(key)
                path = Path(entry.path)
                if _special(path):
                    raise WorkspaceError("link_or_shared_file")
                if entry.is_dir(follow_symlinks=False):
                    walk(path, child_parts)
                elif entry.is_file(follow_symlinks=False):
                    key = "/".join(child_parts)
                    files[key] = file_digest(path)
                else:
                    raise WorkspaceError("unsupported_file")
    walk(root, ())
    return files


def _copy_files(source, destination, base):
    for name in base:
        src = checked_path(source, name)
        dst = destination / relative_path(name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst, follow_symlinks=False)


def _git(source, args):
    executable = shutil.which("git")
    if executable is None:
        raise WorkspaceError("git_unavailable")
    env = dict(os.environ)
    for name in tuple(env):
        if name.upper() in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG_COUNT"}:
            env.pop(name, None)
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"})
    try:
        result = subprocess.run([executable, "-C", str(source), "-c", "core.hooksPath=" + os.devnull,
                                 *args], capture_output=True, text=True, encoding="utf-8",
                                errors="replace", env=env, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError("git_command_failed") from exc
    if result.returncode:
        raise WorkspaceError("git_command_failed")
    return result.stdout.strip()


def snapshot(source, state_root, workspace_id):
    """Create a source-checked snapshot or a no-checkout Git worktree."""
    if not isinstance(workspace_id, str) or not workspace_id.isalnum():
        raise WorkspaceError("invalid_workspace_id")
    source, state_root = project_root(source), checked_root(state_root)
    if _inside(source, state_root) and not _excluded(state_root.relative_to(source).parts):
        raise WorkspaceError("recursive_state_root")
    destination = state_root / workspace_id
    if os.path.lexists(destination):
        raise WorkspaceError("workspace_exists")
    base = manifest(source)
    if (source / ".git").exists():
        top = Path(_git(source, ["rev-parse", "--show-toplevel"])).resolve(strict=True)
        if top != source:
            raise WorkspaceError("git_root_required")
        commit = _git(source, ["rev-parse", "--verify", "HEAD"])
        if len(commit) not in (40, 64) or any(char not in "0123456789abcdef" for char in commit):
            raise WorkspaceError("git_head_invalid")
        created = False
        try:
            # No checkout prevents hooks, smudge filters and accidental copying of excluded files.
            _git(source, ["worktree", "add", "--detach", "--no-checkout", str(destination), commit])
            created = True
            _git(destination, ["read-tree", commit])
            _copy_files(source, destination, base)
            if manifest(source) != base or manifest(destination) != base:
                raise WorkspaceError("source_changed_during_snapshot")
            return {"path": str(destination), "base": base, "base_hash": digest(base),
                    "kind": "git", "head": commit}
        except BaseException:
            if created:
                _git(source, ["worktree", "remove", "--force", str(destination)])
            raise
    staging = Path(tempfile.mkdtemp(prefix=".hive-snapshot-", dir=state_root))
    try:
        _copy_files(source, staging, base)
        if manifest(source) != base or manifest(staging) != base:
            raise WorkspaceError("source_changed_during_snapshot")
        os.replace(staging, destination)
        return {"path": str(destination), "base": base, "base_hash": digest(base), "kind": "snapshot"}
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def runtime_generation(project, generations):
    """Copy the Hive runtime and its approved shared launcher into a hash generation."""
    project, generations = checked_root(project), checked_root(generations)
    backend = checked_path(project, "HiveMind/backend")
    if not backend.is_dir():
        raise WorkspaceError("runtime_unavailable")
    names = []
    for current, directories, files in os.walk(backend, followlinks=False):
        directories[:] = [name for name in directories if name != "__pycache__"]
        for directory in directories:
            if _special(Path(current) / directory):
                raise WorkspaceError("link_or_shared_file")
        for name in files:
            path = Path(current) / name
            if path.suffix.casefold() not in {".py", ".md", ".json"}:
                continue
            relative = path.relative_to(project).as_posix()
            checked_path(project, relative)
            names.append(relative)
    names.extend(["HiveMind/__init__.py", "hub_runtime/__init__.py", "hub_runtime/assistant.py", "hub_runtime/paths.py"])
    base = {name: file_digest(checked_path(project, name)) for name in sorted(set(names))}
    generation_id = digest(base)
    destination = generations / generation_id
    if destination.exists():
        generation = {"path": str(destination), "hash": generation_id, "manifest": base}
        validate_runtime_generation(generation)
        return generation
    staging = Path(tempfile.mkdtemp(prefix=".hive-runtime-", dir=generations))
    try:
        _copy_files(project, staging, base)
        if any(file_digest(checked_path(project, name)) != value for name, value in base.items()):
            raise WorkspaceError("runtime_changed_during_generation")
        if manifest(staging) != base:
            raise WorkspaceError("runtime_changed_during_generation")
        os.replace(staging, destination)
        return {"path": str(destination), "hash": generation_id, "manifest": base}
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def validate_runtime_generation(generation):
    if (not isinstance(generation, dict) or not isinstance(generation.get("manifest"), dict)
            or not isinstance(generation.get("path"), str)
            or digest(generation["manifest"]) != generation.get("hash")):
        raise WorkspaceError("runtime_generation_changed")
    root = checked_root(generation["path"])
    expected = set(generation["manifest"])
    expected_dirs = {Path(name).parent.as_posix() for name in expected}
    expected_dirs |= {parent.as_posix() for name in expected for parent in Path(name).parents}
    observed = set()
    for current, directories, files in os.walk(root, followlinks=False):
        for name in directories:
            path = Path(current) / name
            if _special(path) or path.relative_to(root).as_posix() not in expected_dirs:
                raise WorkspaceError("runtime_generation_changed")
        for name in files:
            path = Path(current) / name
            if _special(path):
                raise WorkspaceError("runtime_generation_changed")
            observed.add(path.relative_to(root).as_posix())
    if observed != expected or manifest(root) != generation["manifest"]:
        raise WorkspaceError("runtime_generation_changed")


def load_runtime_generation(project, generations):
    """Load a generation as a private package without importing mutable source."""
    import importlib
    import importlib.abc
    import importlib.machinery
    import importlib.util
    import sys
    generation = runtime_generation(project, generations)
    backend = Path(generation["path"]) / "HiveMind" / "backend"
    name = "_hivemind_runtime_" + generation["hash"]
    if name not in sys.modules:
        class SourceOnly(importlib.machinery.SourceFileLoader):
            def get_code(self, fullname):
                return self.source_to_code(self.get_data(self.path), self.path)
        class GenerationFinder(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path, target=None):
                if not fullname.startswith(name + "."):
                    return None
                item = backend.joinpath(*fullname[len(name) + 1:].split("."))
                package_file = item / "__init__.py"
                source = package_file if package_file.is_file() else item.with_suffix(".py")
                if not source.is_file():
                    raise ModuleNotFoundError(fullname)
                return importlib.util.spec_from_file_location(
                    fullname, source, loader=SourceOnly(fullname, str(source)),
                    submodule_search_locations=[str(item)] if source == package_file else None)
        sys.meta_path.insert(0, GenerationFinder())
        spec = importlib.util.spec_from_file_location(name, backend / "__init__.py",
                                                       loader=SourceOnly(name, str(backend / "__init__.py")),
                                                       submodule_search_locations=[str(backend)])
        if spec is None or spec.loader is None:
            raise WorkspaceError("runtime_unavailable")
        package = importlib.util.module_from_spec(spec)
        sys.modules[name] = package
        try:
            spec.loader.exec_module(package)
        except BaseException:
            sys.modules.pop(name, None)
            raise
    return generation, importlib.import_module(name + ".service").HiveService
