import tempfile
import unittest
from pathlib import Path
from preferences import normalize, WIDGETS
from pomodoro import Pomodoro
from widget_layout import positions

class TimerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.path=Path(self.temp.name)/'timer.json';self.now=1000
  self.prefs=normalize({});self.timer=Pomodoro(self.prefs,self.path,lambda:self.now)
 def finish(self):
  self.timer.toggle();self.now+=self.timer.state['duration']+10
  return self.timer.tick()
 def test_pause_resume_and_restart(self):
  self.timer.toggle();self.now+=123;self.assertEqual(self.timer.remaining(),1377)
  self.timer.toggle();self.now+=500;self.assertEqual(self.timer.remaining(),1377)
  self.timer.toggle();self.now+=10
  restored=Pomodoro(self.prefs,self.path,lambda:self.now)
  self.assertEqual(restored.remaining(),1367)
 def test_four_completed_focus_sessions_offer_long_break(self):
  for number in range(4):
   self.assertEqual(self.finish(),'focus')
   self.assertEqual(self.timer.state['completed'],number+1)
   self.assertFalse(self.timer.state['running'])
   self.assertEqual(self.timer.state['mode'],'long' if number==3 else 'short')
   if number<3:self.finish()
  self.finish();self.assertEqual(self.timer.state['completed'],0)
  self.assertEqual(self.timer.state['mode'],'focus')
 def test_skip_reset_and_manual_mode_do_not_count(self):
  self.timer.toggle();self.now+=60;self.timer.skip()
  self.assertEqual(self.timer.state['completed'],0)
  self.timer.mode('focus');self.timer.toggle();self.now+=60;self.timer.reset()
  self.assertEqual(self.timer.remaining(),1500);self.assertFalse(self.timer.state['running'])
  self.assertEqual(self.timer.state['completed'],0)
 def test_delayed_completion_is_once_across_restarts(self):
  self.timer.toggle();self.now+=10000
  self.assertEqual(self.timer.tick(),'focus');self.assertIsNone(self.timer.tick())
  restored=Pomodoro(self.prefs,self.path,lambda:self.now)
  self.assertIsNone(restored.tick());self.assertEqual(restored.state['completed'],1)
 def test_auto_start_does_not_credit_unattended_cycles(self):
  self.prefs['pomodoro_auto_start']=True;self.timer.toggle();self.now+=20000
  self.assertEqual(self.timer.tick(),'focus');self.assertTrue(self.timer.state['running'])
  self.assertEqual(self.timer.remaining(),300);self.assertEqual(self.timer.state['completed'],1)
 def test_changed_duration_applies_on_reset(self):
  self.timer.toggle();self.prefs['pomodoro_focus']=40
  self.assertEqual(self.timer.remaining(),1500)
  self.timer.reset();self.assertEqual(self.timer.remaining(),2400)
 def test_defaults_and_invalid_settings(self):
  prefs=normalize({'pomodoro_focus':float('nan'),'pomodoro_short':-1,'pomodoro_long':999})
  self.assertEqual((prefs['pomodoro_focus'],prefs['pomodoro_short'],prefs['pomodoro_long']),(25,1,120))
  self.assertFalse(prefs['pomodoro_auto_start']);self.assertIn('pomodoro',WIDGETS)
 def test_corrupt_state_recovers(self):
  self.path.write_text('{broken');restored=Pomodoro(self.prefs,self.path,lambda:self.now)
  self.assertEqual(restored.remaining(),1500)
 def test_default_placement_is_below_left_cards(self):
  sizes={name:(340,160) for name in WIDGETS};sizes['logtime']=(340,330)
  result=positions(1920,1080,sizes,self.prefs)
  self.assertGreaterEqual(result['pomodoro'][1],result['links'][1]+160)
  self.assertLess(result['pomodoro'][0]+340,1920/2)

 def test_settings_round_trip_preserves_existing_values(self):
  from unittest.mock import patch
  import preferences
  with patch.object(preferences,'FILE',Path(self.temp.name)/'preferences.json'):
   preferences.save({'notes':'personal note','opacity':.61,'pomodoro_focus':42,'pomodoro_sound':True,'visible':{'pomodoro':False},'positions':{'pomodoro':[45,700]}})
   restored=preferences.load()
   self.assertEqual(restored['pomodoro_focus'],42)
   self.assertEqual(restored['opacity'],.61);self.assertEqual(restored['notes'],'personal note')
   self.assertFalse(restored['visible']['pomodoro']);self.assertEqual(restored['positions']['pomodoro'],[45,700])
 def test_small_screen_finds_free_space_when_left_column_is_full(self):
  sizes={name:(260,100) for name in WIDGETS};sizes['logtime']=(260,270);sizes['links']=(260,140);sizes['pomodoro']=(260,300)
  layout=positions(1366,768,sizes,self.prefs);x,y=layout['pomodoro'];w,h=sizes['pomodoro']
  for name,(ox,oy) in layout.items():
   if name=='pomodoro':continue
   ow,oh=sizes[name]
   self.assertFalse(x<ox+ow and ox<x+w and y<oy+oh and oy<y+h,name)
