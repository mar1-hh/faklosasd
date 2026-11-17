"""Recover display environment from this user's running GNOME Shell only."""
import os
from pathlib import Path

KEYS=('DISPLAY','XAUTHORITY','WAYLAND_DISPLAY','XDG_SESSION_TYPE')

def graphical_environment(environ=None,proc=Path('/proc')):
 env=dict(os.environ if environ is None else environ)
 candidates=[]
 try:entries=proc.iterdir()
 except OSError:return env
 for entry in entries:
  if not entry.name.isdigit():continue
  try:
   if entry.stat().st_uid!=os.getuid():continue
   if (entry/'comm').read_text().strip()!='gnome-shell':continue
   values={}
   for item in (entry/'environ').read_bytes().split(b'\0'):
    key,separator,value=item.partition(b'=')
    if separator and key.decode(errors='replace') in KEYS:
     values[key.decode()]=value.decode(errors='replace')
   if not values.get('DISPLAY'):continue
   authority=values.get('XAUTHORITY')
   if authority:
    path=Path(authority)
    if not path.is_absolute() or path.stat().st_uid!=os.getuid() or not os.access(path,os.R_OK):continue
   candidates.append(values)
  except (OSError,ValueError):continue
 matches=[value for value in candidates if value['DISPLAY']==env.get('DISPLAY')]
 selected=matches[0] if len(matches)==1 else candidates[0] if len(candidates)==1 else None
 if selected:
  for key in KEYS:
   if key in selected:env[key]=selected[key]
  # Shell using the default ~/.Xauthority must not inherit a stale explicit file.
  if 'XAUTHORITY' not in selected:env.pop('XAUTHORITY',None)
 return env
