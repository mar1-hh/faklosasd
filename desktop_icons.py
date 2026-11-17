"""Reversible control of GNOME's desktop-icons extension; never moves files."""
import json
import subprocess
from preferences import ROOT
from native_wallpaper import atomic_write

BACKUP=ROOT/'state/desktop-icons-before.json'
EXTENSIONS=('ding@rastersoft.com','desktop-icons@csoriano')

def command(*args):
 try:
  result=subprocess.run(['gnome-extensions',*args],capture_output=True,text=True,timeout=8)
 except (OSError,subprocess.SubprocessError) as error:raise RuntimeError('Cannot contact GNOME extensions. Run Neon Studio inside your desktop session.') from error
 if result.returncode:raise RuntimeError(result.stderr.strip() or 'GNOME rejected the desktop-icons change.')
 return result.stdout.splitlines()

def hide():
 if BACKUP.exists():return 'Desktop icons are already managed. Use Restore desktop icons to show them.'
 enabled=set(command('list','--enabled'))
 selected=[name for name in EXTENSIONS if name in enabled]
 if not selected:raise RuntimeError('No enabled GNOME desktop-icons extension was found. Your desktop may use another icon manager.')
 atomic_write(BACKUP,json.dumps(selected))
 try:
  for name in selected:command('disable',name)
  if any(name in command('list','--enabled') for name in selected):raise RuntimeError('GNOME policy prevented hiding desktop icons.')
 except Exception:
  # Keep the restore record if any extension was changed or rollback fails.
  restore()
  raise
 return 'Desktop icons hidden. Your files remain in their original folders.'

def restore():
 if not BACKUP.exists():return 'No desktop-icons change to restore.'
 selected=json.loads(BACKUP.read_text())
 if not isinstance(selected,list) or any(name not in EXTENSIONS for name in selected):raise RuntimeError('Invalid desktop-icons restore record.')
 for name in selected:command('enable',name)
 enabled=set(command('list','--enabled'))
 if any(name not in enabled for name in selected):raise RuntimeError('GNOME policy prevented restoring desktop icons. The restore record was kept.')
 BACKUP.unlink()
 return 'Desktop icons restored.'

if __name__=='__main__':
 import sys
 try:print(restore() if sys.argv[1:]==['restore'] else hide())
 except (OSError,ValueError,RuntimeError) as error:print(error);raise SystemExit(1)
