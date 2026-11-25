"""Unit tests for multi-mode Keep-Awake engine."""
import unittest
from unittest.mock import MagicMock, patch

from keep_awake_input import KeepAwakeController, GnomeInhibitor, X11Pointer, X11Keyboard
import keep_awake


class TestKeepAwakeModes(unittest.TestCase):
    def test_controller_inhibit_mode(self):
        with patch("keep_awake_input.GnomeInhibitor") as mock_inhibit:
            inst = mock_inhibit.return_value
            inst.cookie = 9999

            controller = KeepAwakeController(mode="inhibit")
            self.assertEqual(controller.mode, "inhibit")
            self.assertIsNone(controller.input_backend)
            self.assertTrue(controller.pulse())
            controller.close()
            inst.close.assert_called_once()

    def test_controller_mouse_mode_pulse(self):
        with patch("keep_awake_input.GnomeInhibitor"), \
             patch("keep_awake_input.X11Pointer") as mock_pointer:
            p_inst = mock_pointer.return_value
            p_inst.pulse.return_value = True

            controller = KeepAwakeController(mode="mouse")
            self.assertEqual(controller.mode, "mouse")
            self.assertTrue(controller.pulse())
            p_inst.pulse.assert_called_once()
            controller.close()
            p_inst.close.assert_called_once()

    def test_controller_shift_mode(self):
        with patch("keep_awake_input.GnomeInhibitor"), \
             patch("keep_awake_input.X11Keyboard") as mock_kb:
            kb_inst = mock_kb.return_value

            controller = KeepAwakeController(mode="shift")
            self.assertEqual(controller.mode, "shift")
            controller.pulse()
            kb_inst.pulse.assert_called_once()
            controller.close()
            kb_inst.close.assert_called_once()

    def test_status_text_formatting(self):
        with patch("keep_awake.load", return_value={"keep_awake_enabled": True}), \
             patch("keep_awake.running_pid", return_value=1234), \
             patch("pathlib.Path.read_text", return_value='{"interval": 30, "method": "mouse"}'):
            status = keep_awake.status_text()
            self.assertIn("Pointer excursion", status)
            self.assertIn("30s", status)


if __name__ == "__main__":
    unittest.main()
