"""Placement regression tests using allocated GTK-card sizes."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preferences import DEFAULTS
from widget_layout import positions
class LayoutTests(unittest.TestCase):
 def setUp(self):
  self.prefs=deepcopy(DEFAULTS)
  self.sizes={'logtime':(345,410),'links':(345,180),'clock':(403,150),'system':(345,160),'calendar':(345,310),'notes':(345,145),'launcher':(559,140)}
 def test_initial_layout_updates_after_real_allocations(self):
  early=positions(1920,1080,{name:(1,1) for name in self.sizes},self.prefs)
  final=positions(1920,1080,self.sizes,self.prefs)
  self.assertNotEqual(early['links'],final['links'])
  self.assertGreaterEqual(final['links'][1],final['logtime'][1]+self.sizes['logtime'][1]+20)
  self.assertGreaterEqual(final['calendar'][1],final['system'][1]+self.sizes['system'][1]+20)
 def test_default_visible_cards_do_not_overlap(self):
  layout=positions(1920,1080,self.sizes,self.prefs)
  for index,(name,(x,y)) in enumerate(layout.items()):
   w,h=self.sizes[name]
   for other in list(layout)[index+1:]:
    ox,oy=layout[other];ow,oh=self.sizes[other]
    self.assertFalse(x<ox+ow and ox<x+w and y<oy+oh and oy<y+h,(name,other))
 def test_hidden_cards_do_not_reserve_space_in_column(self):
  self.prefs['visible']['system']=False
  layout=positions(1920,1080,self.sizes,self.prefs)
  self.assertEqual(layout['calendar'][1],62)
 def test_user_positions_are_retained(self):
  self.prefs['positions']['clock']=[500,300]
  self.assertEqual(positions(1920,1080,self.sizes,self.prefs)['clock'],(500,300))
 def test_old_offscreen_position_is_clamped(self):
  self.prefs['positions']['clock']=[8000,8000]
  x,y=positions(1920,1080,self.sizes,self.prefs)['clock']
  self.assertLessEqual(x+self.sizes['clock'][0],1920)
  self.assertLessEqual(y+self.sizes['clock'][1],1080)
 def test_layout_does_not_write_automatic_positions_to_preferences(self):
  positions(1920,1080,self.sizes,self.prefs)
  self.assertEqual(self.prefs['positions'],{})
if __name__=='__main__':unittest.main()
