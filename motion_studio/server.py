"""Loopback HTTP server for Motion Graphics Studio (stdlib only)."""

import hmac
import json
import math
import os
import re
import secrets
import sys
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .scene import is_uuid
from .store import Store, StoreError

STATIC_ROOT = Path(__file__).resolve().parent / "static"
MAX_BODY = 1024 * 1024
MAX_DRAIN = 8 * 1024 * 1024

CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
    "form-action 'none'; frame-ancestors 'none'"
)

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
}

WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
POSITIVE_INT_RE = re.compile(r"[1-9][0-9]{0,11}")
QUERY_INT_RE = re.compile(r"[0-9]{1,9}")


class _BadJson(Exception):
    pass


def _reject_constant(name):
    raise ValueError("non-finite number")


def _parse_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("non-finite number")
    return value


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def parse_json_object(data):
    try:
        text = data.decode("utf-8")
        value = json.loads(
            text,
            parse_constant=_reject_constant,
            parse_float=_parse_float,
            object_pairs_hook=_object_pairs,
        )
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise _BadJson()
    if not isinstance(value, dict):
        raise _BadJson()
    return value


def _route(path):
    """Return (name, params, allowed_methods) or None."""
    if path == "/":
        return "index", {}, ("GET",)
    if path.startswith("/static/"):
        return "static", {"rest": path[len("/static/"):]}, ("GET",)
    if path == "/api/v1/health":
        return "health", {}, ("GET",)
    if path == "/api/session":
        return "session", {}, ("GET",)
    if path == "/api/projects":
        return "projects", {}, ("GET", "POST")
    if path.startswith("/api/projects/"):
        parts = path.split("/")
        # ['', 'api', 'projects', id, 'revisions'[, n]]
        if len(parts) in (5, 6) and parts[4] == "revisions" and is_uuid(parts[3]):
            if len(parts) == 5:
                return "revisions", {"id": parts[3]}, ("GET", "POST")
            if POSITIVE_INT_RE.fullmatch(parts[5]):
                return "revision", {"id": parts[3], "n": int(parts[5])}, ("GET",)
    return None


def resolve_static(rest):
    """Map the part after /static/ to a file path or None."""
    low = rest.lower()
    if "%2f" in low or "%5c" in low or "%00" in low:
        return None
    try:
        decoded = urllib.parse.unquote(rest, errors="strict")
    except UnicodeDecodeError:
        return None
    if not decoded or "\\" in decoded or ":" in decoded:
        return None
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in decoded):
        return None
    parts = decoded.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    if os.path.splitext(parts[-1])[1] not in MIME:
        return None
    try:
        root = STATIC_ROOT.resolve()
        candidate = root.joinpath(*parts).resolve()
        candidate.relative_to(root)
    except (OSError, ValueError):
        return None
    if not candidate.is_file():
        return None
    return candidate


