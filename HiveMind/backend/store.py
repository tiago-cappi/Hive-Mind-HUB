"""SQLite state, atomic events, revision checks and command deduplication."""

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from .bees import InvalidProfile, incomplete, normalize, profile_gaps


class Conflict(Exception):
    """The command does not match the current revision or a prior request."""


class NotFound(Exception):
    """The requested record does not exist."""


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.session() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS missions (
                    id TEXT PRIMARY KEY, state TEXT NOT NULL, revision INTEGER NOT NULL,
                    cycle INTEGER NOT NULL, cycle_limit INTEGER NOT NULL, data TEXT NOT NULL,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, mission_id TEXT NOT NULL,
                    kind TEXT NOT NULL, data TEXT NOT NULL, created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS event_mission_seq ON events(mission_id, seq);
                CREATE TABLE IF NOT EXISTS commands (
                    mission_id TEXT NOT NULL, key TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    result TEXT NOT NULL, PRIMARY KEY(mission_id, key)
                );
                CREATE TABLE IF NOT EXISTS bees (
                    mission_id TEXT NOT NULL, id TEXT NOT NULL, role TEXT NOT NULL,
                    temporary INTEGER NOT NULL, active INTEGER NOT NULL, data TEXT NOT NULL,
                    PRIMARY KEY(mission_id, id)
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, bee_id TEXT NOT NULL,
                    role TEXT NOT NULL, state TEXT NOT NULL, data TEXT NOT NULL,
                    FOREIGN KEY(mission_id) REFERENCES missions(id)
                );
                CREATE INDEX IF NOT EXISTS jobs_mission ON jobs(mission_id, state);
                CREATE TABLE IF NOT EXISTS leases (
                    mission_id TEXT PRIMARY KEY, owner TEXT NOT NULL, expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK(id=1), worker_limit INTEGER NOT NULL, revision INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO settings VALUES(1,2,0);
                CREATE TABLE IF NOT EXISTS roster_settings (
                    id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL, revision INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO roster_settings VALUES(1,'[]',0);
            """)

    def connect(self):
        connection = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def session(self):
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _decode(row):
        if row is None:
            raise NotFound("mission_not_found")
        result = dict(row)
        result["data"] = json.loads(result["data"])
        return result

    def get(self, mission_id):
        with self.session() as connection:
            return self._decode(connection.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone())

    def command_result(self, mission_id, key):
        """Return the saved result of a deduplicated command, or None."""
        with self.session() as connection:
            row = connection.execute("SELECT result FROM commands WHERE mission_id=? AND key=?",
                                     (mission_id, key)).fetchone()
        return json.loads(row["result"]) if row else None

    def events(self, mission_id, after=0, limit=200):
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("invalid event cursor")
        with self.session() as connection:
            rows = connection.execute("SELECT seq, kind, data, created_at FROM events "
                                      "WHERE mission_id=? AND seq>? ORDER BY seq LIMIT ?",
                                      (mission_id, after, limit)).fetchall()
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]

    def bee_events(self, mission_id):
        """Every tool and progress event of the mission, without the paging limit of `events`."""
        with self.session() as connection:
            rows = connection.execute("SELECT seq, kind, data FROM events WHERE mission_id=? "
                                      "AND kind IN ('tool_completed','bee_progress') ORDER BY seq",
                                      (mission_id,)).fetchall()
        return [{"seq": row["seq"], "kind": row["kind"], "data": json.loads(row["data"])} for row in rows]

    def roster(self, mission_id):
        with self.session() as connection:
            rows = connection.execute("SELECT id, role, temporary, active, data FROM bees "
                                      "WHERE mission_id=? ORDER BY id", (mission_id,)).fetchall()
        return [{**dict(row), "temporary": bool(row["temporary"]), "active": bool(row["active"]),
                 "data": json.loads(row["data"])} for row in rows]

    def settings(self):
        with self.session() as connection:
            return dict(connection.execute("SELECT worker_limit,revision FROM settings WHERE id=1").fetchone())

    def configured_bees(self):
        with self.session() as connection:
            row = connection.execute("SELECT data,revision FROM roster_settings WHERE id=1").fetchone()
        bees = json.loads(row["data"])
        return {"bees": bees, "revision": row["revision"], "incomplete": incomplete(bees)}

    def set_configured_bees(self, bees, key, revision):
        from .adapters.base import safe_name
        self._key(key)
        if (not isinstance(bees, list) or type(revision) is not int or revision < 0 or any(
                not isinstance(bee, dict) or not safe_name(bee.get("id")) or
                bee.get("role") not in {"queen", "worker", "subagent", "verifier"} or
                bee.get("provider") not in {"codex", "claude"} or not safe_name(bee.get("model")) or
                not safe_name(bee.get("effort")) or bee.get("temporary") is not False for bee in bees)
                or len({bee["id"] for bee in bees}) != len(bees)
                or sum(bee["role"] == "queen" for bee in bees) != 1
                or sum(bee["role"] == "verifier" for bee in bees) != 1
                or not any(bee["role"] == "worker" for bee in bees)):
            raise ValueError("invalid roster")
        fingerprint = digest(["roster", bees, revision])
        with self.transaction() as connection:
            prior = connection.execute("SELECT fingerprint,result FROM commands WHERE mission_id=? AND key=?",
                                       ("__roster__", key)).fetchone()
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Conflict("idempotency_key_reused")
                return json.loads(prior["result"])
            current = connection.execute("SELECT data,revision FROM roster_settings WHERE id=1").fetchone()
            if current["revision"] != revision:
                raise Conflict("stale_revision")
            # Cadastro antigo incompleto só permanece se vier idêntico ao salvo; qualquer outra abelha vem completa.
            stored = json.loads(current["data"])
            for bee in bees:
                if profile_gaps(bee) and bee not in stored:
                    raise InvalidProfile(bee, profile_gaps(bee)[0])
            bees = [bee if profile_gaps(bee) else normalize(bee) for bee in bees]
            result = {"bees": bees, "revision": revision + 1, "incomplete": incomplete(bees)}
            connection.execute("UPDATE roster_settings SET data=?,revision=? WHERE id=1", (canonical(bees), revision + 1))
            connection.execute("INSERT INTO commands VALUES(?,?,?,?)", ("__roster__", key, fingerprint, canonical(result)))
            return result

    def list_missions(self):
        with self.session() as connection:
            rows = connection.execute("SELECT * FROM missions ORDER BY updated_at DESC LIMIT 100").fetchall()
        return [self._decode(row) for row in rows]

    def jobs(self, mission_id):
        with self.session() as connection:
            rows = connection.execute("SELECT id,bee_id,role,state,data FROM jobs WHERE mission_id=? ORDER BY rowid",
                                      (mission_id,)).fetchall()
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]

    def set_worker_limit(self, limit, key, revision):
        self._key(key)
        if type(limit) is not int or not 1 <= limit <= 20 or type(revision) is not int or revision < 0:
            raise ValueError("invalid settings")
        fingerprint = digest(["worker_limit", limit, revision])
        with self.transaction() as connection:
            prior = connection.execute("SELECT fingerprint,result FROM commands WHERE mission_id=? AND key=?",
                                       ("__settings__", key)).fetchone()
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Conflict("idempotency_key_reused")
                return json.loads(prior["result"])
            current = connection.execute("SELECT revision FROM settings WHERE id=1").fetchone()
            if current["revision"] != revision:
                raise Conflict("stale_revision")
            result = {"worker_limit": limit, "revision": revision + 1}
            connection.execute("UPDATE settings SET worker_limit=?,revision=? WHERE id=1", (limit, revision + 1))
            connection.execute("INSERT INTO commands VALUES(?,?,?,?)", ("__settings__", key, fingerprint, canonical(result)))
            return result

    @staticmethod
    def event(connection, mission_id, kind, data):
        connection.execute("INSERT INTO events(mission_id,kind,data,created_at) VALUES(?,?,?,?)",
                           (mission_id, kind, canonical(data), time.time()))

    def create(self, mission_id, key, title, cycle_limit):
        if not isinstance(mission_id, str) or not mission_id or not isinstance(title, str) or not title.strip():
            raise ValueError("invalid mission")
        if type(cycle_limit) is not int or not 1 <= cycle_limit <= 20:
            raise ValueError("invalid cycle limit")
        fingerprint = digest(["create", mission_id, title, cycle_limit])
        self._key(key)
        with self.transaction() as connection:
            prior = connection.execute("SELECT fingerprint,result FROM commands WHERE mission_id=? AND key=?",
                                       (mission_id, key)).fetchone()
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Conflict("idempotency_key_reused")
                return json.loads(prior["result"])
            now = time.time()
            try:
                connection.execute("INSERT INTO missions VALUES(?,?,?,?,?,?,?,?)",
                    (mission_id, "draft", 0, 1, cycle_limit, canonical({"title": title}), now, now))
            except sqlite3.IntegrityError as exc:
                raise Conflict("mission_exists") from exc
            self.event(connection, mission_id, "mission_created", {"cycle": 1, "cycle_limit": cycle_limit})
            result = self._decode(connection.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone())
            connection.execute("INSERT INTO commands VALUES(?,?,?,?)", (mission_id, key, fingerprint, canonical(result)))
            return result

    @staticmethod
    def _key(key):
        if not isinstance(key, str) or not 1 <= len(key) <= 128:
            raise ValueError("invalid idempotency key")

    def mutate(self, mission_id, key, expected_revision, kind, request, change):
        self._key(key)
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("invalid revision")
        fingerprint = digest([kind, expected_revision, request])
        with self.transaction() as connection:
            prior = connection.execute("SELECT fingerprint,result FROM commands WHERE mission_id=? AND key=?",
                                       (mission_id, key)).fetchone()
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise Conflict("idempotency_key_reused")
                return json.loads(prior["result"])
            mission = self._decode(connection.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone())
            if mission["revision"] != expected_revision:
                raise Conflict("stale_revision")
            event_data = change(connection, mission)
            revision = expected_revision + 1
            connection.execute("UPDATE missions SET state=?,revision=?,cycle=?,cycle_limit=?,data=?,updated_at=? WHERE id=?",
                (mission["state"], revision, mission["cycle"], mission["cycle_limit"],
                 canonical(mission["data"]), time.time(), mission_id))
            self.event(connection, mission_id, kind, event_data)
            result = self._decode(connection.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone())
            connection.execute("INSERT INTO commands VALUES(?,?,?,?)", (mission_id, key, fingerprint, canonical(result)))
            return result

    def recover_interrupted(self):
        """Never retry a possibly executed external effect after process restart."""
        with self.transaction() as connection:
            rows = connection.execute("SELECT * FROM missions WHERE state IN "
                "('planning','preparing','running','verifying','correcting','pausing','applying')").fetchall()
            for row in rows:
                connection.execute("UPDATE missions SET state='recovery_required',revision=revision+1,updated_at=? WHERE id=?",
                                   (time.time(), row["id"]))
                connection.execute("UPDATE jobs SET state='unknown' WHERE mission_id=? AND state IN "
                                   "('running','tool_active','draining')", (row["id"],))
                self.event(connection, row["id"], "recovery_required", {"previous_state": row["state"]})
            count = len(rows)
            for row in connection.execute("SELECT id,data FROM missions WHERE state='awaiting_user'").fetchall():
                data = json.loads(row["data"])
                operation = data.get("reconciliation_operation") or {}
                if operation.get("status") != "pending":
                    continue
                data["reconciliation_operation"] = {**operation, "status": "recovery_required"}
                connection.execute("UPDATE missions SET state='recovery_required',revision=revision+1,data=?,updated_at=? WHERE id=?",
                                   (canonical(data), time.time(), row["id"]))
                self.event(connection, row["id"], "recovery_required", {"previous_state": "awaiting_user",
                                                                         "operation": operation.get("key")})
                count += 1
            return count
