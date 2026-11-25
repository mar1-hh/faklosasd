"""Unit tests for smart app launcher model and dock widget."""
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app_launcher import AppLauncherModel, AppEntry, fuzzy_score

ROOT = Path(__file__).resolve().parents[1]


class MockAppInfo:
    def __init__(self, app_id, name, display_name="", desc="", exe=""):
        self._id = app_id
        self._name = name
        self._display = display_name or name
        self._desc = desc
        self._exe = exe

    def should_show(self):
        return True

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def get_display_name(self):
        return self._display

    def get_description(self):
        return self._desc

    def get_executable(self):
        return self._exe

    def get_icon(self):
        return None

    def launch(self, files, context):
        return True


class TestAppLauncher(unittest.TestCase):
    def setUp(self):
        self.mock_apps = [
            MockAppInfo("firefox.desktop", "Firefox Web Browser", "Firefox", "Browse the web", "firefox"),
            MockAppInfo("org.gnome.Terminal.desktop", "Terminal", "Terminal", "Use the command line", "gnome-terminal"),
            MockAppInfo("code.desktop", "Visual Studio Code", "Code", "Code editor", "code"),
            MockAppInfo("spotify.desktop", "Spotify Music", "Spotify", "Play music", "spotify"),
        ]
        self.model = AppLauncherModel(app_resolver=lambda: self.mock_apps)

    def test_fuzzy_score(self):
        self.assertEqual(fuzzy_score("term", "Terminal"), 800 - len("Terminal"))
        self.assertGreater(fuzzy_score("fire", "Firefox"), 100)
        self.assertEqual(fuzzy_score("", "anything"), 0)

    def test_search_apps(self):
        results = self.model.search("code")
        self.assertTrue(any(app.id == "code.desktop" for app in results))

        results_term = self.model.search("terminal")
        self.assertTrue(any(app.id == "org.gnome.Terminal.desktop" for app in results_term))

        empty = self.model.search("nonexistentapplicationxyz")
        self.assertEqual(len(empty), 0)

    def test_favorites(self):
        favs = self.model.get_favorites(["firefox.desktop", "spotify.desktop"])
        self.assertEqual(len(favs), 2)
        self.assertEqual(favs[0].id, "firefox.desktop")
        self.assertEqual(favs[1].id, "spotify.desktop")

    def test_launch_app(self):
        entry = self.model.search("firefox")[0]
        success, msg = self.model.launch(entry)
        self.assertTrue(success)
        self.assertIn("Launched", msg)

    def test_launcher_card_widget_subprocess(self):
        script = """
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from app_launcher import AppLauncherModel
from launcher_card import LauncherCard
from tests.test_app_launcher import MockAppInfo

apps = [
    MockAppInfo("firefox.desktop", "Firefox Web Browser", "Firefox", "Browse the web", "firefox"),
    MockAppInfo("code.desktop", "Visual Studio Code", "Code", "Code editor", "code"),
]
model = AppLauncherModel(app_resolver=lambda: apps)

ok, _ = Gtk.init_check()
if not ok:
    import sys
    sys.exit(0)
win = Gtk.Window()
parent = Gtk.Box()
win.add(parent)
class MockHost:
    def card(self, p, title):
        box = Gtk.Box()
        p.pack_start(box, False, False, 0)
        return box

card = LauncherCard(MockHost(), parent, model=model, page_size=2)
assert "launcher-dock-card" in card.card.get_style_context().list_classes()
assert card.esc_badge is not None
assert len(card.displayed_apps) >= 2
card.search_entry.set_text("code")
assert any(app.id == "code.desktop" for app in card.displayed_apps)
card.search_entry.set_text("")
assert card.search_query == ""
"""
        result = subprocess.run(
            ['/usr/bin/python3', '-c', script],
            cwd=ROOT,
            env=dict(os.environ, GSETTINGS_BACKEND='memory'),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
