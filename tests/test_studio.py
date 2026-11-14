"""Headless regression tests for saved preferences and wallpaper transactions."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import preferences as prefs
import studio_backend as backend
from live_logtime import live_hours,format_hours
from launchers import available_apps
ROOT=prefs.ROOT
spec=importlib.util.spec_from_file_location('studio_control',ROOT/'control-center.py')
studio=importlib.util.module_from_spec(spec);spec.loader.exec_module(studio)

class FakeSettings:
 def __init__(self,locked=False,fail=None):
  self.locked=locked;self.fail=fail;self.calls=[]
  self.values={'picture-uri':'file:///before.png','picture-uri-dark':'file:///before-dark.png','picture-options':'scaled'}
 def is_writable(self,key):return not self.locked
 def get_string(self,key):return self.values[key]
 def set_string(self,key,value):
  self.calls.append((key,value))
  if key==self.fail:return False
  self.values[key]=value;return True

class StudioTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'state').mkdir()
  self.path=patch.object(prefs,'FILE',self.root/'state/preferences.json');self.path.start()
 def tearDown(self):self.path.stop();self.tmp.cleanup()
 def test_missing_optional_app_cannot_crash_launcher(self):
  def resolver(name):
   if name=='code.desktop':raise TypeError('constructor returned NULL')
   return name
  apps=available_apps(resolver)
  self.assertEqual([title for title,app in apps],['Web','Files','Terminal'])
 def test_no_installed_launchers_is_allowed(self):
  self.assertEqual(available_apps(lambda _:None),[])
 def test_preferences_preserve_other_controls(self):
  prefs.update({'notes':'Ship it.','accent':'Teal','visible':{'clock':False}})
  prefs.update({'scale':1.6})
  current=prefs.load()
  self.assertEqual(current['notes'],'Ship it.');self.assertEqual(current['accent'],'Teal')
  self.assertFalse(current['visible']['clock']);self.assertTrue(current['visible']['logtime'])
 def test_invalid_preferences_are_safe(self):
  prefs.FILE.write_text('{broken');self.assertEqual(prefs.load()['target_hours'],120)
  prefs.save({'scale':float('nan'),'opacity':-20,'margin':20000,'username':'bad;command','positions':{'clock':['bad',2],'system':[12,40]}})
  result=prefs.load();self.assertEqual(result['scale'],1.3);self.assertEqual(result['opacity'],.3)
  self.assertEqual(result['margin'],200);self.assertEqual(result['username'],'')
  self.assertEqual(result['positions'],{'system':[12,40]})
 def test_restore_keeps_original_snapshot(self):
  with patch.object(backend,'ROOT',self.root):
   prefs.update({'notes':'Before'});backend.backup_preferences()
   prefs.update({'notes':'After'});backend.backup_preferences();backend.restore_preferences()
   self.assertEqual(prefs.load()['notes'],'Before')
 def test_wallpaper_discovery_handles_spaces_and_filters(self):
  for name in ('My Picture.PNG','notes.txt','night.webp'):(self.root/name).touch()
  self.assertEqual([p.name for p in backend.wallpapers(self.root)],['My Picture.PNG','night.webp'])
  self.assertEqual(backend.wallpapers(self.root/'missing'),[])
 def fake_window(self,settings):
  image=self.root/'image.png';image.touch()
  win=SimpleNamespace(bg=settings,selected=image,messages=[])
  win.notify=win.messages.append;win.wallpaper_writable=lambda:studio.Studio.wallpaper_writable(win)
  return win
 def test_locked_wallpaper_does_not_write(self):
  win=self.fake_window(FakeSettings(locked=True))
  with patch.object(studio,'ROOT',self.root):studio.Studio.apply_wallpaper(win)
  self.assertEqual(win.bg.calls,[]);self.assertFalse((self.root/'state/wallpaper-before.json').exists())
 def test_failed_wallpaper_rolls_back_completed_write(self):
  settings=FakeSettings(fail='picture-uri-dark');win=self.fake_window(settings)
  with patch.object(studio,'ROOT',self.root):studio.Studio.apply_wallpaper(win)
  self.assertEqual(settings.values['picture-uri'],'file:///before.png')
  self.assertIn('rejected',win.messages[-1])
 def test_successful_wallpaper_has_restorable_backup(self):
  settings=FakeSettings();win=self.fake_window(settings)
  with patch.object(studio,'ROOT',self.root),patch.object(studio,'Gio',SimpleNamespace(Settings=SimpleNamespace(sync=lambda:None))):
   studio.Studio.apply_wallpaper(win)
  saved=json.loads((self.root/'state/wallpaper-before.json').read_text())
  self.assertEqual(saved['picture-uri'],'file:///before.png')
  self.assertEqual(settings.values['picture-uri-dark'],win.selected.as_uri())
 def test_live_session_not_added_twice(self):
  data={'snapshot_time':1000,'session_detected':True,'hours':{'projected':74,'session':2}}
  self.assertEqual(format_hours(live_hours(data,1061)['projected']),'74:01:01')
  fresh={'snapshot_time':1061,'session_detected':True,'hours':{'projected':75,'session':3}}
  self.assertEqual(format_hours(live_hours(fresh,1062)['projected']),'75:00:01')
 def test_settings_launcher(self):
  subprocess.run(['/usr/bin/python3',str(ROOT/'install-settings.py')],env=dict(os.environ,XDG_DATA_HOME=str(self.root)),check=True,capture_output=True)
  app=studio.Gio.DesktopAppInfo.new_from_filename(str(self.root/'applications/neon-desktop-settings.desktop'))
  self.assertIsNotNone(app);self.assertIn('control-center.py',app.get_commandline())
 def test_autostart_only_removes_our_entry(self):
  with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.root)}):
   entry=backend.autostart_path();entry.parent.mkdir(parents=True);entry.write_text('unrelated program')
   backend.set_autostart(False);self.assertTrue(entry.exists())
   entry.write_text(str(ROOT/'desktop-widgets.py'));backend.set_autostart(False);self.assertFalse(entry.exists())

if __name__=='__main__':unittest.main()
