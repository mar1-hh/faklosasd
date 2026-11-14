"""Personal GNOME wallpaper profile, following TrpStrata's session setup.

This backend is for a campus that permits this user-level configuration.
Only user-owned files are written. The Shell is never restarted automatically.
The app's own GSettings environment remains unchanged; wallpaper commands run
in child processes with the selected profile.
"""
import ast
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time

class WallpaperError(RuntimeError):
 pass

def atomic_write(path,text):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(prefix='.neon-',dir=path.parent)
 try:
  with os.fdopen(fd,'w') as stream:stream.write(text)
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)

class NativeWallpaper:
 SCHEMA='org.gnome.desktop.background'
 KEYS={'picture-uri','picture-uri-dark','picture-options'}
 MARKER='# Managed by Neon Studio wallpaper setup\n'
 def __init__(self,config=None,runner=None):
  self.config=Path(config) if config is not None else Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
  self.profile=self.config/'dconf/neon-studio-wallpaper.profile'
  self.runner=runner or subprocess.run
  self.original_env=dict(os.environ)
  self.pending_login=None;self.last_error='';self.cache={};self.disabled=False
 def run(self,args,personal=True,allow_failure=False):
  env=dict(self.original_env)
  if personal:
   env.update(DCONF_PROFILE=str(self.profile),GSETTINGS_BACKEND='dconf')
  try:result=self.runner(args,env=env,capture_output=True,text=True,timeout=4)
  except (OSError,subprocess.SubprocessError) as error:
   if allow_failure:return None
   raise WallpaperError(f'Could not access GNOME: {error}') from error
  if not allow_failure and (result.returncode or result.stderr.strip()):
   raise WallpaperError(result.stderr.strip() or result.stdout.strip() or 'GNOME rejected the command.')
  return result
 def prepare_profile(self):
  if self.profile.exists() or self.profile.is_symlink():
   if not self.profile.is_file() or self.profile.is_symlink():raise WallpaperError('The personal wallpaper profile must be a regular user file.')
   text=self.profile.read_text()
   if not text.startswith(self.MARKER):raise WallpaperError('A different wallpaper profile exists at this path; it was left unchanged.')
   return
  source=self.original_env.get('DCONF_PROFILE','user')
  source=Path(source) if source.startswith('/') else Path('/etc/dconf/profile')/source
  storage='user-db:user'
  try:
   for line in source.read_text().splitlines():
    if re.match(r'^\s*(user-db:|service-db:)',line):storage=line.strip();break
  except OSError:pass
  atomic_write(self.profile,self.MARKER+storage+'\n')
 def is_writable(self,key):
  if key not in self.KEYS:return False
  cached=self.cache.get(key)
  if cached and time.monotonic()-cached[0]<15:return cached[1]
  try:
   self.prepare_profile()
   result=self.run(['gsettings','writable',self.SCHEMA,key])
   writable=result.stdout.strip()=='true';self.last_error='' if writable else 'GNOME will not write '+key
  except (OSError,WallpaperError) as error:
   writable=False;self.last_error=str(error)
  self.cache[key]=(time.monotonic(),writable);return writable
 def get_string(self,key):return self._get(key,True)
 def get_original(self,key):return self._get(key,False)
 def _get(self,key,personal):
  if key not in self.KEYS:raise WallpaperError('Unsupported wallpaper setting: '+key)
  result=self.run(['gsettings','get',self.SCHEMA,key],personal=personal)
  try:value=ast.literal_eval(result.stdout.strip())
  except (ValueError,SyntaxError) as error:raise WallpaperError('GNOME returned an invalid wallpaper value.') from error
  if not isinstance(value,str):raise WallpaperError('GNOME returned an invalid wallpaper type.')
  return value
 def set_string(self,key,value):
  if key not in self.KEYS or not isinstance(value,str):raise WallpaperError('Unsupported wallpaper setting.')
  if key=='picture-options' and value not in {'zoom','scaled','stretched','centered','wallpaper','spanned','none'}:raise WallpaperError('Unsupported wallpaper fit.')
  if not self.is_writable(key):return False
  self.run(['gsettings','set',self.SCHEMA,key,repr(value)])
  if self.get_string(key)!=value:raise WallpaperError('GNOME did not save '+key)
  return True
 def shell_unit(self):
  kind=self.original_env.get('XDG_SESSION_TYPE','x11')
  kinds=list(dict.fromkeys([kind,'x11','wayland']))
  for candidate in kinds:
   if candidate not in ('x11','wayland'):continue
   unit=f'org.gnome.Shell@{candidate}.service'
   result=self.run(['systemctl','--user','is-active','--quiet',unit],personal=False,allow_failure=True)
   if result and result.returncode==0:return unit
  raise WallpaperError('No active GNOME Shell user service was found. This session cannot use the personal-profile setup.')
 def loaded(self,unit):
  result=self.run(['systemctl','--user','show',unit,'--property=MainPID','--value'],personal=False,allow_failure=True)
  if not result or not result.stdout.strip().isdigit() or int(result.stdout.strip())<=0:return False
  try:
   environ=Path('/proc')/result.stdout.strip()/'environ'
   return ('DCONF_PROFILE='+str(self.profile)).encode() in environ.read_bytes().split(b'\0')
  except OSError:return False
 def override_path(self,unit):return self.config/'systemd/user'/(unit+'.d')/'90-neon-studio-wallpaper.conf'
 def ensure_setup(self):
  if os.geteuid()==0:raise WallpaperError('Run Neon Studio as your normal desktop user, without sudo.')
  self.prepare_profile()
  if not all(self.is_writable(key) for key in self.KEYS):raise WallpaperError(self.last_error or 'The personal wallpaper profile is not writable.')
  unit=self.shell_unit();override=self.override_path(unit)
  for path in override.parent.glob('*.conf'):
   if path==override:continue
   for line in path.read_text().splitlines():
    if line.strip().startswith('Environment='):
     try:values=shlex.split(line.strip().partition('=')[2])
     except ValueError:continue
     if any(value.startswith('DCONF_PROFILE=') for value in values):
      raise WallpaperError(f'A different Shell profile is configured in {path.name}; it was left unchanged.')
  value=str(self.profile).replace('\\','\\\\').replace('"','\\"').replace('%','%%')
  text=self.MARKER+'[Service]\nEnvironment="DCONF_PROFILE='+value+'"\nEnvironment=GSETTINGS_BACKEND=dconf\n'
  if override.exists() or override.is_symlink():
   if override.is_symlink() or override.read_text()!=text:raise WallpaperError('An existing Shell override was left unchanged.')
  else:
   atomic_write(override,text)
   try:self.run(['systemctl','--user','daemon-reload'],personal=False)
   except WallpaperError:
    override.unlink();raise
  self.disabled=False
  self.pending_login=not self.loaded(unit)
  return self.pending_login
 def disable_setup(self):
  removed=[]
  for kind in ('x11','wayland'):
   path=self.override_path(f'org.gnome.Shell@{kind}.service')
   if path.exists():
    if path.is_symlink() or not path.read_text().startswith(self.MARKER):raise WallpaperError('An unrecognized Shell override was left unchanged.')
    text=path.read_text();path.unlink();removed.append((path,text))
  if removed:
   try:self.run(['systemctl','--user','daemon-reload'],personal=False)
   except WallpaperError:
    for path,text in removed:atomic_write(path,text)
    raise
   self.disabled=True
   return 'Personal wallpaper setup disabled. Log out and back in to load your previous GNOME profile.'
  return 'No Neon Studio Shell profile override is installed.'
 def status_text(self):
  if self.disabled:return 'Personal wallpaper setup disabled. Log out and back in to return to your previous profile.'
  if self.last_error:return self.last_error
  if self.pending_login is True:return 'Wallpaper saved. Log out and back in once so GNOME can load your personal wallpaper profile.'
  if self.pending_login is False:return 'Personal wallpaper profile active. Wallpaper changes apply immediately.'
  return 'Personal wallpaper profile ready. The first Apply may require one normal logout/login.'

if __name__=='__main__':
 import sys
 backend=NativeWallpaper()
 try:
  if sys.argv[1:]!=['disable']:raise WallpaperError('Usage: native_wallpaper.py disable')
  print(backend.disable_setup())
 except (OSError,WallpaperError) as error:
  print(str(error),file=sys.stderr);sys.exit(1)
