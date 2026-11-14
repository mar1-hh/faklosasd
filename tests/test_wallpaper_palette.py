"""Dominant hue must win over minority colors and dark background pixels."""
from pathlib import Path
import colorsys,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wallpaper_palette import dominant_color,tinted_surface
from preferences import normalize,effective_accent
class PaletteTests(unittest.TestCase):
 def rgb(self,color):return tuple(int(color[i:i+2],16) for i in (1,3,5))
 def test_majority_red_is_not_averaged_with_blue(self):
  r,g,b=self.rgb(dominant_color([(240,30,20)]*80+[(20,30,240)]*20))
  self.assertGreater(r,b*2);self.assertGreater(r,g*2)
 def test_black_background_does_not_hide_accent(self):
  r,g,b=self.rgb(dominant_color([(0,0,0)]*900+[(25,210,60)]*100))
  self.assertGreater(g,r*2)
 def test_bright_foreground_can_beat_a_muted_dark_background(self):
  r,g,b=self.rgb(dominant_color([(65,25,80)]*80+[(245,180,70)]*20))
  self.assertGreater(r,b*1.5);self.assertGreater(g,b)
 def test_red_wraparound_stays_red(self):
  pixels=[tuple(round(c*255) for c in colorsys.hsv_to_rgb(h,.8,.8)) for h in (.99,.01)]*50
  r,g,b=self.rgb(dominant_color(pixels));self.assertGreater(r,max(g,b)*2)
 def test_transparent_pixels_are_ignored(self):
  color=dominant_color([(255,0,0,0)]*90+[(20,40,230,255)]*10)
  r,g,b=self.rgb(color);self.assertGreater(b,r*2)
 def test_neutral_wallpaper_still_has_readable_color(self):
  r,g,b=self.rgb(dominant_color([(55,55,55)]*100));self.assertEqual(r,g);self.assertEqual(g,b);self.assertGreaterEqual(r,125)
 def test_custom_color_is_validated_before_css(self):
  prefs=normalize({'accent_color':'red;bad-css','auto_accent':True})
  self.assertEqual(effective_accent(prefs),'#dfa1c6')
  prefs=normalize({'accent_color':'#12ab34','auto_accent':True})
  self.assertEqual(effective_accent(prefs),'#12ab34')
  prefs=normalize({'accent':'Blue','auto_accent':False,'accent_color':'#12ab34'})
  self.assertEqual(effective_accent(prefs),'#8ebff0')
 def test_surface_is_dark_but_tinted(self):
  r,g,b=self.rgb(tinted_surface('#ff3030'));self.assertGreater(r,g);self.assertLess(r,60)
if __name__=='__main__':unittest.main()
