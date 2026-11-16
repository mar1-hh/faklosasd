"""Reversible GNOME Terminal profile colors and Ubuntu transparency support."""
import json
from pathlib import Path
from preferences import ROOT,effective_accent
from wallpaper_palette import tinted_surface
from native_wallpaper import atomic_write
SCHEMA='org.gnome.Terminal.Legacy.Profile'
PROFILE_PATH='/org/gnome/terminal/legacy/profiles:/'
class TerminalThemeError(RuntimeError):pass

def colors(accent,transparency):
 background=tinted_surface(accent)
 base=['#18151e','#e06c75','#98c379','#e5c07b','#61afef','#c678dd','#56b6c2','#ded8e5','#706577','#ef8991','#b2d993','#f5d694','#89c7ff','#dba0ed','#83d9df','#ffffff']
 tint=[int(accent[i:i+2],16) for i in (1,3,5)]
 palette=[]
 for index,color in enumerate(base):
  weight=0 if index in (0,7,8,15) else .12
  rgb=[int(color[i:i+2],16) for i in (1,3,5)]
  palette.append('#'+''.join(f'{round(value*(1-weight)+tint[i]*weight):02x}' for i,value in enumerate(rgb)))
 return {'use-theme-colors':False,'background-color':background,'foreground-color':'#eee5ee','palette':palette,'bold-color-same-as-fg':True,'cursor-colors-set':True,'cursor-background-color':accent,'cursor-foreground-color':background,'highlight-colors-set':True,'highlight-background-color':accent,'highlight-foreground-color':background,'use-theme-transparency':False,'use-transparent-background':transparency>0,'background-transparency-percent':int(transparency)}

class TerminalTheme:
 def __init__(self,backup=None,gio=None,glib=None):
  if gio is None or glib is None:
   from gi.repository import Gio,GLib
   gio=gio or Gio;glib=glib or GLib
  self.gio=gio;self.glib=glib;self.backup=Path(backup) if backup is not None else ROOT/'state/terminal-before.json'
  self.schema=gio.SettingsSchemaSource.get_default().lookup(SCHEMA,True)
  self.signature=None;self.message='Terminal matching is off.'
 def available(self):return self.schema is not None
 def transparency_supported(self):
  return bool(self.schema and all(self.schema.has_key(key) for key in ('use-transparent-background','background-transparency-percent')))
 def profile(self,identity=None):
  import uuid
  profiles=self.gio.Settings.new('org.gnome.Terminal.ProfilesList')
  identities=profiles.get_strv('list')
  if identity is None:
   identity=profiles.get_string('default')
   if identity not in identities:identity=identities[0] if identities else None
  if not identity or identity not in identities:raise TerminalThemeError('No matching GNOME Terminal profile was found.')
  try:uuid.UUID(identity)
  except (ValueError,TypeError) as error:raise TerminalThemeError('Invalid terminal profile identifier.') from error
  return identity,self.gio.Settings.new_with_path(SCHEMA,PROFILE_PATH+':'+identity+'/')
 def snapshot(self,profile,keys):
  result={}
  for key in keys:
   value=profile.get_user_value(key);result[key]=None if value is None else value.print_(True)
  return result
 def put_snapshot(self,profile,values):
  for key,raw in values.items():
   if raw is None:profile.reset(key)
   else:
    kind=self.schema.get_key(key).get_value_type()
    value=self.glib.Variant.parse(kind,raw,None,None)
    if not profile.set_value(key,value):raise TerminalThemeError('GNOME could not restore '+key)
 def check_writable(self,profile,keys):
  locked=[key for key in keys if not profile.is_writable(key)]
  if locked:raise TerminalThemeError('Terminal profile settings are locked: '+', '.join(locked))
 def apply(self,accent,transparency):
  if not self.available():raise TerminalThemeError('GNOME Terminal profile settings are not installed.')
  identity,profile=self.profile()
  desired={key:value for key,value in colors(accent,transparency).items() if self.schema.has_key(key)}
  self.check_writable(profile,desired)
  previous=self.snapshot(profile,desired)
  saved=json.loads(self.backup.read_text()) if self.backup.exists() else {'profiles':{}}
  if identity not in saved['profiles']:
   saved['profiles'][identity]=previous
   atomic_write(self.backup,json.dumps(saved,indent=2))
  try:
   for key,value in desired.items():
    kind=self.schema.get_key(key).get_value_type().dup_string()
    if not profile.set_value(key,self.glib.Variant(kind,value)):raise TerminalThemeError('GNOME rejected terminal setting '+key)
   self.gio.Settings.sync()
  except Exception:
   self.put_snapshot(profile,previous);self.gio.Settings.sync();raise
  self.message='Default GNOME Terminal profile matches the widget colors.'
  if transparency and not self.transparency_supported():self.message+=' This terminal build does not support transparency.'
  return self.message
 def restore(self):
  if not self.backup.exists():return 'No terminal changes to restore.'
  if not self.available():raise TerminalThemeError('GNOME Terminal settings are unavailable; the backup was retained.')
  saved=json.loads(self.backup.read_text());prepared=[]
  for identity,values in saved['profiles'].items():
   try:_,profile=self.profile(identity)
   except TerminalThemeError:continue # A deleted profile must not be recreated.
   values={key:value for key,value in values.items() if self.schema.has_key(key)}
   self.check_writable(profile,values);prepared.append((profile,values,self.snapshot(profile,values)))
  completed=[]
  try:
   for profile,values,previous in prepared:
    completed.append((profile,previous));self.put_snapshot(profile,values)
   self.gio.Settings.sync()
  except Exception:
   for profile,previous in completed:self.put_snapshot(profile,previous)
   self.gio.Settings.sync();raise
  self.backup.unlink();self.signature=None;self.message='Original terminal colors and transparency restored.'
  return self.message
 def sync(self,prefs):
  signature=(prefs['terminal_match'],effective_accent(prefs),prefs['terminal_transparency'])
  if self.signature==signature:return self.message
  try:
   if prefs['terminal_match']:self.apply(signature[1],signature[2])
   elif self.backup.exists():self.restore()
   else:self.message='Terminal matching is off.'
  except Exception as error:self.message='Terminal: '+str(error)
  self.signature=signature
  return self.message

if __name__=='__main__':
 import sys
 try:
  if sys.argv[1:]!=['restore']:raise TerminalThemeError('Usage: terminal_theme.py restore')
  print(TerminalTheme().restore())
  from preferences import update
  update({'terminal_match':False})
 except Exception as error:print(str(error),file=sys.stderr);sys.exit(1)
