"""Hash-addressed delivery with conservative, journaled application."""

import json
import os
from pathlib import Path
import shutil

from .missions import _require
from .store import Conflict, canonical, digest
from .workspaces import WorkspaceError, checked_path, checked_root, file_digest, manifest, relative_path


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


class Delivery:
    def __init__(self, store, journal_root):
        self.store = store
        self.journal_root = checked_root(journal_root)

    def prepare(self, mission_id, key, revision, source, candidate, base):
        source, candidate = checked_root(source), checked_root(candidate)
        current = manifest(candidate)
        if not isinstance(base, dict) or any(not _hash(value) for value in base.values()):
            raise WorkspaceError("invalid_base_manifest")
        for name in base:
            relative_path(name)
        changes = sorted(name for name in set(base) | set(current) if base.get(name) != current.get(name))
        candidate_hash = digest(current)
        def change(connection, mission):
            _require(mission, "awaiting_delivery_approval")
            data = mission["data"]
            bound = data.get("workspace") or {}
            if (bound.get("source") != str(source) or bound.get("path") != str(candidate)
                    or bound.get("base") != base or bound.get("base_hash") != digest(base)
                    or bound.get("plan_hash") != data.get("plan_hash")):
                raise Conflict("workspace_mismatch")
            if data.get("candidate_hash") != candidate_hash or (data.get("verdict") or {}).get("passed") is not True:
                raise Conflict("stale_candidate")
            allowed = {relative_path(path).as_posix() for task in data["plan"]["tasks"] for path in task["files"]}
            if not set(changes) <= allowed:
                raise Conflict("changes_outside_plan")
            if Path(data["plan"]["project"]["path"]).resolve(strict=True) != source:
                raise Conflict("project_mismatch")
            package = {"source": str(source), "candidate": str(candidate), "base": base,
                       "candidate_manifest": current, "candidate_hash": candidate_hash, "changes": changes,
                       "plan_hash": data["approved_plan_hash"]}
            package_hash = digest(package)
            data.update({"delivery": package, "delivery_hash": package_hash, "approved_delivery_hash": None})
            return {"delivery_hash": package_hash, "candidate_hash": candidate_hash, "changes": changes}
        return self.store.mutate(mission_id, key, revision, "delivery_prepared",
                                 {"candidate_hash": candidate_hash, "base_hash": digest(base)}, change)

    @staticmethod
    def _save_journal(path, journal):
        temporary = path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(canonical(journal))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    @staticmethod
    def _same_volume(first, second):
        if os.name != "nt":
            raise Conflict("delivery_platform_unsupported")
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        get_volume = kernel.GetVolumePathNameW
        get_volume.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        get_volume.restype = ctypes.c_int
        roots = []
        for path in (first, second):
            output = ctypes.create_unicode_buffer(32768)
            if not get_volume(str(path), output, len(output)):
                raise ctypes.WinError(ctypes.get_last_error())
            roots.append(os.path.normcase(output.value))
        return roots[0] == roots[1]

    @staticmethod
    def _replace(target, staged, captured):
        """Windows captures the actually replaced file as the backup in one operation."""
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        replace = kernel.ReplaceFileW
        replace.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p,
                            ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        replace.restype = ctypes.c_int
        if not replace(str(target), str(staged), str(captured), 0, None, None):
            raise ctypes.WinError(ctypes.get_last_error())

    @staticmethod
    def _move(source, destination):
        """Move on the same volume without replacing a destination created concurrently."""
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        move = kernel.MoveFileExW
        move.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        move.restype = ctypes.c_int
        if not move(str(source), str(destination), 0):
            raise ctypes.WinError(ctypes.get_last_error())

    @staticmethod
    def _copy_exclusive(source, destination, expected):
        if os.path.lexists(destination):
            if not destination.is_file() or file_digest(destination) != expected:
                raise Conflict("delivery_artifact_changed")
            return
        with open(source, "rb") as old, open(destination, "xb") as new:
            shutil.copyfileobj(old, new)
            new.flush()
            os.fsync(new.fileno())
        if file_digest(destination) != expected:
            raise Conflict("delivery_artifact_changed")

    def apply(self, mission_id, key, revision, delivery_hash):
        mission = self.store.get(mission_id)
        if mission["state"] == "completed" and mission["data"].get("approved_delivery_hash") == delivery_hash:
            return mission
        _require(mission, "delivery_approved")
        data = mission["data"]
        if (not _hash(delivery_hash) or data.get("approved_delivery_hash") != delivery_hash
                or data.get("delivery_hash") != delivery_hash or digest(data.get("delivery")) != delivery_hash
                or (data.get("verdict") or {}).get("passed") is not True):
            raise Conflict("delivery_not_approved")
        if not self._same_volume(checked_root(data["delivery"]["source"]), self.journal_root):
            raise Conflict("delivery_same_volume_required")
        def begin(connection, record):
            _require(record, "delivery_approved")
            data = record["data"]
            if (not _hash(delivery_hash) or data.get("approved_delivery_hash") != delivery_hash
                    or data.get("delivery_hash") != delivery_hash or digest(data.get("delivery")) != delivery_hash
                    or (data.get("verdict") or {}).get("passed") is not True):
                raise Conflict("delivery_not_approved")
            record["state"] = "applying"
            return {"delivery_hash": delivery_hash}
        started = self.store.mutate(mission_id, key, revision, "delivery_applying", {"delivery_hash": delivery_hash}, begin)
        package = started["data"]["delivery"]
        directory = self.journal_root / ("delivery-" + digest([mission_id, delivery_hash]))
        journal = {"delivery_hash": delivery_hash, "source": package["source"], "items": [], "complete": False}
        journal_path = directory / "journal.json"
        try:
            if os.path.lexists(directory):
                raise Conflict("delivery_recovery_required")
            directory.mkdir()
            source, candidate = checked_root(package["source"]), checked_root(package["candidate"])
            for index, name in enumerate(package["changes"]):
                journal["items"].append({"path": name, "old": package["base"].get(name),
                    "new": package["candidate_manifest"].get(name), "original": f"{index}.original",
                    "staged": f"{index}.new", "captured": f"{index}.captured",
                    "restore": f"{index}.restore", "rollback_capture": f"{index}.rollback",
                    "attempted": False, "rollback_attempted": False})
            self._save_journal(journal_path, journal)
            if not self._same_volume(source, directory):
                raise Conflict("delivery_same_volume_required")
            if manifest(source) != package["base"]:
                raise Conflict("source_changed")
            if manifest(candidate) != package["candidate_manifest"]:
                raise Conflict("candidate_changed")
            for item in journal["items"]:
                if item["old"]:
                    self._copy_exclusive(checked_path(source, item["path"]), directory / item["original"], item["old"])
                if item["new"]:
                    self._copy_exclusive(checked_path(candidate, item["path"]), directory / item["staged"], item["new"])
            expected = dict(package["base"])
            for item in journal["items"]:
                if manifest(source) != expected:
                    raise Conflict("source_changed")
                target = checked_path(source, item["path"], allow_missing=True)
                if not target.parent.is_dir():
                    raise WorkspaceError("missing_delivery_parent")
                staged, captured = directory / item["staged"], directory / item["captured"]
                item["attempted"] = True
                self._save_journal(journal_path, journal)
                if item["old"] and item["new"]:
                    self._replace(target, staged, captured)
                elif item["old"]:
                    self._move(target, captured)
                else:
                    self._move(staged, target)
                if item["old"] and (not captured.is_file() or file_digest(captured) != item["old"]):
                    raise Conflict("source_changed_during_apply")
                if item["new"]:
                    expected[item["path"]] = item["new"]
                else:
                    expected.pop(item["path"], None)
            if manifest(source) != expected:
                raise Conflict("source_changed")
            journal["complete"] = True
            self._save_journal(journal_path, journal)
            def finish(connection, record):
                _require(record, "applying")
                record["state"] = "completed"
                connection.execute("UPDATE bees SET active=0 WHERE mission_id=? AND temporary=1", (mission_id,))
                return {"delivery_hash": delivery_hash}
            return self.store.mutate(mission_id, "finish-" + digest([key]), started["revision"],
                                     "delivery_completed", {"delivery_hash": delivery_hash}, finish)
        except BaseException:
            rollback_ok = self._rollback(directory, journal)
            current = self.store.get(mission_id)
            if current["state"] == "applying":
                def fail(connection, record):
                    _require(record, "applying")
                    record["state"] = "recovery_required"
                    record["data"]["approved_delivery_hash"] = None
                    return {"rollback_complete": rollback_ok}
                self.store.mutate(mission_id, "fail-" + digest([key]), current["revision"],
                                  "delivery_interrupted", {"delivery_hash": delivery_hash}, fail)
            raise

    def recover(self, mission_id, key, revision):
        """Reconcile only a verified journal; ambiguous files remain untouched and retained."""
        mission = self.store.get(mission_id)
        _require(mission, "recovery_required")
        package = mission["data"].get("delivery")
        package_hash = mission["data"].get("delivery_hash")
        if not isinstance(package, dict) or not _hash(package_hash) or digest(package) != package_hash:
            raise Conflict("delivery_journal_unverified")
        directory = self.journal_root / ("delivery-" + digest([mission_id, package_hash]))
        try:
            checked_root(directory)
            path = checked_path(directory, "journal.json")
            if path.stat().st_size > 10 * 1024 * 1024:
                raise Conflict("delivery_journal_unverified")
            journal = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, WorkspaceError) as exc:
            raise Conflict("delivery_journal_unverified") from exc
        if not isinstance(journal, dict):
            raise Conflict("delivery_journal_unverified")
        items = journal.get("items")
        if (journal.get("delivery_hash") != package_hash or journal.get("source") != package["source"]
                or not isinstance(items, list) or len(items) != len(package["changes"])):
            raise Conflict("delivery_journal_unverified")
        for index, (item, name) in enumerate(zip(items, package["changes"])):
            expected_names = {"original": f"{index}.original", "staged": f"{index}.new",
                              "captured": f"{index}.captured", "restore": f"{index}.restore",
                              "rollback_capture": f"{index}.rollback"}
            if (not isinstance(item, dict) or item.get("path") != name
                    or item.get("old") != package["base"].get(name)
                    or item.get("new") != package["candidate_manifest"].get(name)
                    or any(item.get(key) != value for key, value in expected_names.items())
                    or type(item.get("attempted")) is not bool
                    or type(item.get("rollback_attempted")) is not bool):
                raise Conflict("delivery_journal_unverified")
        if not self._rollback(directory, journal):
            raise Conflict("delivery_recovery_ambiguous")
        source_stale = manifest(checked_root(package["source"])) != package["base"]
        def finish(connection, record):
            _require(record, "recovery_required")
            if record["data"].get("delivery_hash") != package_hash:
                raise Conflict("stale_delivery")
            record["state"] = "awaiting_user"
            record["data"]["approved_delivery_hash"] = None
            if source_stale:
                workspace = record["data"].get("workspace") or {}
                record["data"]["reconciliation_required"] = {
                    "delivery_hash": package_hash, "workspace": workspace.get("path"),
                    "base_hash": workspace.get("base_hash"),
                }
            return {"delivery_hash": package_hash, "rollback_complete": True}
        return self.store.mutate(mission_id, key, revision, "delivery_recovered", {"delivery_hash": package_hash}, finish)

    def _rollback(self, directory, journal):
        try:
            source = checked_root(journal["source"])
            if not directory.is_dir():
                return False
            if not any(item["attempted"] for item in journal["items"]):
                return True
            if not self._same_volume(source, directory):
                return False
            for item in reversed(journal["items"]):
                if not item["attempted"]:
                    continue
                target = checked_path(source, item["path"], allow_missing=True)
                captured = checked_path(directory, item["captured"], allow_missing=True)
                rollback_capture = checked_path(directory, item["rollback_capture"], allow_missing=True)
                current = file_digest(target) if target.is_file() else None
                capture_hash = file_digest(captured) if captured.is_file() else None
                rollback_hash = file_digest(rollback_capture) if rollback_capture.is_file() else None
                old, new = item["old"], item["new"]
                if capture_hash is not None and capture_hash != old:
                    return False
                if rollback_hash is not None and rollback_hash != new:
                    return False
                if current == old:
                    continue
                if old is None:
                    if current is None:
                        continue
                    if current != new or rollback_hash is not None:
                        return False
                    item["rollback_attempted"] = True
                    self._save_journal(directory / "journal.json", journal)
                    self._move(target, rollback_capture)
                    if file_digest(rollback_capture) != new:
                        return False
                else:
                    if capture_hash != old or (current != new and not (new is None and current is None)):
                        return False
                    restore = checked_path(directory, item["restore"], allow_missing=True)
                    self._copy_exclusive(captured, restore, old)
                    item["rollback_attempted"] = True
                    self._save_journal(directory / "journal.json", journal)
                    if new is None:
                        self._move(restore, target)
                    else:
                        if rollback_hash is not None:
                            return False
                        self._replace(target, restore, rollback_capture)
                        if file_digest(rollback_capture) != new:
                            return False
                if (file_digest(target) if target.is_file() else None) != old:
                    return False
            return True
        except (OSError, WorkspaceError, Conflict):
            return False
