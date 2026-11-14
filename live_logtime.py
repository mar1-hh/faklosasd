"""Pure display math, shared by the GTK logtime card."""
import time

def format_hours(hours):
 seconds=max(0,int(hours*3600))
 return f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}'

def live_hours(data, now=None):
 now=time.time() if now is None else now
 h=data['hours']
 elapsed=max(0,now-data.get('snapshot_time',now))/3600 if data.get('session_detected',False) else 0
 return dict(h,projected=h['projected']+elapsed,session=h['session']+elapsed)
