"""Unit tests for device_controls.py audio, brightness, and system metrics."""
import unittest
from unittest.mock import MagicMock, patch

from device_controls import AudioController, BrightnessController, SystemMetrics


class TestDeviceControls(unittest.TestCase):
    def test_audio_controller_mock_pulse(self):
        with patch("shutil.which", return_value="/usr/bin/pactl"), \
             patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="Volume: front-left: 36421 / 56% / -15.31 dB\n", returncode=0),
                MagicMock(stdout="Mute: no\n", returncode=0),
            ]
            audio = AudioController()
            self.assertTrue(audio.is_available())
            vol, muted = audio.get_state()
            self.assertEqual(vol, 56)
            self.assertFalse(muted)

    def test_brightness_controller(self):
        with patch("gi.repository.Gio.bus_get_sync") as mock_bus_get:
            mock_bus = MagicMock()
            mock_bus_get.return_value = mock_bus
            mock_reply = MagicMock()
            mock_reply.unpack.return_value = (42,)
            mock_bus.call_sync.return_value = mock_reply

            b = BrightnessController()
            val = b.get_brightness()
            self.assertEqual(val, 42)
            self.assertTrue(b.available)

            b.set_brightness(75)
            mock_bus.call_sync.assert_called()

    def test_system_metrics(self):
        metrics = SystemMetrics().get_metrics()
        self.assertIn("ram_pct", metrics)
        self.assertIn("disk_pct", metrics)
        self.assertIn("load_1m", metrics)
        self.assertGreaterEqual(metrics["disk_free_gb"], 0.0)


if __name__ == "__main__":
    unittest.main()
