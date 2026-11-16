#!/usr/bin/env python3
"""User-supplied Shift keep-awake behavior, with Neon Studio lifecycle support."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import threading
import time
from preferences import ROOT,load
from native_wallpaper import atomic_write

STATE=ROOT/'state'
def write_status(state,**details):
 STATE.mkdir(exist_ok=True)
 atomic_write(STATE/'keep-awake-status.json',json.dumps({'state':state,'updated_at':time.time(),**details}))

def run_events(controller,key,minutes=60,interval=30,enabled=lambda:True,wait=None,clock=time.monotonic):
 """Wait between events and promptly stop on shutdown or preference changes."""
 stop=threading.Event();wait=wait or stop.wait
 deadline=clock()+minutes*60 if minutes else None
 next_event=clock()+interval
 while enabled():
  now=clock()
  if deadline is not None and now>=deadline:return 'finished'
  remaining=next_event-now
  if remaining>0:
   if wait(min(1,remaining)):return 'stopped'
   continue
  try:controller.press(key)
  finally:controller.release(key)
  print(time.strftime('%H:%M:%S'),'Keyboard event sent',flush=True)
  next_event=clock()+interval
 return 'disabled'

def main(argv=None):
 parser=argparse.ArgumentParser(description='Run the personal sc.py keep-awake behavior.')
 parser.add_argument('minutes',nargs='?',type=int,default=60,help='Duration in minutes; 0 runs indefinitely.')
 parser.add_argument('--interval',type=int,default=30,help='Seconds between Shift events (minimum 5).')
 parser.add_argument('--managed',action='store_true',help='Follow the Neon Studio on/off preference.')
 args=parser.parse_args(argv)
 if args.minutes<0 or args.interval<5:parser.error('minutes must be >= 0 and interval must be >= 5.')
 STATE.mkdir(exist_ok=True)
 with (STATE/'keep-awake.lock').open('a+') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return 0
  if args.managed and not load()['keep_awake_enabled']:
   write_status('disabled');return 0
  atomic_write(STATE/'keep-awake.pid',str(os.getpid()))
  stopped=threading.Event()
  signal.signal(signal.SIGTERM,lambda *_:stopped.set())
  signal.signal(signal.SIGINT,lambda *_:stopped.set())
  controller=None;key=None
  try:
   # Import only after the lock/preferences check; tests never create real input.
   from pynput.keyboard import Controller,Key
   controller=Controller();key=Key.shift
   if args.managed and 'NEON_KEEP_AWAKE_UNTIL' in os.environ:
    resume=float(os.environ['NEON_KEEP_AWAKE_UNTIL'])
    if resume and resume<=time.time():return 0
    args.minutes=max(0,(resume-time.time())/60) if resume else 0
   started=time.time();ends=started+args.minutes*60 if args.minutes else None
   write_status('running',pid=os.getpid(),started_at=started,ends_at=ends,interval=args.interval)
   print(f'Keep-awake started: {args.minutes} minutes, Shift every {args.interval} seconds.',flush=True)
   result=run_events(controller,key,args.minutes,args.interval,enabled=lambda:not stopped.is_set() and (not args.managed or load()['keep_awake_enabled']),wait=stopped.wait)
   write_status(result);print('Keep-awake '+result+'.',flush=True)
   return 0
  except Exception as error:
   write_status('error',message=str(error));print('Keep-awake error: '+str(error),flush=True)
   return 1
  finally:
   if controller is not None:
    try:controller.release(key)
    except Exception:pass
   try:(STATE/'keep-awake.pid').unlink()
   except FileNotFoundError:pass

if __name__=='__main__':raise SystemExit(main())