def _parse_list_query(query):
    limit, before = 25, None
    if not query:
        return limit, before
    try:
        pairs = urllib.parse.parse_qsl(
            query, keep_blank_values=True, strict_parsing=True, max_num_fields=8
        )
    except ValueError:
        raise StoreError(400, "invalid_request", "Invalid query string.")
    seen = set()
    errors = []
    for key, value in pairs:
        if key not in ("limit", "before") or key in seen:
            errors.append({"path": key[:40], "message": "unknown or repeated parameter"})
            continue
        seen.add(key)
        if not QUERY_INT_RE.fullmatch(value):
            errors.append({"path": key, "message": "must be an integer"})
            continue
        number = int(value)
        if key == "limit":
            if 1 <= number <= 25:
                limit = number
            else:
                errors.append({"path": key, "message": "must be 1 to 25"})
        else:
            if number >= 1:
                before = number
            else:
                errors.append({"path": key, "message": "must be >= 1"})
    if errors:
        raise StoreError(400, "invalid_request", "Invalid query string.",
                         {"errors": errors})
    return limit, before


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "MotionStudio"
    sys_version = ""
    timeout = 20

    # -- logging: method, path, status only --------------------------------

    def log_request(self, code="-", size="-"):
        try:
            path = (getattr(self, "path", "") or "").split("?", 1)[0]
            line = "%s %s %s\n" % (
                getattr(self, "command", None) or "-",
                ascii(path)[:200],
                getattr(code, "value", code),
            )
            sys.stderr.write(line)
            sys.stderr.flush()
        except Exception:
            pass

    def log_message(self, format, *args):
        pass

    # -- verbs ---------------------------------------------------------------

    def do_GET(self):
        self._dispatch()

    do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = do_GET

    # -- response helpers ----------------------------------------------------

    def _send(self, status, body, content_type, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if getattr(self, "command", None) != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status, obj, extra=None):
        body = json.dumps(obj, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        self._send(status, body, "application/json; charset=utf-8", extra)

    def _send_error_json(self, status, code, message, details=None, extra=None):
        self._drain()
        self._send_json(
            status,
            {"error": {"code": code, "message": message, "details": details or {}}},
            extra,
        )

    def send_error(self, code, message=None, explain=None):
        # Used by the base class for malformed requests; keep it JSON.
        self.close_connection = True
        try:
            status = HTTPStatus(code)
            text = status.phrase
        except ValueError:
            text = "Error"
        mapping = {501: "method_not_allowed", 405: "method_not_allowed",
                   404: "not_found", 408: "request_timeout"}
        try:
            self._body_consumed = True
            self._send_error_json(code, mapping.get(code, "invalid_request"), text)
        except Exception:
            pass

    def _drain(self):
        """Discard an unread request body so the client sees our response."""
        if getattr(self, "_body_consumed", False):
            return
        self._body_consumed = True
        try:
            remaining = int(self.headers.get("Content-Length", "0"))
        except (TypeError, ValueError, AttributeError):
            return
        remaining = min(max(remaining, 0), MAX_DRAIN)
        try:
            while remaining > 0:
                chunk = self.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
        except Exception:
            pass

    # -- dispatch ------------------------------------------------------------

    def _dispatch(self):
        self._body_consumed = False
        try:
            self._dispatch_inner()
        except StoreError as exc:
            self._send_error_json(exc.status, exc.code, exc.message, exc.details)
        except (BrokenPipeError, ConnectionError, TimeoutError):
            self.close_connection = True
        except Exception:
            try:
                self._send_error_json(500, "internal_error",
                                      "Internal server error.")
            except Exception:
                self.close_connection = True

    def _dispatch_inner(self):
        srv = self.server
        method = self.command
        port = srv.server_port
        host = self.headers.get("Host")
        valid_hosts = ("127.0.0.1:%d" % port, "localhost:%d" % port)
        if host is None or host.lower() not in valid_hosts:
            raise StoreError(403, "forbidden_host", "Host not allowed.")
        host = host.lower()

        target = self.path
        if not target.startswith("/"):
            raise StoreError(404, "not_found", "Not found.")
        target = target.split("#", 1)[0]
        path, _, query = target.partition("?")

        route = _route(path)
        if route is None:
            raise StoreError(404, "not_found", "Not found.")
        name, params, allowed = route
        if method not in allowed:
            self._drain()
            self._send_error_json(
                405, "method_not_allowed", "Method not allowed.",
                extra={"Allow": ", ".join(allowed)})
            return

        body = None
        if method in WRITE_METHODS:
            if self.headers.get("Origin") != "http://" + host:
                raise StoreError(403, "forbidden_origin", "Origin not allowed.")
            token = self.headers.get("X-Session-Token") or ""
            if not hmac.compare_digest(token.encode("utf-8", "replace"),
                                       srv.session_token.encode("ascii")):
                raise StoreError(403, "session_invalid",
                                 "Session token missing or invalid.")
            ctype = (self.headers.get("Content-Type") or "").split(";", 1)[0]
            if ctype.strip().lower() != "application/json":
                raise StoreError(415, "unsupported_media_type",
                                 "Content-Type must be application/json.")
            body = self._read_body()

        if name == "index":
            return self._serve_file(STATIC_ROOT / "index.html")
        if name == "static":
            file_path = resolve_static(params["rest"])
            if file_path is None:
                raise StoreError(404, "not_found", "Not found.")
            return self._serve_file(file_path)
        if name == "health":
            srv.store.ping()
            return self._send_json(200, {"status": "ok", "service": "motion_studio",
                                         "schema_version": 1})
        if name == "session":
            return self._send_json(200, {"token": srv.session_token})
        if name == "projects":
            if method == "GET":
                return self._send_json(200, {"projects": srv.store.list_projects()})
            return self._create_project(body)
        if name == "revisions":
            if method == "GET":
                limit, before = _parse_list_query(query)
                items, next_before = srv.store.list_revisions(
                    params["id"], limit, before)
                return self._send_json(200, {"revisions": items,
                                             "next_before": next_before})
            return self._save_revision(params["id"], body)
        if name == "revision":
            rev = srv.store.get_revision(params["id"], params["n"])
            return self._send_json(200, {"revision": rev})
        raise StoreError(404, "not_found", "Not found.")

    def _read_body(self):
        if self.headers.get("Transfer-Encoding") is not None:
            raise StoreError(400, "invalid_request",
                             "Transfer-Encoding is not supported.")
        raw = self.headers.get("Content-Length")
        if raw is None:
            raise StoreError(411, "length_required", "Content-Length is required.")
        raw = raw.strip()
        if not raw.isascii() or not raw.isdigit() or len(raw) > 12:
            raise StoreError(400, "invalid_request", "Invalid Content-Length.")
        length = int(raw)
        if length > MAX_BODY:
            raise StoreError(413, "payload_too_large",
                             "Request body exceeds 1 MiB.")
        data = b""
        while len(data) < length:
            chunk = self.rfile.read(length - len(data))
            if not chunk:
                break
            data += chunk
        self._body_consumed = True
        if len(data) != length:
            self.close_connection = True
            raise StoreError(400, "invalid_json", "Request body is incomplete.")
        try:
            return parse_json_object(data)
        except _BadJson:
            raise StoreError(400, "invalid_json",
                             "Body must be a UTF-8 JSON object.")

    def _create_project(self, body):
        errors = []
        fields = ("request_id", "name", "template", "preset")
        for key in fields:
            if key not in body:
                errors.append({"path": key, "message": "is required"})
        for key in body:
            if key not in fields:
                errors.append({"path": key[:40], "message": "unknown field"})
        if errors:
            raise StoreError(400, "invalid_request", "Request is invalid.",
                             {"errors": errors})
        summary, revision, replayed = self.server.store.create_project(
            body["request_id"], body["name"], body["template"], body["preset"])
        payload = {"project": summary, "revision": revision}
        if replayed:
            payload["replayed"] = True
            return self._send_json(200, payload)
        return self._send_json(201, payload)

    def _save_revision(self, project_id, body):
        errors = []
        fields = ("request_id", "expected_head", "scene")
        for key in fields:
            if key not in body:
                errors.append({"path": key, "message": "is required"})
        for key in body:
            if key not in fields:
                errors.append({"path": key[:40], "message": "unknown field"})
        if errors:
            raise StoreError(400, "invalid_request", "Request is invalid.",
                             {"errors": errors})
        revision, summary, replayed = self.server.store.save_revision(
            project_id, body["request_id"], body["expected_head"], body["scene"])
        payload = {"revision": revision, "project": summary}
        if replayed:
            payload["replayed"] = True
            return self._send_json(200, payload)
        return self._send_json(201, payload)

    def _serve_file(self, file_path):
        ext = os.path.splitext(str(file_path))[1].lower()
        try:
            data = Path(file_path).read_bytes()
        except OSError:
            raise StoreError(404, "not_found", "Not found.")
        self._send(200, data, MIME.get(ext, "application/octet-stream"))


class MotionServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = os.name != "nt"

    def __init__(self, data_dir, port=0):
        self.store = Store(data_dir)
        self.session_token = secrets.token_urlsafe(32)
        try:
            super().__init__(("127.0.0.1", port), Handler)
        except BaseException:
            self.store.close()
            raise

    def server_close(self):
        try:
            super().server_close()
        finally:
            self.store.close()


def create_server(data_dir, port=0):
    return MotionServer(data_dir, port)
