"""Unit tests for theme_manager.py."""
import tempfile
import unittest
from pathlib import Path

from theme_manager import ThemeManager, relative_luminance, hex_to_rgb, rgb_to_hex


class TestThemeManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.hooks_dir = Path(self.temp_dir.name)
        self.manager = ThemeManager(hooks_dir=self.hooks_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_luminance_and_on_accent_contrast(self):
        # White has high luminance -> on_accent should be dark
        pal_white = self.manager.build_palette("#ffffff", mode="dark")
        self.assertEqual(pal_white["on_accent"], "#131018")

        # Dark blue has low luminance -> on_accent should be white
        pal_dark = self.manager.build_palette("#112244", mode="dark")
        self.assertEqual(pal_dark["on_accent"], "#ffffff")

    def test_light_mode_palette(self):
        pal = self.manager.build_palette("#dfa1c6", mode="light")
        self.assertEqual(pal["mode"], "light")
        self.assertEqual(pal["paper"], "#faf8fb")
        self.assertEqual(pal["ink"], "#1a1620")

    def test_execute_hooks(self):
        hook_script = self.hooks_dir / "01-test-hook.sh"
        hook_script.write_text("""#!/bin/sh
if [ "$NEON_ACCENT" = "#73d7c2" ]; then
    exit 0
else
    exit 2
fi
""")
        hook_script.chmod(0o755)

        pal = {"mode": "dark", "accent": "#73d7c2"}
        results = self.manager.execute_hooks(pal, wallpaper_path="/test/path.png")
        self.assertEqual(len(results), 1)
        self.assertIn("OK", results[0])


if __name__ == "__main__":
    unittest.main()
