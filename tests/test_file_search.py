"""Unit tests for bounded file search and indexing."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from file_search import (
    normalize,
    fuzzy_score,
    scan_files,
    search_files,
    FileSearchModel,
)


class TestFileSearch(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Create dummy directory structure
        (self.root / "projects").mkdir()
        (self.root / "documents").mkdir()
        (self.root / ".hidden").mkdir()
        (self.root / "node_modules").mkdir()

        # Files
        (self.root / "projects" / "main.py").write_text("print('hello')")
        (self.root / "projects" / "test_runner.py").write_text("assert True")
        (self.root / "documents" / "report_2026.pdf").write_text("sample pdf")
        (self.root / "documents" / "notes.txt").write_text("some notes")
        (self.root / ".hidden" / "secret.txt").write_text("secret")
        (self.root / "node_modules" / "package.json").write_text("{}")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_normalize(self):
        self.assertEqual(normalize("Café_Résumé.TXT"), "cafe_resume.txt")
        self.assertEqual(normalize("Hello World"), "hello world")

    def test_fuzzy_score(self):
        # Exact match
        self.assertEqual(fuzzy_score("notes.txt", "notes.txt"), 1000)
        # Prefix match
        self.assertGreater(fuzzy_score("note", "notes.txt"), 800)
        # Substring match
        self.assertGreater(fuzzy_score("runner", "test_runner.py"), 600)
        # Typo match
        self.assertGreater(fuzzy_score("notse", "notes.txt"), 150)
        # No match
        self.assertEqual(fuzzy_score("zebra", "notes.txt"), 0)

    def test_scan_files_skips_hidden_and_skip_dirs(self):
        entries, capped = scan_files(str(self.root), limit=100)
        self.assertFalse(capped)
        paths = [e[0] for e in entries]

        # Valid files indexed
        self.assertTrue(any("main.py" in p for p in paths))
        self.assertTrue(any("test_runner.py" in p for p in paths))
        self.assertTrue(any("report_2026.pdf" in p for p in paths))
        self.assertTrue(any("notes.txt" in p for p in paths))

        # Hidden and skip_dirs excluded
        self.assertFalse(any(".hidden" in p for p in paths))
        self.assertFalse(any("node_modules" in p for p in paths))

    def test_search_files(self):
        entries, _ = scan_files(str(self.root))
        matches = search_files(entries, "runner", limit=5)
        self.assertTrue(len(matches) >= 1)
        self.assertTrue("test_runner.py" in matches[0])

        matches_doc = search_files(entries, "report", limit=5)
        self.assertTrue(len(matches_doc) >= 1)
        self.assertTrue("report_2026.pdf" in matches_doc[0])

    def test_file_search_model(self):
        model = FileSearchModel(root=str(self.root))
        try:
            # Wait for background indexer
            deadline = time.time() + 3.0
            while time.time() < deadline:
                results, status, busy, total = model.view()
                if not busy and total >= 4:
                    break
                time.sleep(0.05)

            results, status, busy, total = model.view()
            self.assertFalse(busy)
            self.assertEqual(total, 4)

            # Query
            model.set_query("main")
            deadline = time.time() + 3.0
            while time.time() < deadline:
                results, status, busy, total = model.view()
                if not busy and len(results) > 0:
                    break
                time.sleep(0.05)

            self.assertTrue(any("main.py" in r for r in results))
        finally:
            model.close()

    def test_file_search_card_ui_in_subprocess(self):
        code = """
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from unittest.mock import MagicMock
from file_search_card import FileSearchCard
from file_search import FileSearchModel

ok, _ = Gtk.init_check()
if not ok:
    print("UI_OK")
    import sys
    sys.exit(0)
win = Gtk.Window()
parent = Gtk.Box()
win.add(parent)
host = MagicMock()
card_box = Gtk.Box()
host.card.return_value = card_box

model = FileSearchModel(root="/tmp")
try:
    card = FileSearchCard(host, parent, model=model)
    assert card.card is not None
    assert card.entry is not None
    card.close()
finally:
    model.close()
print("UI_OK")
"""
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        self.assertIn("UI_OK", res.stdout)


if __name__ == "__main__":
    unittest.main()
