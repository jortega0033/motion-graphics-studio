"""Normal entry point: python -m motion_studio --data-dir <dir> --port <port>."""

import http.client
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import TempDataDir

ROOT = Path(__file__).resolve().parent.parent


class CliTests(unittest.TestCase):
    def test_module_entry_point_serves_health_and_persists(self):
        with TempDataDir() as data_dir:
            proc = subprocess.Popen(
                [sys.executable, "-m", "motion_studio", "--data-dir", data_dir, "--port", "0"],
                cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            try:
                line = proc.stdout.readline()
                match = re.search(r"http://127\.0\.0\.1:(\d+)/", line)
                self.assertIsNotNone(match, line)
                port = int(match.group(1))
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                conn.request("GET", "/api/v1/health", headers={"Host": f"127.0.0.1:{port}"})
                resp = conn.getresponse()
                self.assertEqual(resp.status, 200)
                self.assertEqual(json.loads(resp.read())["status"], "ok")
                conn.close()
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                proc.stdout.close()
            self.assertTrue((Path(data_dir) / "motion_studio.sqlite3").exists())

    def test_no_host_option(self):
        with TempDataDir() as data_dir:
            result = subprocess.run(
                [sys.executable, "-m", "motion_studio", "--data-dir", data_dir, "--host", "0.0.0.0"],
                cwd=str(ROOT), capture_output=True, text=True, timeout=20,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
