"""Keep-awake lifecycle tests: no real key events or desktop startup changes."""
from pathlib import Path
import json,os,signal,sys,tempfile,unittest,subprocess
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import preferences
import keep_awake
import sc

class Clock:
 def __init__(self):self.value=0
 def now(self):return self.value
 def wait(self,seconds):self.value+=seconds;return False
class Keyboard:
 def __init__(self,fail=False):self.events=[];self.fail=fail
 def press(self,key):
  self.events.append(('press',key))
  if self.fail:raise RuntimeError('input error')
 def release(self,key):self.events.append(('release',key))
class KeepAwakeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'state').mkdir()
  self.patch_root=patch.object(keep_awake,'ROOT',self.root);self.patch_root.start()
  self.patch_file=patch.object(preferences,'FILE',self.root/'state/preferences.json');self.patch_file.start()
  self.patch_env=patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.root/'config')});self.patch_env.start()
  (self.root/'keep-awake-python').symlink_to(sys.executable)
 def tearDown(self):self.patch_env.stop();self.patch_file.stop();self.patch_root.stop();self.tmp.cleanup()
 def test_default_is_enabled_and_explicit_off_survives_load(self):
  self.assertTrue(preferences.load()['keep_awake_enabled'])
  preferences.update({'keep_awake_enabled':False});self.assertFalse(preferences.load()['keep_awake_enabled'])
 def test_login_entry_has_absolute_paths_and_zero_delay(self):
  keep_awake.configure_startup(True);text=keep_awake.entry_path().read_text()
  self.assertIn(str(self.root/'sc.py'),text);self.assertIn('--managed',text)
  self.assertIn('X-GNOME-Autostart-Delay=0',text)
  self.assertIn(str(Path(sys.executable).resolve()),text)
 def test_disable_removes_entry_and_stops_verified_helper(self):
  keep_awake.configure_startup(True)
  with patch.object(keep_awake,'running_pid',return_value=12345),patch.object(keep_awake.os,'kill') as kill:
   keep_awake.set_enabled(False);kill.assert_called_once_with(12345,signal.SIGTERM)
  self.assertFalse(preferences.load()['keep_awake_enabled']);self.assertFalse(keep_awake.entry_path().exists())
 def test_unknown_startup_entry_is_not_overwritten(self):
  entry=keep_awake.entry_path();entry.parent.mkdir(parents=True);entry.write_text('unrelated')
  with self.assertRaises(RuntimeError):keep_awake.configure_startup(True)
  self.assertEqual(entry.read_text(),'unrelated')
 def test_enabled_switch_starts_helper(self):
  with patch.object(keep_awake,'start',return_value='started') as start:
   self.assertEqual(keep_awake.set_enabled(True),'started');start.assert_called_once()
  self.assertTrue(keep_awake.entry_path().exists())
 def test_start_uses_pinned_interpreter_and_detached_managed_script(self):
  with patch.object(keep_awake,'running_pid',return_value=None),patch.object(keep_awake.subprocess,'Popen') as popen:
   popen.return_value.wait.side_effect=subprocess.TimeoutExpired('sc',.5)
   keep_awake.start()
   args=popen.call_args.args[0]
   self.assertEqual(args[-2:],[str(self.root/'sc.py'),'--managed'])
   self.assertTrue(popen.call_args.kwargs['start_new_session'])
 def test_disabled_setting_never_starts_a_helper(self):
  preferences.update({'keep_awake_enabled':False})
  with patch.object(keep_awake.subprocess,'Popen') as popen:
   keep_awake.start();popen.assert_not_called()
 def test_finished_run_status_does_not_restart_it(self):
  (self.root/'state/keep-awake-status.json').write_text(json.dumps({'state':'finished'}))
  with patch.object(keep_awake,'running_pid',return_value=None),patch.object(keep_awake,'start') as start:
   self.assertIn('finished',keep_awake.status_text());start.assert_not_called()
 def test_no_events_before_first_interval_and_duration_ends(self):
  keyboard=Keyboard();clock=Clock()
  result=sc.run_events(keyboard,'shift',minutes=1,interval=30,clock=clock.now,wait=clock.wait)
  self.assertEqual(result,'finished')
  self.assertEqual(keyboard.events,[('press','shift'),('release','shift')])
  self.assertEqual(clock.value,60)
 def test_disabled_preference_produces_no_keys(self):
  keyboard=Keyboard();clock=Clock()
  self.assertEqual(sc.run_events(keyboard,'shift',enabled=lambda:False,clock=clock.now,wait=clock.wait),'disabled')
  self.assertEqual(keyboard.events,[])
 def test_switch_off_is_seen_within_one_second(self):
  keyboard=Keyboard();clock=Clock()
  result=sc.run_events(keyboard,'shift',enabled=lambda:clock.value<3,clock=clock.now,wait=clock.wait)
  self.assertEqual(result,'disabled');self.assertEqual(clock.value,3);self.assertEqual(keyboard.events,[])
 def test_shift_is_released_when_press_fails(self):
  keyboard=Keyboard(fail=True);clock=Clock()
  with self.assertRaises(RuntimeError):sc.run_events(keyboard,'shift',clock=clock.now,wait=clock.wait)
  self.assertEqual(keyboard.events[-1],('release','shift'))
 def test_stop_request_cancels_before_any_event(self):
  keyboard=Keyboard();clock=Clock()
  self.assertEqual(sc.run_events(keyboard,'shift',wait=lambda _:True,clock=clock.now),'stopped')
  self.assertFalse(keyboard.events)
 def test_stale_pid_is_not_signalled(self):
  (self.root/'state/keep-awake.pid').write_text('9999999999')
  with patch.object(keep_awake.os,'kill') as kill:keep_awake.stop();kill.assert_not_called()
 def test_unrecognized_legacy_entry_is_preserved(self):
  legacy=keep_awake.entry_path().parent/'neon-sc-login.desktop';legacy.parent.mkdir(parents=True);legacy.write_text('other')
  keep_awake.migrate_standalone();self.assertTrue(legacy.exists())
 def test_marked_standalone_entry_is_backed_up(self):
  legacy=keep_awake.entry_path().parent/'neon-sc-login.desktop';legacy.parent.mkdir(parents=True);legacy.write_text('X-Neon-SC-Managed=true\n')
  with patch.object(keep_awake.subprocess,'run',side_effect=OSError('no process scanner')):keep_awake.migrate_standalone()
  self.assertFalse(legacy.exists());self.assertTrue((self.root/'state/standalone-sc-startup-before.desktop').exists())
 def test_missing_old_pynput_pin_uses_system_python(self):
  (self.root/'keep-awake-python').unlink()
  self.assertEqual(keep_awake.interpreter(),Path('/usr/bin/python3'))
  keep_awake.configure_startup(True)
  self.assertIn('/usr/bin/python3',keep_awake.entry_path().read_text())
if __name__=='__main__':unittest.main()
