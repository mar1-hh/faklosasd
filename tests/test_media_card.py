"""Isolate GTK 3 from the GTK 4 Control Center tests in discovery."""
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestMediaCard(unittest.TestCase):
    def test_media_card_regressions_in_subprocess(self):
        result = subprocess.run(
            ['/usr/bin/python3', '-m', 'unittest', 'tests.media_card_cases', '-v'],
            cwd=ROOT, env=dict(os.environ, GSETTINGS_BACKEND='memory'),
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        # Keep the real pass/skip counts visible in the full discovery log.
        print(result.stderr, end='')
