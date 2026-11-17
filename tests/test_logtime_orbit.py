import unittest
from logtime_orbit import values,ring_geometry,summary

class OrbitValues(unittest.TestCase):
 def snapshot(self,total=92+41/60,session=1):
  return {'snapshot_time':1000,'session_detected':True,'hours':{'projected':total,'session':session,'today':2}}
 def test_summary_target_and_live_seconds(self):
  result=values(self.snapshot(),120,1000)
  self.assertEqual(result['total'],'92h 41m');self.assertEqual(result['target'],'Target 120h')
  self.assertEqual(result['remaining'],'27h 19m remaining');self.assertEqual(result['percent'],'77%')
  self.assertEqual(result['today'],'3h 00m');self.assertEqual(result['session'],'01:00:00')
  later=values(self.snapshot(),120,1061)
  self.assertEqual(later['total'],'92h 42m');self.assertEqual(later['session'],'01:01:01')
  self.assertTrue(later['active'])
 def test_goal_exceeded_and_exact_goal(self):
  for total in (120,150):
   result=values(self.snapshot(total),120,1000)
   self.assertEqual(result['fraction'],1);self.assertEqual(result['remaining'],'Goal reached!')
  self.assertEqual(values(self.snapshot(150),120,1000)['percent'],'125%')
 def test_missing_invalid_zero_targets(self):
  for target in (None,0,-1,'bad',float('nan'),float('inf')):
   result=values(self.snapshot(),target,1000)
   self.assertEqual(result['fraction'],0);self.assertEqual(result['percent'],'—')
   self.assertEqual(result['remaining'],'Set a target in Settings')
 def test_inactive_snapshot_does_not_advance(self):
  data=self.snapshot();data['session_detected']=False
  self.assertEqual(values(data,120,1000),values(data,120,9000))
 def test_target_changes_recalculate_without_changing_data(self):
  data=self.snapshot(60)
  self.assertEqual(values(data,120,1000)['percent'],'50%')
  self.assertEqual(values(data,100,1000)['percent'],'60%')
  self.assertEqual(data['hours']['projected'],60)
 def test_ring_geometry_fits_allocated_space(self):
  for width,height in ((152,152),(247,247),(342,342),(320,200),(0,0)):
   x,y,radius,stroke=ring_geometry(width,height)
   self.assertGreaterEqual(radius,0)
   if radius:
    self.assertLessEqual(radius+stroke/2,min(width,height)/2)
    self.assertEqual((x,y),(width/2,height/2))
 def test_empty_and_large_summary_values(self):
  self.assertEqual(summary(0),'0h 00m');self.assertEqual(summary(999.5),'999h 30m')

 def test_real_cairo_ring_draws_without_display(self):
  import subprocess
  script="""
import cairo
from types import SimpleNamespace
from orbit_card import Orbit
for size in (152,247,342):
 for fraction in (0,.5,1):
  surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,size,size)
  context=cairo.Context(surface)
  widget=SimpleNamespace(get_allocated_width=lambda:size,get_allocated_height=lambda:size)
  Orbit.draw(SimpleNamespace(fraction=fraction),widget,context)
  surface.flush()
  assert any(surface.get_data()),'ring did not draw'
"""
  result=subprocess.run(['/usr/bin/python3','-c',script],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
