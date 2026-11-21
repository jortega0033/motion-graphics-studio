import copy
import sqlite3
import threading
import unittest
import uuid
from pathlib import Path

from motion_studio.store import StoreError

from helpers import RunningServer, TempDataDir, shape_layer, text_layer, with_layers


class ServerCase(unittest.TestCase):
    def setUp(self):
        self._dir = TempDataDir()
        self.data_dir = self._dir.__enter__()
        self.srv = RunningServer(self.data_dir)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.srv.stop()
        self._dir.__exit__(None, None, None)


class HealthAndSecurityTests(ServerCase):
    def test_health(self):
        status, headers, body = self.srv.request("GET", "/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "motion_studio")
        self.assertEqual(body["schema_version"], 1)
        self.assertEqual(headers["cache-control"], "no-store")

    def test_binds_loopback_only(self):
        self.assertEqual(self.srv.httpd.server_address[0], "127.0.0.1")

    def test_security_headers(self):
        _, headers, _ = self.srv.request("GET", "/api/v1/health")
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        csp = headers["content-security-policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp)

    def test_bad_host_rejected(self):
        for host in ("evil.example", f"evil.example:{self.srv.port}", "127.0.0.1:1"):
            status, _, body = self.srv.request("GET", "/api/v1/health", host=host)
            self.assertEqual(status, 403, host)
            self.assertEqual(body["error"]["code"], "forbidden_host")

    def test_localhost_host_allowed(self):
        status, _, _ = self.srv.request("GET", "/api/v1/health", host=f"localhost:{self.srv.port}")
        self.assertEqual(status, 200)

    def test_write_requires_same_origin(self):
        payload = {"request_id": str(uuid.uuid4()), "name": "x", "template": "blank", "preset": "landscape"}
        for origin in (None, "http://evil.example", f"http://127.0.0.1:{self.srv.port + 1}"):
            status, _, body = self.srv.request("POST", "/api/projects", payload, origin=origin)
            self.assertEqual(status, 403, origin)
            self.assertEqual(body["error"]["code"], "forbidden_origin")
        self.assertEqual(self.srv.request("GET", "/api/projects")[2]["projects"], [])

    def test_write_requires_session_token(self):
        payload = {"request_id": str(uuid.uuid4()), "name": "x", "template": "blank", "preset": "landscape"}
        for token in (None, "wrong"):
            status, _, body = self.srv.request("POST", "/api/projects", payload, token=token)
            self.assertEqual(status, 403)
            self.assertEqual(body["error"]["code"], "session_invalid")

    def test_session_token_is_stable_within_process_and_changes_after_restart(self):
        first = self.srv.request("GET", "/api/session")
        self.assertEqual(first[1]["cache-control"], "no-store")
        self.assertEqual(self.srv.request("GET", "/api/session")[2]["token"], first[2]["token"])
        self.srv.stop()
        self.srv = RunningServer(self.data_dir)
        self.assertNotEqual(self.srv.request("GET", "/api/session")[2]["token"], first[2]["token"])

    def test_write_check_order(self):
        payload = {"request_id": str(uuid.uuid4()), "name": "x", "template": "blank", "preset": "landscape"}
        # bad host wins over everything on a write
        status, _, body = self.srv.request("POST", "/api/projects", payload, host="evil.example", origin=None, token=None)
        self.assertEqual(body["error"]["code"], "forbidden_host")
        # bad origin beats bad token
        status, _, body = self.srv.request("POST", "/api/projects", payload, origin="http://evil.example", token="bad")
        self.assertEqual(body["error"]["code"], "forbidden_origin")
        # bad token beats wrong content type
        status, _, body = self.srv.request("POST", "/api/projects", raw=b"{}", token="bad",
                                           headers={"Content-Type": "text/plain"})
        self.assertEqual(body["error"]["code"], "session_invalid")

    def test_exact_security_headers(self):
        _, headers, _ = self.srv.request("GET", "/api/v1/health")
        self.assertEqual(headers["referrer-policy"], "no-referrer")
        self.assertEqual(
            headers["content-security-policy"],
            "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

    def test_content_type_and_json_errors(self):
        status, _, body = self.srv.request("POST", "/api/projects", raw=b"{}", headers={"Content-Type": "text/plain"})
        self.assertEqual((status, body["error"]["code"]), (415, "unsupported_media_type"))
        for raw in (b"{not json", b"[]", b'{"a": NaN}', b"\xff\xfe"):
            status, _, body = self.srv.request("POST", "/api/projects", raw=raw)
            self.assertEqual((status, body["error"]["code"]), (400, "invalid_json"), raw)

    def test_body_cap(self):
        raw = b'{"pad":"' + b"a" * (1024 * 1024 + 10) + b'"}'
        try:
            status, _, body = self.srv.request("POST", "/api/projects", raw=raw)
        except (ConnectionError, OSError):
            return  # server closed the connection before reading the whole body; also acceptable
        self.assertEqual((status, body["error"]["code"]), (413, "payload_too_large"))

    def test_unknown_route_and_method(self):
        status, _, body = self.srv.request("GET", "/api/nope")
        self.assertEqual((status, body["error"]["code"]), (404, "not_found"))
        status, headers, body = self.srv.request("POST", "/api/v1/health", {})
        self.assertEqual((status, body["error"]["code"]), (405, "method_not_allowed"))
        self.assertIn("allow", headers)

    def test_invalid_ids_are_404(self):
        for path in ("/api/projects/not-a-uuid/revisions", f"/api/projects/{uuid.uuid4()}/revisions/1",
                     f"/api/projects/{uuid.uuid4()}/revisions"):
            self.assertEqual(self.srv.request("GET", path)[0], 404, path)

    def test_static_index_and_traversal(self):
        index = Path(__file__).resolve().parent.parent / "motion_studio" / "static" / "index.html"
        status, headers, body = self.srv.request("GET", "/")
        self.assertTrue(index.exists())
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["content-type"])
        self.assertIn(b"stage-canvas", body)
        for path in ("/static/../server.py", "/static/%2e%2e/server.py", "/static/..%2fserver.py",
                     "/static/js/..\\..\\server.py", "/static/nothing.exe"):
            status, _, _ = self.srv.request("GET", path)
            self.assertEqual(status, 404, path)


class ProjectTests(ServerCase):
    def test_a1_create_blank_portrait_and_title_card_landscape(self):
        portrait = self.srv.create_project("Blank portrait", "blank", "portrait")
        self.assertEqual(portrait["project"]["width"], 720)
        self.assertEqual(portrait["project"]["height"], 1280)
        self.assertEqual(portrait["project"]["head_revision"], 1)
        self.assertEqual(portrait["revision"]["number"], 1)
        self.assertEqual(portrait["revision"]["scene"]["layers"], [])

        card = self.srv.create_project("Card landscape", "title_card", "landscape")
        self.assertEqual((card["project"]["width"], card["project"]["height"]), (1280, 720))
        self.assertEqual(len(card["revision"]["scene"]["layers"]), 3)

        listing = self.srv.request("GET", "/api/projects")[2]["projects"]
        self.assertEqual({p["name"] for p in listing}, {"Blank portrait", "Card landscape"})
        for p in listing:
            self.assertEqual(
                set(p), {"id", "name", "preset", "width", "height", "duration_frames", "head_revision",
                         "created_at", "updated_at"})

    def test_create_replay_and_conflict(self):
        body = {"request_id": str(uuid.uuid4()), "name": "Once", "template": "blank", "preset": "landscape"}
        s1, _, first = self.srv.request("POST", "/api/projects", body)
        s2, _, second = self.srv.request("POST", "/api/projects", body)
        self.assertEqual((s1, s2), (201, 200))
        self.assertTrue(second["replayed"])
        self.assertEqual(first["project"]["id"], second["project"]["id"])
        self.assertEqual(len(self.srv.request("GET", "/api/projects")[2]["projects"]), 1)
        changed = dict(body, name="Different")
        status, _, err = self.srv.request("POST", "/api/projects", changed)
        self.assertEqual((status, err["error"]["code"]), (409, "request_conflict"))

    def test_create_validation(self):
        good = {"request_id": str(uuid.uuid4()), "name": "ok", "template": "blank", "preset": "landscape"}
        bad_variants = [
            dict(good, name=""), dict(good, name="   "), dict(good, name="x" * 81), dict(good, name="a\x01b"),
            dict(good, template="video"), dict(good, preset="square"), dict(good, request_id="nope"),
            dict(good, extra=1),
        ]
        for variant in bad_variants:
            status, _, body = self.srv.request("POST", "/api/projects", variant)
            self.assertEqual((status, body["error"]["code"]), (400, "invalid_request"), variant)
        missing = {k: v for k, v in good.items() if k != "preset"}
        self.assertEqual(self.srv.request("POST", "/api/projects", missing)[0], 400)
        self.assertEqual(self.srv.request("GET", "/api/projects")[2]["projects"], [])

    def test_name_is_trimmed_and_markup_is_stored_as_text(self):
        made = self.srv.create_project("  <img src=x onerror=alert(1)>  ", "blank", "landscape")
        self.assertEqual(made["project"]["name"], "<img src=x onerror=alert(1)>")

    def test_opening_creates_no_revision(self):
        made = self.srv.create_project()
        pid = made["project"]["id"]
        for _ in range(3):
            self.srv.request("GET", f"/api/projects/{pid}/revisions/1")
            self.srv.request("GET", f"/api/projects/{pid}/revisions")
        listing = self.srv.request("GET", f"/api/projects/{pid}/revisions")[2]
        self.assertEqual([r["number"] for r in listing["revisions"]], [1])


class SaveTests(ServerCase):
    def setUp(self):
        super().setUp()
        made = self.srv.create_project("Save fixture", "blank", "landscape")
        self.pid = made["project"]["id"]
        self.scene = made["revision"]["scene"]

    def edited(self, *layers, **changes):
        scene = with_layers(self.scene, *layers)
        scene.update(changes)
        return scene

    def test_save_numbers_revisions_and_preserves_document(self):
        scene = self.edited(shape_layer(), text_layer(), title="Edited title")
        status, _, body = self.srv.save(self.pid, 1, scene)
        self.assertEqual(status, 201)
        self.assertEqual(body["revision"]["number"], 2)
        self.assertEqual(body["project"]["head_revision"], 2)
        self.assertEqual(body["project"]["name"], "Edited title")
        status, _, got = self.srv.request("GET", f"/api/projects/{self.pid}/revisions/2")
        self.assertEqual(got["revision"]["scene"], scene)
        # revision 1 stays inspectable and unchanged
        _, _, first = self.srv.request("GET", f"/api/projects/{self.pid}/revisions/1")
        self.assertEqual(first["revision"]["scene"], self.scene)

    def test_a5_replay_adds_exactly_one_revision(self):
        scene = self.edited(shape_layer())
        rid = str(uuid.uuid4())
        s1, _, first = self.srv.save(self.pid, 1, scene, request_id=rid)
        s2, _, second = self.srv.save(self.pid, 1, scene, request_id=rid)
        self.assertEqual((s1, s2), (201, 200))
        self.assertTrue(second["replayed"])
        self.assertEqual(second["revision"]["number"], first["revision"]["number"])
        listing = self.srv.request("GET", f"/api/projects/{self.pid}/revisions")[2]["revisions"]
        self.assertEqual([r["number"] for r in listing], [2, 1])

    def test_reused_request_id_with_different_input_conflicts(self):
        rid = str(uuid.uuid4())
        self.srv.save(self.pid, 1, self.edited(shape_layer()), request_id=rid)
        status, _, body = self.srv.save(self.pid, 1, self.edited(text_layer()), request_id=rid)
        self.assertEqual((status, body["error"]["code"]), (409, "request_conflict"))
        self.assertEqual(self.srv.request("GET", "/api/projects")[2]["projects"][0]["head_revision"], 2)

    def test_stale_head_returns_current_and_adds_nothing(self):
        self.srv.save(self.pid, 1, self.edited(shape_layer()))
        status, _, body = self.srv.save(self.pid, 1, self.edited(text_layer()))
        self.assertEqual(status, 409)
        self.assertEqual(body["error"]["code"], "stale_head")
        self.assertEqual(body["error"]["details"]["current_head"], 2)
        self.assertEqual(body["error"]["details"]["current_revision"]["number"], 2)
        listing = self.srv.request("GET", f"/api/projects/{self.pid}/revisions")[2]["revisions"]
        self.assertEqual(len(listing), 2)

    def test_concurrent_saves_from_one_head_yield_one_winner(self):
        results = []

        def attempt(layer):
            results.append(self.srv.save(self.pid, 1, self.edited(layer))[0])

        threads = [threading.Thread(target=attempt, args=(shape_layer(),)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(results), [201, 409, 409, 409])
        listing = self.srv.request("GET", f"/api/projects/{self.pid}/revisions")[2]["revisions"]
        self.assertEqual([r["number"] for r in listing], [2, 1])

    def test_invalid_scene_keeps_head(self):
        bad = self.edited(shape_layer(opacity=3))
        status, _, body = self.srv.save(self.pid, 1, bad)
        self.assertEqual((status, body["error"]["code"]), (422, "invalid_scene"))
        self.assertIn("layers[0].opacity", [e["path"] for e in body["error"]["details"]["errors"]])
        self.assertEqual(self.srv.request("GET", "/api/projects")[2]["projects"][0]["head_revision"], 1)

    def test_preset_cannot_change(self):
        portrait = copy.deepcopy(self.scene)
        portrait.update(preset="portrait", width=720, height=1280)
        status, _, _ = self.srv.save(self.pid, 1, portrait)
        self.assertEqual(status, 422)

    def test_request_shape_errors(self):
        good = {"request_id": str(uuid.uuid4()), "expected_head": 1, "scene": self.scene}
        for variant in (dict(good, expected_head=0), dict(good, expected_head=True), dict(good, expected_head="1"),
                        dict(good, request_id="x"), dict(good, scene=[])):
            status, _, body = self.srv.request("POST", f"/api/projects/{self.pid}/revisions", variant)
            self.assertEqual((status, body["error"]["code"]), (400, "invalid_request"), variant)

    def test_save_to_unknown_project(self):
        status, _, body = self.srv.save(str(uuid.uuid4()), 1, self.scene)
        self.assertEqual((status, body["error"]["code"]), (404, "not_found"))

    def test_revision_history_paging(self):
        head = 1
        for i in range(27):
            scene = self.edited(shape_layer(), title=f"Edit {i}")
            status, _, body = self.srv.save(self.pid, head, scene)
            self.assertEqual(status, 201)
            head = body["revision"]["number"]
        page1 = self.srv.request("GET", f"/api/projects/{self.pid}/revisions")[2]
        self.assertEqual(len(page1["revisions"]), 25)
        self.assertEqual(page1["revisions"][0]["number"], 28)
        self.assertEqual(page1["next_before"], 4)
        page2 = self.srv.request("GET", f"/api/projects/{self.pid}/revisions?before={page1['next_before']}")[2]
        self.assertEqual([r["number"] for r in page2["revisions"]], [3, 2, 1])
        self.assertIsNone(page2["next_before"])
        for q in ("limit=0", "limit=26", "limit=x", "before=0"):
            self.assertEqual(self.srv.request("GET", f"/api/projects/{self.pid}/revisions?{q}")[0], 400, q)

    def test_markup_text_round_trips_unmodified(self):
        scene = self.edited(text_layer(text="<script>alert(1)</script>\n& \"quotes\" é"))
        self.srv.save(self.pid, 1, scene)
        got = self.srv.request("GET", f"/api/projects/{self.pid}/revisions/2")[2]["revision"]["scene"]
        self.assertEqual(got["layers"][0]["text"], "<script>alert(1)</script>\n& \"quotes\" é")

    def test_revisions_are_immutable_in_the_database(self):
        self.srv.save(self.pid, 1, self.edited(shape_layer()))
        db = sqlite3.connect(str(Path(self.data_dir) / "motion_studio.sqlite3"))
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("UPDATE revisions SET scene_json='{}' WHERE number=1")
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("DELETE FROM revisions WHERE number=1")
        finally:
            db.close()


class RestartTests(ServerCase):
    def test_a5_edit_save_restart_reopen(self):
        made = self.srv.create_project("Restart fixture", "title_card", "portrait")
        pid = made["project"]["id"]
        scene = copy.deepcopy(made["revision"]["scene"])
        scene["title"] = "Restart fixture edited"
        scene["layers"].append(shape_layer("ellipse", name="Marker"))
        scene["layers"].append(text_layer(text="Persisted"))
        scene["layers"].reverse()
        status, _, saved = self.srv.save(pid, 1, scene)
        self.assertEqual(status, 201)

        self.srv.stop()
        self.srv = RunningServer(self.data_dir)

        listing = self.srv.request("GET", "/api/projects")[2]["projects"]
        self.assertEqual(len(listing), 1)
        summary = listing[0]
        self.assertEqual((summary["id"], summary["head_revision"]), (pid, 2))
        self.assertEqual((summary["width"], summary["height"]), (720, 1280))
        self.assertEqual(summary["name"], "Restart fixture edited")
        got = self.srv.request("GET", f"/api/projects/{pid}/revisions/{summary['head_revision']}")[2]["revision"]
        self.assertEqual(got["scene"], scene)
        self.assertEqual(got["committed_at"], saved["revision"]["committed_at"])

        # a new request against the old head is stale and adds nothing
        status, _, body = self.srv.save(pid, 1, scene)
        self.assertEqual((status, body["error"]["code"]), (409, "stale_head"))
        self.assertEqual(len(self.srv.request("GET", f"/api/projects/{pid}/revisions")[2]["revisions"]), 2)

    def test_replay_survives_restart(self):
        made = self.srv.create_project()
        pid = made["project"]["id"]
        scene = with_layers(made["revision"]["scene"], shape_layer())
        rid = str(uuid.uuid4())
        self.assertEqual(self.srv.save(pid, 1, scene, request_id=rid)[0], 201)
        self.srv.stop()
        self.srv = RunningServer(self.data_dir)
        status, _, body = self.srv.save(pid, 1, scene, request_id=rid)
        self.assertEqual(status, 200)
        self.assertTrue(body["replayed"])
        self.assertEqual(len(self.srv.request("GET", f"/api/projects/{pid}/revisions")[2]["revisions"]), 2)

    def test_newer_schema_database_is_refused_and_untouched(self):
        self.srv.stop()
        path = Path(self.data_dir) / "motion_studio.sqlite3"
        db = sqlite3.connect(str(path))
        db.execute("PRAGMA user_version=99")
        db.commit()
        db.close()
        before = path.read_bytes()
        with self.assertRaises(StoreError) as ctx:
            RunningServer(self.data_dir)
        self.assertEqual(ctx.exception.code, "unsupported_database")
        self.assertEqual(path.read_bytes(), before)
        # restore so cleanup's stop() on the stopped server stays harmless
        self.srv = type("Stopped", (), {"stop": lambda self_: None})()


if __name__ == "__main__":
    unittest.main()
