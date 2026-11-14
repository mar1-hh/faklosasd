"""Neon Studio actions. No GTK or system-wide settings changes."""
import json
import os
from pathlib import Path
import signal
import subprocess
from preferences import ROOT,FILE,load,save,normalize
IMAGE_SUFFIXES={'.png','.jpg','.jpeg','.webp','.bmp'}
def wallpapers(folder):
 folder=Path(folder).expanduser()
 try:return sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES),key=lambda p:p.name.lower())[:300]
 except OSError:return []
def widget_pids():
 try:
  result=subprocess.run(['pgrep','-u',str(os.getuid()),'-f','desktop-widgets[.]py'],capture_output=True,text=True,timeout=3)
 except (OSError,subprocess.SubprocessError):return []
 pids=[]
 for token in result.stdout.split():
  try:
   pid=int(token)
   args=Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')
   scripts=[arg for arg in args[1:] if arg.endswith('desktop-widgets.py')]
   for script in scripts:
    full=Path(script) if Path(script).is_absolute() else Path(f'/proc/{pid}/cwd').resolve()/script
    if full.resolve()==ROOT/'desktop-widgets.py':pids.append(pid);break
  except (OSError,ValueError):pass
 return pids
def start_widgets():
 if widget_pids():return 'Desktop widgets are already running.'
 interpreter=ROOT/'python'
 if not interpreter.exists():raise RuntimeError('Run install.sh first to select the logtime Python interpreter.')
 with (ROOT/'state/widgets.log').open('a') as log:
  process=subprocess.Popen(['/usr/bin/python3',str(ROOT/'desktop-widgets.py')],cwd=ROOT,stdout=log,stderr=log,start_new_session=True)
  try:code=process.wait(timeout=0.7)
  except subprocess.TimeoutExpired:return 'Desktop widgets started.'
  if code:raise RuntimeError('Desktop cards could not start. See state/widgets.log for the error.')
 return 'Desktop widgets are already running.'
def stop_widgets():
 for pid in widget_pids():
  try:os.kill(pid,signal.SIGTERM)
  except ProcessLookupError:pass
 return 'Desktop widgets stopped.'
def autostart_path():
 return Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'autostart/neon-dashboard.desktop'
def autostart_enabled():
 entry=autostart_path()
 try:return str(ROOT/'desktop-widgets.py') in entry.read_text()
 except OSError:return False
def set_autostart(enabled):
 entry=autostart_path()
 if enabled:
  subprocess.run(['/usr/bin/python3',str(ROOT/'install-dashboard.py')],check=True,cwd=ROOT,capture_output=True,text=True)
 elif autostart_enabled():entry.unlink()
def backup_preferences():
 path=ROOT/'state/studio-before.json'
 if not path.exists():path.write_text(json.dumps(load(),indent=2))
def restore_preferences():
 path=ROOT/'state/studio-before.json'
 if not path.exists():raise RuntimeError('No saved Studio settings to restore.')
 save(normalize(json.loads(path.read_text())))
 return 'Restored settings from before Neon Studio setup.'


def start_studio():
 with (ROOT/'state/studio.log').open('a') as log:
  process=subprocess.Popen(['/usr/bin/python3',str(ROOT/'control-center.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
  try:
   code=process.wait(timeout=1.5)
  except subprocess.TimeoutExpired:return 'Neon Studio launched.'
  if code:raise RuntimeError('Neon Studio exited during startup. Run open-studio.sh to see the error, or read state/studio.log.')
 return 'Open Neon Studio from Applications.'
