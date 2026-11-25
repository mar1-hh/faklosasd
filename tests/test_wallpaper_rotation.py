"""Unit tests for wallpaper_rotation.py."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wallpaper_rotation import WallpaperRotationManager


class TestWallpaperRotation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.manager = WallpaperRotationManager(root=self.root)
        self.manager.history_file = self.root / "history.json"
        self.manager.favorites_file = self.root / "favorites.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_history_recording_and_previous(self):
        p1 = "/path/to/wall1.png"
        p2 = "/path/to/wall2.png"
        p3 = "/path/to/wall3.png"

        self.manager.record_history(p1)
        self.manager.record_history(p2)
        self.manager.record_history(p3)

        self.assertEqual(len(self.manager.get_history()), 3)

        with patch("wallpaper_rotation.load", return_value={"active_wallpaper": p3}):
            prev = self.manager.get_previous()
            self.assertEqual(prev, p2)

    def test_favorites_toggle(self):
        p = "/path/to/wall.png"
        self.assertFalse(self.manager.is_favorite(p))

        added = self.manager.toggle_favorite(p)
        self.assertTrue(added)
        self.assertTrue(self.manager.is_favorite(p))

        removed = self.manager.toggle_favorite(p)
        self.assertFalse(removed)
        self.assertFalse(self.manager.is_favorite(p))

    def test_rotation_interval_logic(self):
        with patch("wallpaper_rotation.load", return_value={"rotate_hours": 0}):
            self.assertFalse(self.manager.should_rotate())

        with patch("wallpaper_rotation.load", return_value={"rotate_hours": 1}):
            self.manager.last_rotate_time = 0
            self.assertTrue(self.manager.should_rotate())


if __name__ == "__main__":
    unittest.main()
