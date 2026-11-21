"""SQLite persistence for projects and immutable scene revisions."""

import hashlib
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .scene import (
    PRESETS,
    canonical_json,
    is_uuid,
    new_scene,
    validate_scene,
)

DB_NAME = "motion_studio.sqlite3"
USER_VERSION = 1
TEMPLATES = ("blank", "title_card")

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        head_revision INTEGER NOT NULL,
        create_request_id TEXT NOT NULL UNIQUE,
        create_request_hash TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS revisions (
        project_id TEXT NOT NULL REFERENCES projects(id),
        number INTEGER NOT NULL,
        schema_version INTEGER NOT NULL,
        scene_json TEXT NOT NULL,
        committed_at TEXT NOT NULL,
        request_id TEXT,
        request_hash TEXT,
        PRIMARY KEY (project_id, number),
        UNIQUE (project_id, request_id)
    )""",
    """CREATE TRIGGER IF NOT EXISTS revisions_no_update
        BEFORE UPDATE ON revisions
        BEGIN SELECT RAISE(ABORT, 'revisions are immutable'); END""",
    """CREATE TRIGGER IF NOT EXISTS revisions_no_delete
        BEFORE DELETE ON revisions
        BEGIN SELECT RAISE(ABORT, 'revisions are immutable'); END""",
)


class StoreError(Exception):
    def __init__(self, status, code, message, details=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = dict(details) if details else {}


def _now():
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _hash(obj):
    text = canonical_json(obj)
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()


def _invalid(errors):
    return StoreError(400, "invalid_request", "Request is invalid.",
                      {"errors": errors})


def _not_found(what="Resource"):
    return StoreError(404, "not_found", "%s not found." % what)


def _has_control(text):
    import unicodedata
    return any(unicodedata.category(c) in ("Cc", "Cs") for c in text)


def _summary_from(project_id, created_at, head, scene, committed_at):
    return {
        "id": project_id,
        "name": scene["title"],
        "preset": scene["preset"],
        "width": scene["width"],
        "height": scene["height"],
        "duration_frames": scene["duration_frames"],
        "head_revision": head,
        "created_at": created_at,
        "updated_at": committed_at,
    }


def _revision_from(project_id, number, schema_version, scene_json, committed_at):
    return {
        "project_id": project_id,
        "number": number,
        "schema_version": schema_version,
        "committed_at": committed_at,
        "scene": json.loads(scene_json),
    }


class Store:
    def __init__(self, data_dir):
        path = Path(data_dir)
        path.mkdir(parents=True, exist_ok=True)
        self.path = path / DB_NAME
        self._lock = threading.RLock()
        self._closed = False
        conn = sqlite3.connect(
            str(self.path),
            check_same_thread=False,
            isolation_level=None,
            timeout=10.0,
        )
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > USER_VERSION:
                raise StoreError(
                    500,
                    "unsupported_database",
                    "Database %s has schema version %d, but this build only "
                    "supports version %d. Refusing to start; the file was "
                    "not modified." % (self.path, version, USER_VERSION),
                )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("BEGIN IMMEDIATE")
            try:
                for stmt in SCHEMA:
                    conn.execute(stmt)
                conn.execute("PRAGMA user_version=%d" % USER_VERSION)
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
        except BaseException:
            conn.close()
            raise
        self._conn = conn

    # -- infrastructure ---------------------------------------------------

    def close(self):
        with self._lock:
            if not self._closed:
                self._closed = True
                self._conn.close()

    def ping(self):
        with self._lock:
            self._check_open()
            self._conn.execute("SELECT 1").fetchone()

    def _check_open(self):
        if self._closed:
            raise StoreError(500, "internal_error", "Store is closed.")

    @contextmanager
    def _tx(self):
        with self._lock:
            self._check_open()
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
            except BaseException:
                try:
                    self._conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
            else:
                self._conn.execute("COMMIT")

    @contextmanager
    def _read(self):
        with self._lock:
            self._check_open()
            yield self._conn

    # -- helpers (call with lock held) -------------------------------------

    @staticmethod
    def _load_revision(c, project_id, number):
        row = c.execute(
            "SELECT schema_version, scene_json, committed_at FROM revisions "
            "WHERE project_id=? AND number=?",
            (project_id, number),
        ).fetchone()
        if row is None:
            return None
        return _revision_from(project_id, number, row[0], row[1], row[2])

    @staticmethod
    def _load_summary(c, project_id):
        row = c.execute(
            "SELECT p.created_at, p.head_revision, r.scene_json, r.committed_at "
            "FROM projects p JOIN revisions r "
            "ON r.project_id = p.id AND r.number = p.head_revision "
            "WHERE p.id=?",
            (project_id,),
        ).fetchone()
        if row is None:
            return None
        return _summary_from(project_id, row[0], row[1], json.loads(row[2]), row[3])

    # -- public API ----------------------------------------------------------

    def create_project(self, request_id, name, template, preset):
        errors = []
        if not is_uuid(request_id):
            errors.append({"path": "request_id", "message": "must be a lowercase UUID"})
        if not isinstance(name, str):
            errors.append({"path": "name", "message": "must be a string"})
        else:
            trimmed = name.strip()
            if _has_control(name):
                errors.append({"path": "name",
                               "message": "must not contain control characters"})
            elif not 1 <= len(trimmed) <= 80:
                errors.append({"path": "name",
                               "message": "must be 1 to 80 characters"})
        if not isinstance(template, str) or template not in TEMPLATES:
            errors.append({"path": "template",
                           "message": "must be blank or title_card"})
        if not isinstance(preset, str) or preset not in PRESETS:
            errors.append({"path": "preset",
                           "message": "must be landscape or portrait"})
        if errors:
            raise _invalid(errors)
        name = name.strip()
        req_hash = _hash({"name": name, "template": template, "preset": preset})

        with self._tx() as c:
            row = c.execute(
                "SELECT id, create_request_hash FROM projects "
                "WHERE create_request_id=?",
                (request_id,),
            ).fetchone()
            if row is not None:
                if row[1] != req_hash:
                    raise StoreError(
                        409, "request_conflict",
                        "request_id was already used with different input.")
                return (self._load_summary(c, row[0]),
                        self._load_revision(c, row[0], 1), True)
            project_id = str(uuid.uuid4())
            now = _now()
            scene = new_scene(name, template, preset)
            scene_json = canonical_json(scene)
            c.execute(
                "INSERT INTO projects (id, created_at, head_revision, "
                "create_request_id, create_request_hash) VALUES (?,?,?,?,?)",
                (project_id, now, 1, request_id, req_hash),
            )
            c.execute(
                "INSERT INTO revisions (project_id, number, schema_version, "
                "scene_json, committed_at, request_id, request_hash) "
                "VALUES (?,?,?,?,?,NULL,NULL)",
                (project_id, 1, 1, scene_json, now),
            )
            summary = _summary_from(project_id, now, 1, scene, now)
            revision = _revision_from(project_id, 1, 1, scene_json, now)
            return summary, revision, False

    def list_projects(self):
        with self._read() as c:
            rows = c.execute(
                "SELECT p.id, p.created_at, p.head_revision, r.scene_json, "
                "r.committed_at FROM projects p JOIN revisions r "
                "ON r.project_id = p.id AND r.number = p.head_revision "
                "ORDER BY r.committed_at DESC, p.id ASC"
            ).fetchall()
        return [
            _summary_from(r[0], r[1], r[2], json.loads(r[3]), r[4]) for r in rows
        ]

    def get_revision(self, project_id, number):
        with self._read() as c:
            rev = None
            if (isinstance(number, int) and not isinstance(number, bool)
                    and number >= 1):
                rev = self._load_revision(c, project_id, number)
        if rev is None:
            raise _not_found("Revision")
        return rev

    def list_revisions(self, project_id, limit=25, before=None):
        if (not isinstance(limit, int) or isinstance(limit, bool)
                or not 1 <= limit <= 25):
            raise _invalid([{"path": "limit", "message": "must be 1 to 25"}])
        if before is not None and (not isinstance(before, int)
                                   or isinstance(before, bool) or before < 1):
            raise _invalid([{"path": "before",
                             "message": "must be a positive integer"}])
        with self._read() as c:
            if c.execute("SELECT 1 FROM projects WHERE id=?",
                         (project_id,)).fetchone() is None:
                raise _not_found("Project")
            if before is None:
                rows = c.execute(
                    "SELECT number, committed_at, scene_json FROM revisions "
                    "WHERE project_id=? ORDER BY number DESC LIMIT ?",
                    (project_id, limit + 1),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT number, committed_at, scene_json FROM revisions "
                    "WHERE project_id=? AND number<? ORDER BY number DESC LIMIT ?",
                    (project_id, before, limit + 1),
                ).fetchall()
        more = len(rows) > limit
        rows = rows[:limit]
        items = []
        for number, committed_at, scene_json in rows:
            scene = json.loads(scene_json)
            items.append({
                "number": number,
                "committed_at": committed_at,
                "title": scene["title"],
                "layer_count": len(scene["layers"]),
            })
        next_before = items[-1]["number"] if more and items else None
        return items, next_before

    def save_revision(self, project_id, request_id, expected_head, scene):
        errors = []
        if not is_uuid(request_id):
            errors.append({"path": "request_id", "message": "must be a lowercase UUID"})
        if (not isinstance(expected_head, int) or isinstance(expected_head, bool)
                or expected_head < 1):
            errors.append({"path": "expected_head",
                           "message": "must be an integer >= 1"})
        if not isinstance(scene, dict):
            errors.append({"path": "scene", "message": "must be an object"})
        if errors:
            raise _invalid(errors)
        try:
            req_hash = _hash({"expected_head": expected_head, "scene": scene})
        except (ValueError, TypeError, RecursionError):
            raise _invalid([{"path": "scene",
                             "message": "is not representable as JSON"}])

        with self._tx() as c:
            proj = c.execute(
                "SELECT head_revision FROM projects WHERE id=?", (project_id,)
            ).fetchone()
            if proj is None:
                raise _not_found("Project")
            head = proj[0]

            existing = c.execute(
                "SELECT number, request_hash FROM revisions "
                "WHERE project_id=? AND request_id=?",
                (project_id, request_id),
            ).fetchone()
            if existing is not None:
                if existing[1] != req_hash:
                    raise StoreError(
                        409, "request_conflict",
                        "request_id was already used with different input.")
                return (self._load_revision(c, project_id, existing[0]),
                        self._load_summary(c, project_id), True)

            scene_errors = validate_scene(scene)
            base = c.execute(
                "SELECT scene_json FROM revisions WHERE project_id=? AND number=1",
                (project_id,),
            ).fetchone()
            if base is not None:
                base_scene = json.loads(base[0])
                for field in ("preset", "width", "height"):
                    if (field in scene and scene[field] != base_scene[field]
                            and not any(e["path"] == field for e in scene_errors)):
                        scene_errors.append({
                            "path": field,
                            "message": "cannot change after project creation "
                                       "(must be %s)" % (base_scene[field],),
                        })
            if scene_errors:
                raise StoreError(422, "invalid_scene", "Scene is invalid.",
                                 {"errors": scene_errors})

            if expected_head != head:
                raise StoreError(
                    409, "stale_head",
                    "Project head is revision %d, not %d." % (head, expected_head),
                    {"current_head": head,
                     "current_revision": self._load_revision(c, project_id, head)},
                )

            number = head + 1
            now = _now()
            scene_json = canonical_json(scene)
            c.execute(
                "INSERT INTO revisions (project_id, number, schema_version, "
                "scene_json, committed_at, request_id, request_hash) "
                "VALUES (?,?,?,?,?,?,?)",
                (project_id, number, 1, scene_json, now, request_id, req_hash),
            )
            c.execute("UPDATE projects SET head_revision=? WHERE id=?",
                      (number, project_id))
            created = c.execute("SELECT created_at FROM projects WHERE id=?",
                                (project_id,)).fetchone()[0]
            revision = _revision_from(project_id, number, 1, scene_json, now)
            summary = _summary_from(project_id, created, number,
                                    revision["scene"], now)
            return revision, summary, False
