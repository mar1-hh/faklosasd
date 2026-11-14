#!/usr/bin/python3
import json
from pathlib import Path
import shutil
import sys
from gi.repository import Gio
root = Path(__file__).resolve().parent
uuid = 'neon-desktop@local'
dest = Path.home() / '.local/share/gnome-shell/extensions' / uuid
backup = root / 'state' / 'settings-before.json'
settings = {
 'org.gnome.desktop.background': ['picture-uri','picture-uri-dark','picture-options'],
 'org.gnome.desktop.interface': ['color-scheme'],
}
def set_string_if_allowed(settings, key, value):
 if not settings.is_writable(key):
  print(f'Skipped administrator-locked setting: {settings.props.schema_id} / {key}')
  return False
 if not settings.set_string(key, value):
  print(f'Could not save setting: {key}', file=sys.stderr)
  return False
 return True

if sys.argv[1] == '--check':
 for schema, keys in settings.items():
  obj = Gio.Settings.new(schema)
  for key in keys:
   print(f'{schema} / {key}: {"writable" if obj.is_writable(key) else "locked"}')
 shell = Gio.Settings.new('org.gnome.shell')
 print('Extension activation: ' + ('writable' if shell.is_writable('enabled-extensions') else 'locked'))
 sys.exit(0)

if sys.argv[1] == 'install':
 shell = Gio.Settings.new('org.gnome.shell')
 if not shell.is_writable('enabled-extensions') and uuid not in shell.get_strv('enabled-extensions'):
  raise SystemExit('Administrator policy locks GNOME extension activation. No desktop settings were changed. Ask your administrator to allow neon-desktop@local.')
 if not backup.exists():
  saved = {schema:{key:Gio.Settings.new(schema).get_string(key) for key in keys} for schema,keys in settings.items()}
  backup.write_text(json.dumps(saved, indent=2))
 if dest.exists():
  # Only replace a previous installation owned by this package.
  marker = dest / 'paths.json'
  if not marker.exists() or json.loads(marker.read_text()).get('root') != str(root):
   raise SystemExit(f'Existing extension at {dest}; refusing to overwrite it.')
 dest.mkdir(parents=True, exist_ok=True)
 for file in (root / 'extension').iterdir():
  shutil.copy2(file, dest / file.name)
 (dest / 'paths.json').write_text(json.dumps({'root':str(root)}))
 bg = Gio.Settings.new('org.gnome.desktop.background')
 uri = (root / 'wallpapers/01-cyberpunk-rose.png').as_uri()
 for key in ['picture-uri','picture-uri-dark']:
  set_string_if_allowed(bg,key,uri)
 set_string_if_allowed(bg,'picture-options','zoom')
 set_string_if_allowed(Gio.Settings.new('org.gnome.desktop.interface'),'color-scheme','prefer-dark')
 shell = Gio.Settings.new('org.gnome.shell')
 enabled = shell.get_strv('enabled-extensions')
 if uuid not in enabled:
  if shell.is_writable('enabled-extensions'):
   if not shell.set_strv('enabled-extensions', enabled+[uuid]):
    raise SystemExit('Extension copied, but GNOME could not save its activation setting.')
  else:
   raise SystemExit('Extension copied, but administrator policy locks extension activation.')
 Gio.Settings.sync()
 print('Installed and enabled Neon Desktop. Applied permitted appearance settings.')
else:
 shell = Gio.Settings.new('org.gnome.shell')
 if shell.is_writable('enabled-extensions'):
  shell.set_strv('enabled-extensions',[x for x in shell.get_strv('enabled-extensions') if x != uuid])
 if backup.exists():
  for schema,keys in json.loads(backup.read_text()).items():
   s=Gio.Settings.new(schema)
   for key,value in keys.items(): set_string_if_allowed(s,key,value)
  backup.unlink()
 Gio.Settings.sync()
 if dest.exists() and (dest/'paths.json').exists() and json.loads((dest/'paths.json').read_text()).get('root') == str(root):
  shutil.rmtree(dest)
 print('Removed Neon Desktop and restored writable appearance settings. Log out and back in.')
