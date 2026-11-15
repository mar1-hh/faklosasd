"""Installing an update must not leave login pointing at the old checkout."""
from pathlib import Path
import os,shutil,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import studio_backend
from startup_entries import widget_target,is_enabled
SOURCE=Path(__file__).resolve().parents[1]
class StartupMigrationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'new checkout';self.root.mkdir()
  for name in ('install-dashboard.py','startup_entries.py'):shutil.copy2(SOURCE/name,self.root/name)
  self.root_patch=patch.object(studio_backend,'ROOT',self.root);self.root_patch.start()
  self.env_patch=patch.dict(os.environ,{'XDG_CONFIG_HOME':str(Path(self.tmp.name)/'config')});self.env_patch.start()
  self.entry=studio_backend.autostart_path();self.entry.parent.mkdir(parents=True)
 def tearDown(self):self.env_patch.stop();self.root_patch.stop();self.tmp.cleanup()
 def old_entry(self,enabled=True,name='Neon Desktop Widgets'):
  text='[Desktop Entry]\nType=Application\nName='+name+'\nExec=/usr/bin/python3 "/old checkout/neon-desktop/desktop-widgets.py"\nX-GNOME-Autostart-enabled='+str(enabled).lower()+'\n'
  self.entry.write_text(text);return text
 def test_enabled_old_entry_is_retargeted_without_becoming_uninstall_restore(self):
  original=self.old_entry();studio_backend.refresh_widget_autostart()
  self.assertEqual(widget_target(self.entry.read_text()),self.root/'desktop-widgets.py')
  self.assertTrue(is_enabled(self.entry.read_text()))
  self.assertEqual((self.root/'state/login-target-before.desktop').read_text(),original)
  self.assertFalse((self.root/'state/dashboard-autostart-before').exists())
 def test_explicitly_disabled_startup_is_not_reenabled(self):
  original=self.old_entry(enabled=False);studio_backend.refresh_widget_autostart();self.assertEqual(self.entry.read_text(),original)
 def test_unrelated_entry_is_preserved(self):
  original=self.old_entry(name='Other app');studio_backend.refresh_widget_autostart();self.assertEqual(self.entry.read_text(),original)
 def test_absent_entry_remains_opted_out(self):
  studio_backend.refresh_widget_autostart();self.assertFalse(self.entry.exists())
 def test_active_current_checkout_is_not_rewritten(self):
  text=self.old_entry().replace('/old checkout/neon-desktop',str(self.root));self.entry.write_text(text)
  studio_backend.refresh_widget_autostart();self.assertEqual(self.entry.read_text(),text)
 def test_disabled_entry_is_not_reported_as_enabled_in_app(self):
  text=self.old_entry(enabled=False).replace('/old checkout/neon-desktop',str(self.root));self.entry.write_text(text)
  self.assertFalse(studio_backend.autostart_enabled())
if __name__=='__main__':unittest.main()
