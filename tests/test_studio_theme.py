import unittest
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk
from preferences import normalize
from studio_theme import theme_css

class StudioTheme(unittest.TestCase):
 def test_matches_fixed_and_wallpaper_colors(self):
  self.assertIn(b'#73d7c2',theme_css({'auto_accent':False,'accent':'Teal'}))
  self.assertIn(b'#123456',theme_css({'auto_accent':True,'accent_color':'#123456'}))
 def test_transparency_is_clamped_and_keeps_text_opaque(self):
  self.assertEqual(normalize({'studio_transparency':100})['studio_transparency'],70)
  self.assertEqual(normalize({'studio_transparency':-1})['studio_transparency'],0)
  css=theme_css({'studio_transparency':40})
  self.assertIn(b',0.600)',css);self.assertNotIn(b'opacity:',css)
 def test_css_parses_for_full_range(self):
  provider=Gtk.CssProvider();errors=[]
  provider.connect('parsing-error',lambda _,section,error:errors.append(str(error)))
  for value in (0,8,70):provider.load_from_data(theme_css({'studio_transparency':value}))
  self.assertEqual(errors,[])
