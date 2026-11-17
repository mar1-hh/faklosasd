"""Persistent timestamp-based Pomodoro timer, independent of GTK."""
import json
import math
import time
from preferences import ROOT
from native_wallpaper import atomic_write

DURATIONS={'focus':'pomodoro_focus','short':'pomodoro_short','long':'pomodoro_long'}
class Pomodoro:
 def __init__(self,prefs,path=None,clock=time.time):
  self.path=path or ROOT/'state/pomodoro.json';self.clock=clock;self.prefs=prefs
  try:self.state=json.loads(self.path.read_text())
  except (OSError,ValueError):self.state={}
  try:
   s=self.state
   assert s['mode'] in DURATIONS and isinstance(s['running'],bool)
   assert 0<=s['completed']<=4 and isinstance(s['completed'],int)
   assert all(math.isfinite(float(s[k])) and float(s[k])>=0 for k in ('remaining','duration','deadline'))
   assert s['duration']>0
  except (KeyError,ValueError,TypeError,AssertionError,OverflowError):
   self.state={'mode':'focus','running':False,'completed':0};self.reset()
 def save(self):atomic_write(self.path,json.dumps(self.state))
 def duration(self,mode):return self.prefs[DURATIONS[mode]]*60
 def remaining(self):
  return max(0,self.state['deadline']-self.clock()) if self.state['running'] else self.state['remaining']
 def reset(self):
  self.state.update(running=False,remaining=self.duration(self.state['mode']),duration=self.duration(self.state['mode']),deadline=0)
  self.save()
 def mode(self,mode):
  if mode not in DURATIONS:raise ValueError('Unknown timer mode')
  self.state['mode']=mode;self.reset()
 def toggle(self):
  self.tick()
  if self.state['running']:self.state.update(remaining=self.remaining(),running=False)
  else:self.state.update(deadline=self.clock()+self.state['remaining'],running=True)
  self.save()
 def advance(self,completed):
  old=self.state['mode']
  if old=='focus':
   if completed:self.state['completed']=min(4,self.state['completed']+1)
   mode='long' if self.state['completed']>=4 else 'short'
  else:
   mode='focus'
   if old=='long':self.state['completed']=0
  self.state['mode']=mode;self.reset()
 def skip(self):self.advance(False)
 def tick(self):
  if not self.state['running'] or self.remaining()>0:return None
  ended=self.state['mode'];self.advance(True)
  if self.prefs['pomodoro_auto_start']:
   self.state.update(running=True,deadline=self.clock()+self.state['remaining']);self.save()
  # The transition is committed before the caller emits an alert, preventing duplicates.
  return ended
