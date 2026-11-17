import os
from pathlib import Path
import tempfile
import unittest
from session_environment import graphical_environment

class SessionEnvironment(unittest.TestCase):
 def test_current_shell_replaces_stale_auth_without_reading_cookie(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);shell=root/'123';shell.mkdir();auth=root/'authority';auth.touch()
   (shell/'comm').write_text('gnome-shell\n')
   (shell/'environ').write_bytes(f'DISPLAY=:1\0XAUTHORITY={auth}\0SECRET=private\0'.encode())
   result=graphical_environment({'DISPLAY':':0','XAUTHORITY':'stale','OTHER':'keep'},root)
   self.assertEqual(result['DISPLAY'],':1');self.assertEqual(result['XAUTHORITY'],str(auth))
   self.assertEqual(result['OTHER'],'keep');self.assertNotIn('SECRET',result)
 def test_absent_or_ambiguous_sessions_preserve_environment(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);env={'DISPLAY':':0','XAUTHORITY':'original'}
   self.assertEqual(graphical_environment(env,root),env)
   for number in (1,2):
    shell=root/str(number);shell.mkdir();(shell/'comm').write_text('gnome-shell')
    (shell/'environ').write_bytes(f'DISPLAY=:{number}\0'.encode())
   self.assertEqual(graphical_environment(env,root),env)
 def test_matching_session_with_default_auth_removes_stale_override(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);shell=root/'1';shell.mkdir();(shell/'comm').write_text('gnome-shell')
   (shell/'environ').write_bytes(b'DISPLAY=:0\0')
   result=graphical_environment({'DISPLAY':':0','XAUTHORITY':'stale'},root)
   self.assertNotIn('XAUTHORITY',result)
