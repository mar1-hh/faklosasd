"""Pure presentation values and geometry for the circular Logtime card."""
import math
from live_logtime import live_hours, format_hours

def positive(value):
 try:
  number=float(value)
  return max(0,number) if math.isfinite(number) else 0
 except (ValueError,TypeError):return 0

def summary(hours):
 minutes=int(positive(hours)*60+1e-7)
 return f'{minutes//60}h {minutes%60:02d}m'

def values(data,target,now=None):
 hours=live_hours(data,now);total=positive(hours.get('projected'));target=positive(target)
 percent=100*total/target if target else None
 remaining=max(0,target-total)
 return dict(total=summary(total),target=('Target '+(f'{target:g}h' if target.is_integer() else summary(target))) if target else 'No target set',
             percent=f'{percent:.0f}%' if percent is not None else '—',
             fraction=min(1,total/target) if target else 0,
             remaining=('Goal reached!' if total>=target else summary(remaining)+' remaining') if target else 'Set a target in Settings',
             today=summary(positive(hours.get('today'))+positive(hours.get('session'))),
             session=format_hours(positive(hours.get('session'))),active=bool(data.get('session_detected')))

def ring_geometry(width,height):
 diameter=max(0,min(width,height));stroke=max(1,diameter*.035)
 return width/2,height/2,max(0,(diameter-stroke)/2-3),stroke
