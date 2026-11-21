"""Shared test helpers: a real loopback server on an ephemeral port with a disposable data root."""

import copy
import http.client
import json
import tempfile
import threading
import uuid

from motion_studio.server import create_server


class RunningServer:
    """Start and stop the service against a data directory. Reusable to simulate a restart."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.httpd = create_server(data_dir, port=0)
        self.port = self.httpd.server_port
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self._token = None

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.port}"

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)

    def request(self, method, path, body=None, headers=None, raw=None, host=None, origin="default", token="default"):
        """Return (status, headers, parsed_json_or_bytes). Writes get Origin, token and JSON type by default."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = {"Host": host or f"127.0.0.1:{self.port}"}
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            if origin == "default":
                hdrs["Origin"] = self.origin
            elif origin is not None:
                hdrs["Origin"] = origin
            if token == "default":
                hdrs["X-Session-Token"] = self.token()
            elif token is not None:
                hdrs["X-Session-Token"] = token
            hdrs["Content-Type"] = "application/json"
        if headers:
            hdrs.update(headers)
        payload = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        if payload is not None:
            hdrs.setdefault("Content-Length", str(len(payload)))
        elif method in ("POST", "PUT", "PATCH"):
            hdrs.setdefault("Content-Length", "0")
        hdrs = {k: v for k, v in hdrs.items() if v is not None}
        try:
            conn.request(method, path, body=payload, headers=hdrs)
            resp = conn.getresponse()
            data = resp.read()
            ctype = resp.getheader("Content-Type", "")
            parsed = json.loads(data) if "json" in ctype and data else data
            return resp.status, {k.lower(): v for k, v in resp.getheaders()}, parsed
        finally:
            conn.close()

    def token(self):
        if self._token is None:
            status, _, body = self.request("GET", "/api/session")
            assert status == 200, status
            self._token = body["token"]
        return self._token

    def create_project(self, name="Fixture", template="blank", preset="landscape"):
        status, _, body = self.request(
            "POST", "/api/projects",
            {"request_id": str(uuid.uuid4()), "name": name, "template": template, "preset": preset},
        )
        assert status == 201, (status, body)
        return body

    def save(self, project_id, expected_head, scene, request_id=None):
        return self.request(
            "POST", f"/api/projects/{project_id}/revisions",
            {"request_id": request_id or str(uuid.uuid4()), "expected_head": expected_head, "scene": scene},
        )


def shape_layer(kind="rectangle", **overrides):
    layer = {
        "id": str(uuid.uuid4()), "kind": kind, "name": f"{kind} fixture",
        "x": 100, "y": 80, "width": 200, "height": 120,
        "opacity": 1, "fill": "#f5a524",
    }
    layer.update(overrides)
    return layer


def text_layer(**overrides):
    layer = {
        "id": str(uuid.uuid4()), "kind": "text", "name": "Text fixture",
        "x": 64, "y": 64, "opacity": 1, "fill": "#f4f1ea",
        "text": "Northwind Demo", "font_size": 48, "align": "left",
    }
    layer.update(overrides)
    return layer


def with_layers(scene, *layers):
    scene = copy.deepcopy(scene)
    scene["layers"] = list(layers)
    return scene


class TempDataDir:
    """Context manager yielding a disposable data directory path."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="motion_studio_test_")
        return self._tmp.name

    def __exit__(self, *exc):
        try:
            self._tmp.cleanup()
        except OSError:
            pass  # SQLite files can linger briefly on Windows; the temp dir is disposable.
        return False
