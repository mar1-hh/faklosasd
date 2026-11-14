"""Personal-profile setup tests; all files/services are isolated fakes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_wallpaper import NativeWallpaper,WallpaperError

class Service:
 def __init__(self):
  self.calls=[];self.fail_reload=False
  self.values={'picture-uri':'file:///before.png','picture-uri-dark':'file:///before.png','picture-options':'zoom'}
 def __call__(self,args,**kwargs):
  self.calls.append((args,kwargs['env']))
  output='';code=0;error=''
  if args[0]=='gsettings':
   action,key=args[1],args[3]
   if action=='writable':output='true\n'
   elif action=='get':output=repr(self.values[key])+'\n'
   else:
    import ast
    self.values[key]=ast.literal_eval(args[4])
  elif 'is-active' in args:code=0 if 'x11' in args[-1] else 3
  elif 'daemon-reload' in args and self.fail_reload:code=1;error='reload failed'
  elif '--property=MainPID' in args:output='0\n'
  return subprocess.CompletedProcess(args,code,output,error)

class NativeWallpaperTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.service=Service()
  self.native=NativeWallpaper(self.root,self.service)
 def tearDown(self):self.tmp.cleanup()
 def test_profile_is_user_scoped_and_does_not_mutate_app_environment(self):
  before=dict(os.environ);self.native.prepare_profile()
  self.assertTrue(self.native.profile.read_text().startswith(self.native.MARKER))
  self.assertIn('user-db:user',self.native.profile.read_text())
  self.assertEqual(dict(os.environ),before)
 def test_preserves_selected_user_database_name(self):
  source=self.root/'source-profile';source.write_text('user-db:personal\nsystem-db:local\n')
  self.native.original_env['DCONF_PROFILE']=str(source);self.native.prepare_profile()
  self.assertEqual(self.native.profile.read_text(),self.native.MARKER+'user-db:personal\n')
 def test_unknown_profile_is_not_overwritten(self):
  self.native.profile.parent.mkdir();self.native.profile.write_text('existing profile')
  with self.assertRaises(WallpaperError):self.native.prepare_profile()
  self.assertEqual(self.native.profile.read_text(),'existing profile')
 def test_symlink_profile_is_not_followed(self):
  self.native.profile.parent.mkdir();self.native.profile.symlink_to(self.root/'missing')
  with self.assertRaises(WallpaperError):self.native.prepare_profile()
 def test_setup_writes_dropin_and_reports_pending_login(self):
  with patch('native_wallpaper.os.geteuid',return_value=1000):pending=self.native.ensure_setup()
  override=self.native.override_path('org.gnome.Shell@x11.service')
  self.assertTrue(pending);self.assertTrue(override.exists())
  self.assertIn('DCONF_PROFILE=',override.read_text())
  self.assertTrue(any('daemon-reload' in args for args,env in self.service.calls))
  self.assertFalse(any('restart' in args for args,env in self.service.calls))
 def test_setup_is_idempotent(self):
  with patch('native_wallpaper.os.geteuid',return_value=1000):self.native.ensure_setup();self.native.ensure_setup()
  self.assertEqual(sum('daemon-reload' in args for args,env in self.service.calls),1)
 def test_failed_reload_removes_new_override(self):
  self.service.fail_reload=True
  with patch('native_wallpaper.os.geteuid',return_value=1000),self.assertRaises(WallpaperError):self.native.ensure_setup()
  self.assertFalse(self.native.override_path('org.gnome.Shell@x11.service').exists())
 def test_conflicting_service_profile_is_preserved(self):
  directory=self.native.override_path('org.gnome.Shell@x11.service').parent;directory.mkdir(parents=True)
  foreign=directory/'wallpaper-profile.conf';foreign.write_text('[Service]\nEnvironment=DCONF_PROFILE=/other/profile\n')
  with patch('native_wallpaper.os.geteuid',return_value=1000),self.assertRaises(WallpaperError):self.native.ensure_setup()
  self.assertTrue(foreign.exists());self.assertFalse(self.native.override_path('org.gnome.Shell@x11.service').exists())
 def test_settings_commands_use_personal_profile_only(self):
  self.assertTrue(self.native.is_writable('picture-uri'))
  self.native.set_string('picture-uri','file:///a%20picture.png')
  self.assertEqual(self.native.get_string('picture-uri'),'file:///a%20picture.png')
  for args,env in self.service.calls:self.assertEqual(env['DCONF_PROFILE'],str(self.native.profile))
 def test_original_wallpaper_read_uses_original_environment(self):
  self.native.get_original('picture-uri')
  self.assertEqual(self.service.calls[-1][1],self.native.original_env)
 def test_disable_only_removes_owned_override(self):
  with patch('native_wallpaper.os.geteuid',return_value=1000):self.native.ensure_setup()
  override=self.native.override_path('org.gnome.Shell@x11.service');other=override.parent/'unrelated.conf';other.write_text('[Service]\n')
  self.native.disable_setup();self.assertFalse(override.exists());self.assertTrue(other.exists())
  self.assertTrue(self.native.profile.exists()) # Leave it readable until next login.
 def test_disable_rollback_retains_existing_override_on_reload_failure(self):
  with patch('native_wallpaper.os.geteuid',return_value=1000):self.native.ensure_setup()
  override=self.native.override_path('org.gnome.Shell@x11.service');before=override.read_text();self.service.fail_reload=True
  with self.assertRaises(WallpaperError):self.native.disable_setup()
  self.assertEqual(override.read_text(),before)

if __name__=='__main__':unittest.main()
