"""Start/stop and login registration for Neon Studio's bundled sc.py."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from preferences import ROOT,load,update
from native_wallpaper import atomic_write
MARKER='X-Neon-Keep-Awake=true'

def entry_path():
 return Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'autostart/neon-keep-awake.desktop'
def desktop_quote(value):
 return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'
def interpreter():
 path=ROOT/'keep-awake-python'
 if not path.exists():raise RuntimeError('Keep-awake needs a Python with pynput. Run install.sh; see README → Keep awake.')
 return path.resolve()
def configure_startup(enabled):
 entry=entry_path()
 if entry.exists() and MARKER not in entry.read_text():raise RuntimeError('An unrelated keep-awake startup entry was left unchanged.')
 if enabled:
  python=interpreter()
  text='\n'.join(['[Desktop Entry]','Type=Application','Name=Neon Studio Keep Awake','Comment=Run the personal sc.py behavior at login','Exec='+desktop_quote(python)+' '+desktop_quote(ROOT/'sc.py')+' --managed','TryExec='+str(python),'OnlyShowIn=GNOME;','Terminal=false','X-GNOME-Autostart-enabled=true','X-GNOME-Autostart-Delay=0',MARKER,''])
  atomic_write(entry,text)
 else:
  if entry.exists():entry.unlink()

def running_pid():
 try:
  pid=int((ROOT/'state/keep-awake.pid').read_text())
  args=Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')
  if str(ROOT/'sc.py') in args and '--managed' in args:return pid
 except (OSError,ValueError,UnicodeError):pass
 return None

def start():
 if not load()['keep_awake_enabled']:return 'Keep awake is disabled.'
 if running_pid():return 'Keep awake is running.'
 python=interpreter();(ROOT/'state').mkdir(exist_ok=True)
 with (ROOT/'state/keep-awake.log').open('w') as log:
  process=subprocess.Popen([str(python),'-u',str(ROOT/'sc.py'),'--managed'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
  try:code=process.wait(timeout=.5)
  except subprocess.TimeoutExpired:return 'Keep awake started.'
  if code:raise RuntimeError('Keep awake could not start. See state/keep-awake.log.')
 return 'Keep awake is already running.'
def stop():
 pid=running_pid()
 if pid is not None:
  try:os.kill(pid,signal.SIGTERM)
  except ProcessLookupError:pass
 return 'Keep awake stopped.'
def set_enabled(enabled):
 configure_startup(enabled)
 update({'keep_awake_enabled':bool(enabled)})
 return start() if enabled else stop()
def status_text():
 if not load()['keep_awake_enabled']:return 'Off · disabled for this session and future logins.'
 if not (ROOT/'keep-awake-python').exists():return 'Enabled · pynput is missing. Run install.sh after installing the optional dependency.'
 try:status=json.loads((ROOT/'state/keep-awake-status.json').read_text())
 except (OSError,ValueError):status={}
 if running_pid():
  ends=status.get('ends_at')
  minutes=max(0,int((ends-time.time()+59)//60)) if ends else None
  return 'Running · Shift every 30 seconds'+(f' · about {minutes} min remaining.' if minutes is not None else '.')
 if status.get('state')=='error':return 'Could not start · '+status.get('message','See the keep-awake log.')
 if status.get('state')=='finished':return 'Enabled for next login · this login’s 60-minute run has finished.'
 return 'Enabled for login · not currently running.'

def migrate_standalone():
 """Replace only the marked startup entry created in the previous task."""
 config=entry_path().parent
 legacy=config/'neon-sc-login.desktop'
 if not legacy.exists() or 'X-Neon-SC-Managed=true' not in legacy.read_text():return
 (ROOT/'state').mkdir(exist_ok=True)
 backup=ROOT/'state/standalone-sc-startup-before.desktop'
 if not backup.exists():backup.write_bytes(legacy.read_bytes())
 legacy.unlink()
 # Stop the old script only if its known managed autostart was just migrated.
 old_script=Path.home()/'Desktop/sc.py'
 try:result=subprocess.run(['pgrep','-u',str(os.getuid()),'-f','sc[.]py'],capture_output=True,text=True,timeout=3)
 except (OSError,subprocess.SubprocessError):return
 for token in result.stdout.split():
  try:
   pid=int(token);args=Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')
   if str(old_script) in args:os.kill(pid,signal.SIGINT)
  except (OSError,ValueError,UnicodeError):continue

if __name__=='__main__':
 import sys
 try:
  if sys.argv[1:]==['install']:
   enabled=load()['keep_awake_enabled']
   configure_startup(enabled)
   if enabled:migrate_standalone()
   print('Keep-awake login startup '+('enabled.' if enabled else 'disabled.'))
  elif sys.argv[1:]==['disable']:print(set_enabled(False))
  elif sys.argv[1:]==['start']:print(start())
  else:raise RuntimeError('Usage: keep_awake.py install|start|disable')
 except (OSError,RuntimeError) as error:print(str(error),file=sys.stderr);sys.exit(1)
