"""Terminal changes are tested against in-memory fake profiles, never user dconf."""
from pathlib import Path
import sys,tempfile,unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gi.repository import GLib
from terminal_theme import TerminalTheme,TerminalThemeError,colors
from preferences import normalize
from wallpaper_palette import tinted_surface
UUID='b1dcc9dd-5262-4d8d-a863-c897e6d979b9'
class Schema:
 def __init__(self,transparent=True):
  values=colors('#dfa1c6',25)
  if not transparent:
   for key in ('use-transparent-background','background-transparency-percent','use-theme-transparency'):values.pop(key)
  self.kinds={key:'b' if isinstance(value,bool) else 'i' if isinstance(value,int) else 'as' if isinstance(value,list) else 's' for key,value in values.items()}
 def has_key(self,key):return key in self.kinds
 def get_key(self,key):return SimpleNamespace(get_value_type=lambda:GLib.VariantType.new(self.kinds[key]))
class Profile:
 def __init__(self):self.values={};self.locked=set();self.fail_once=None;self.writes=0
 def get_user_value(self,key):return self.values.get(key)
 def is_writable(self,key):return key not in self.locked
 def set_value(self,key,value):
  self.writes+=1
  if self.fail_once==key:self.fail_once=None;return False
  self.values[key]=value;return True
 def reset(self,key):self.values.pop(key,None)
class Store:
 def __init__(self,transparent=True):
  self.schema=Schema(transparent);self.profile=Profile();self.ids=[UUID];self.default=UUID
  self.gio=SimpleNamespace(Settings=SimpleNamespace(new=self.new,new_with_path=lambda *args:self.profile,sync=lambda:None),SettingsSchemaSource=SimpleNamespace(get_default=lambda:SimpleNamespace(lookup=lambda *args:self.schema)))
 def new(self,name):return SimpleNamespace(get_strv=lambda key:self.ids,get_string=lambda key:self.default)
class TerminalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.backup=Path(self.tmp.name)/'before.json';self.store=Store();self.theme=TerminalTheme(self.backup,self.store.gio,GLib)
 def tearDown(self):self.tmp.cleanup()
 def values(self):return {key:value.unpack() for key,value in self.store.profile.values.items()}
 def test_colors_follow_the_exact_widget_surface_and_accent(self):
  self.theme.apply('#bb7788',35);values=self.values()
  self.assertEqual(values['background-color'],tinted_surface('#bb7788'));self.assertEqual(values['cursor-background-color'],'#bb7788')
  self.assertEqual(len(values['palette']),16);self.assertFalse(values['use-theme-colors'])
 def test_transparency_overrides_theme_transparency(self):
  self.theme.apply('#bb7788',35);values=self.values()
  self.assertTrue(values['use-transparent-background']);self.assertFalse(values['use-theme-transparency']);self.assertEqual(values['background-transparency-percent'],35)
 def test_restore_preserves_unset_values_and_unrelated_font(self):
  self.store.profile.values={'use-theme-colors':GLib.Variant('b',True),'font':GLib.Variant('s','Monospace 15')}
  self.theme.apply('#bb7788',35);self.theme.restore()
  self.assertEqual(self.values(),{'use-theme-colors':True,'font':'Monospace 15'});self.assertFalse(self.backup.exists())
 def test_multiple_wallpapers_restore_the_original_not_previous_theme(self):
  self.store.profile.values={'background-color':GLib.Variant('s','#123456')}
  self.theme.apply('#ff7777',20);self.theme.apply('#7799ff',40);self.theme.restore()
  self.assertEqual(self.values(),{'background-color':'#123456'})
 def test_locked_profile_is_not_modified(self):
  self.store.profile.locked.add('background-color')
  with self.assertRaises(TerminalThemeError):self.theme.apply('#bb7788',35)
  self.assertFalse(self.backup.exists());self.assertEqual(self.store.profile.writes,0)
 def test_failed_apply_rolls_back_completed_writes(self):
  self.store.profile.values={'background-color':GLib.Variant('s','#123456')};self.store.profile.fail_once='palette'
  with self.assertRaises(TerminalThemeError):self.theme.apply('#bb7788',35)
  self.assertEqual(self.values(),{'background-color':'#123456'})
 def test_build_without_transparency_still_supports_colors(self):
  store=Store(False);theme=TerminalTheme(self.backup,store.gio,GLib)
  self.assertFalse(theme.transparency_supported());self.assertIn('does not support transparency',theme.apply('#bb7788',35))
 def test_sync_only_reapplies_when_preferences_change(self):
  prefs=normalize({'terminal_match':True});self.theme.sync(prefs);writes=self.store.profile.writes
  self.theme.sync(prefs);self.assertEqual(self.store.profile.writes,writes)
  prefs['accent_color']='#99bb66';self.theme.sync(prefs);self.assertGreater(self.store.profile.writes,writes)
 def test_disabling_restores_terminal(self):
  prefs=normalize({'terminal_match':True});self.theme.sync(prefs);prefs['terminal_match']=False;self.theme.sync(prefs)
  self.assertEqual(self.values(),{});self.assertFalse(self.backup.exists())
 def test_deleted_profile_is_not_recreated_by_restore(self):
  self.theme.apply('#bb7788',35);self.store.ids=[];self.theme.restore();self.assertFalse(self.backup.exists())
 def test_transparency_preference_is_bounded(self):
  self.assertEqual(normalize({'terminal_transparency':999})['terminal_transparency'],100)
  self.assertEqual(normalize({'terminal_transparency':-1})['terminal_transparency'],0)
if __name__=='__main__':unittest.main()
