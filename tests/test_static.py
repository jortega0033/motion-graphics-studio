"""Static checks on the browser bundle: contract DOM hooks, CSP-safe markup, no external resources."""

import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "motion_studio" / "static"

# Ids present in the markup (the rest are rendered per layer or per project).
REQUIRED_IDS = [
    "projects-view", "new-project-name", "template-select", "preset-select", "create-project",
    "project-list", "projects-status", "projects-error",
    "editor-view", "back-to-projects", "scene-title", "background-color",
    "add-text-layer", "add-rectangle-layer", "add-ellipse-layer", "layer-list",
    "layer-label", "move-up", "move-down", "duplicate-layer", "delete-layer",
    "prop-x", "prop-y", "prop-width", "prop-height", "prop-opacity", "prop-fill",
    "prop-text", "prop-font-size", "prop-align",
    "stage-canvas", "save-button", "save-status", "editor-error", "reload-saved",
]


class StaticBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (STATIC / "index.html").read_text(encoding="utf-8")

    def test_required_hooks_exist(self):
        for hook in REQUIRED_IDS:
            self.assertRegex(self.index, rf'id="{hook}"', hook)

    def test_markup_is_csp_safe(self):
        self.assertNotRegex(self.index, r"<style\b")
        self.assertNotRegex(self.index, r"\sstyle=")
        self.assertNotRegex(self.index, r"\son[a-z]+=")
        for script in re.findall(r"<script\b[^>]*>", self.index):
            self.assertIn("src=", script)

    def test_status_regions_and_labels(self):
        def tag(id_):
            return re.search(rf'<[^>]*id="{id_}"[^>]*>', self.index).group(0)

        for id_ in ("save-status", "projects-status"):
            self.assertIn('role="status"', tag(id_), id_)
        for id_ in ("editor-error", "projects-error"):
            self.assertIn('role="alert"', tag(id_), id_)
        self.assertIn("Layers", tag("layer-list"))
        for text in ("Project title", "Scene title", "Layer label", "Add text layer", "Move up",
                     "Move down", "Duplicate", "Delete", "Save", "Create project", "Projects"):
            self.assertIn(text, self.index, text)

    def test_no_external_references(self):
        for path in STATIC.rglob("*"):
            if path.suffix in {".html", ".css", ".js"}:
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"(?:src|href)=[\"']https?://", str(path))
                self.assertNotRegex(text, r"url\(\s*[\"']?https?://", str(path))
                self.assertNotRegex(text, r"\bimport\s[^;]*from\s+[\"']https?://", str(path))
                self.assertNotRegex(text, r"\bfetch\(\s*[\"']https?://", str(path))

    def test_no_unsafe_html_sinks(self):
        for path in (STATIC / "js").glob("*.js"):
            text = path.read_text(encoding="utf-8")
            for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
                self.assertNotIn(sink, text, f"{path.name}: {sink}")

    def test_renderer_exports_drawscene(self):
        text = (STATIC / "js" / "renderer.js").read_text(encoding="utf-8")
        self.assertRegex(text, r"export\s+(?:function\s+drawScene|\{[^}]*drawScene)")

    def test_page_is_labelled(self):
        self.assertRegex(self.index, r'<html[^>]+lang="en"')
        self.assertRegex(self.index, r"<title>[^<]+</title>")
        self.assertRegex(self.index, r'name="viewport"')


if __name__ == "__main__":
    unittest.main()
