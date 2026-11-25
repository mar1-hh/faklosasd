"""Unit tests for the unified neon CLI tool."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEON_CLI = ROOT / "neon"


class TestNeonCLI(unittest.TestCase):
    def run_cli(self, args):
        cmd = [sys.executable, str(NEON_CLI)] + args
        return subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_neon_status_text(self):
        res = self.run_cli(["status"])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("NEON STUDIO STATUS", res.stdout)
        self.assertIn("Widgets:", res.stdout)
        self.assertIn("Keep-Awake:", res.stdout)
        self.assertIn("RAM Usage:", res.stdout)

    def test_neon_status_json(self):
        res = self.run_cli(["status", "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertIn("widgets", data)
        self.assertIn("keep_awake", data)
        self.assertIn("theme", data)
        self.assertIn("wallpaper", data)
        self.assertIn("storage", data)
        self.assertIn("system", data)

    def test_neon_widgets_list_and_toggle(self):
        res_list = self.run_cli(["widgets", "list"])
        self.assertEqual(res_list.returncode, 0, res_list.stderr)
        self.assertIn("logtime", res_list.stdout)
        self.assertIn("media", res_list.stdout)
        self.assertIn("search", res_list.stdout)

        # Toggle search widget
        res_toggle1 = self.run_cli(["widgets", "toggle", "search"])
        self.assertEqual(res_toggle1.returncode, 0)
        self.assertIn("Widget 'search' is now", res_toggle1.stdout)

        # Toggle back
        res_toggle2 = self.run_cli(["widgets", "toggle", "search"])
        self.assertEqual(res_toggle2.returncode, 0)

    def test_neon_clean_dry_run(self):
        res = self.run_cli(["clean"])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("cache targets", res.stdout)
        self.assertIn("Dry run", res.stdout)

    def test_neon_goinfre_status(self):
        res = self.run_cli(["goinfre", "status"])
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_neon_awake_mode(self):
        res = self.run_cli(["awake", "mode", "mouse"])
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_neon_theme_dark(self):
        res = self.run_cli(["theme", "dark"])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Applied dark theme mode", res.stdout)


if __name__ == "__main__":
    unittest.main()
