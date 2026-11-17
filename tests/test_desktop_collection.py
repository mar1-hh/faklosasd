import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from desktop_collection import entries
import desktop_icons
from preferences import normalize

class Collections(unittest.TestCase):
 def test_listing_is_sorted_read_only_and_excludes_dotfiles(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   for name in ('b.png','a.txt','.secret'):(root/name).write_text('personal')
   (root/'Folder').mkdir()
   self.assertEqual([p.name for p in entries(root)],['a.txt','b.png','Folder'])
   self.assertEqual((root/'a.txt').read_text(),'personal');self.assertTrue((root/'.secret').exists())
 def test_new_preferences_keep_old_settings(self):
  prefs=normalize({'opacity':.55,'notes':'hello','widget_borders':False,'collection_folder':'/tmp/files','visible':{'collection':True},'positions':{'collection':[12,34]}})
  self.assertFalse(prefs['widget_borders']);self.assertTrue(prefs['visible']['collection'])
  self.assertEqual(prefs['opacity'],.55);self.assertEqual(prefs['positions']['collection'],[12,34])
  self.assertTrue(normalize({})['widget_borders']);self.assertFalse(normalize({})['visible']['collection'])
 def test_hide_restore_only_changes_desktop_extension(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(desktop_icons,'BACKUP',Path(folder)/'backup.json'):
   active={'ding@rastersoft.com','other@example.com'};calls=[]
   def command(*args):
    calls.append(args)
    if args[0]=='list':return list(active)
    if args[0]=='disable':active.remove(args[1])
    if args[0]=='enable':active.add(args[1])
    return []
   with patch.object(desktop_icons,'command',side_effect=command):
    desktop_icons.hide();self.assertEqual(active,{'other@example.com'})
    self.assertTrue(desktop_icons.BACKUP.exists())
    desktop_icons.restore();self.assertIn('ding@rastersoft.com',active)
    self.assertFalse(desktop_icons.BACKUP.exists())
 def test_locked_policy_fails_without_claiming_success(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(desktop_icons,'BACKUP',Path(folder)/'backup.json'):
   with patch.object(desktop_icons,'command',return_value=['ding@rastersoft.com']):
    with self.assertRaisesRegex(RuntimeError,'policy'):desktop_icons.hide()
    self.assertFalse(desktop_icons.BACKUP.exists())
 def test_no_supported_extension_leaves_no_restore_record(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(desktop_icons,'BACKUP',Path(folder)/'backup.json'):
   with patch.object(desktop_icons,'command',return_value=[]):
    with self.assertRaises(RuntimeError):desktop_icons.hide()
    self.assertFalse(desktop_icons.BACKUP.exists())

 def test_collection_position_can_be_saved_and_hidden(self):
  from widget_layout import positions
  from preferences import WIDGETS
  prefs=normalize({'visible':{'collection':True},'positions':{'collection':[500,300]}})
  sizes={name:(200,100) for name in WIDGETS}
  self.assertEqual(positions(1920,1080,sizes,prefs)['collection'],(500,300))
 def test_listing_limit(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   for i in range(510):(root/str(i)).touch()
   self.assertEqual(len(entries(root)),500)
