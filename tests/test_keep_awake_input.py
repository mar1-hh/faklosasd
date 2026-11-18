import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from keep_awake_input import X11Keyboard

class NativeInput(unittest.TestCase):
 def setUp(self):
  self.x=SimpleNamespace(**{name:Mock(return_value=value) for name,value in {'XOpenDisplay':123,'XCloseDisplay':0,'XStringToKeysym':0xffe1,'XKeysymToKeycode':50,'XQueryKeymap':1,'XFlush':0}.items()})
  self.xt=SimpleNamespace(XTestQueryExtension=Mock(return_value=1),XTestFakeKeyEvent=Mock(return_value=1))
  self.env=patch.dict(os.environ,{'XDG_SESSION_TYPE':'x11'});self.env.start();self.addCleanup(self.env.stop)
 def keyboard(self):return X11Keyboard(loader=lambda name:self.x if name=='libX11.so.6' else self.xt)
 def test_native_shift_pair_and_cleanup(self):
  keyboard=self.keyboard();keyboard.press('shift');keyboard.release('shift');keyboard.close()
  self.assertEqual([call.args[2] for call in self.xt.XTestFakeKeyEvent.call_args_list],[1,0])
  self.x.XCloseDisplay.assert_called_once_with(123)
 def test_close_releases_held_shift(self):
  keyboard=self.keyboard();keyboard.press('shift');keyboard.close();keyboard.close()
  self.assertEqual([call.args[2] for call in self.xt.XTestFakeKeyEvent.call_args_list],[1,0])
 def test_user_held_shift_is_not_released(self):
  def held(display,buffer):buffer[50//8]=bytes([1<<(50%8)]);return 1
  self.x.XQueryKeymap.side_effect=held
  keyboard=self.keyboard();keyboard.press('shift');keyboard.release('shift');keyboard.close()
  self.xt.XTestFakeKeyEvent.assert_not_called()
 def test_display_failure_is_actionable(self):
  self.x.XOpenDisplay.return_value=None
  with self.assertRaisesRegex(RuntimeError,'active desktop session'):self.keyboard()
 def test_missing_xtest_closes_connection(self):
  self.xt.XTestQueryExtension.return_value=0
  with self.assertRaisesRegex(RuntimeError,'XTest'):self.keyboard()
  self.x.XCloseDisplay.assert_called_once()
 def test_missing_library_and_wayland_report_limits(self):
  with self.assertRaisesRegex(RuntimeError,'libraries'):X11Keyboard(loader=Mock(side_effect=OSError('missing')))
  with patch.dict(os.environ,{'XDG_SESSION_TYPE':'wayland'}):
   with self.assertRaisesRegex(RuntimeError,'X11 session'):self.keyboard()
 def test_rejected_event_does_not_report_pressed(self):
  keyboard=self.keyboard();self.xt.XTestFakeKeyEvent.return_value=0
  with self.assertRaisesRegex(RuntimeError,'rejected'):keyboard.press('shift')
  self.assertFalse(keyboard.pressed);keyboard.close()
