"""Detect the logged-in user's graphical session without using system uptime."""
import os
import subprocess
import time
from datetime import datetime,timedelta

def graphical_start():
 uid=os.getuid()
 try:
  listing=subprocess.run(['loginctl','list-sessions','--no-legend','--no-pager'],capture_output=True,text=True,timeout=3,check=True)
  starts=[]
  for line in listing.stdout.splitlines():
   fields=line.split()
   if len(fields)<2 or fields[1]!=str(uid):continue
   result=subprocess.run(['loginctl','show-session',fields[0],'-p','TimestampMonotonic','-p','Type','-p','User'],capture_output=True,text=True,timeout=3,check=True)
   props=dict(row.split('=',1) for row in result.stdout.splitlines() if '=' in row)
   if props.get('User')!=str(uid) or props.get('Type') not in ('x11','wayland'):continue
   stamp=int(props.get('TimestampMonotonic','0'))/1e6
   current=time.monotonic()
   if 0<stamp<=current:starts.append(datetime.now()-timedelta(seconds=current-stamp))
  if starts:return min(starts),'graphical login'
 except (OSError,ValueError,subprocess.SubprocessError):pass
 # A desktop process supplies a local estimate if logind is inaccessible.
 try:
  result=subprocess.run(['ps','-u',str(uid),'-o','comm=,etimes='],capture_output=True,text=True,timeout=3,check=True)
  ages=[int(row.split()[-1]) for row in result.stdout.splitlines() if row.split() and row.split()[0]=='gnome-shell']
  if ages:return datetime.now()-timedelta(seconds=max(ages)),'desktop process estimate'
 except (OSError,ValueError,subprocess.SubprocessError):pass
 return None,'unavailable'
