#!/usr/bin/python3
"""Register a regular app at login, without changing GNOME policy or settings."""
import os
from pathlib import Path
root=Path(__file__).resolve().parent
config=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
entry=config/'autostart/neon-dashboard.desktop'
entry.parent.mkdir(parents=True,exist_ok=True)
owned = entry.exists() and any(str(root/name) in entry.read_text() for name in ('dashboard.py','desktop-widgets.py'))
if entry.exists() and not owned and not (root/'state/dashboard-autostart-before').exists():
 (root/'state/dashboard-autostart-before').write_bytes(entry.read_bytes())
def quote(value):
 return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'
entry.write_text('[Desktop Entry]\nType=Application\nName=Neon Desktop Widgets\nExec=/usr/bin/python3 '+quote(root/'desktop-widgets.py')+'\nOnlyShowIn=GNOME;\nTerminal=false\nX-GNOME-Autostart-enabled=true\nX-GNOME-Autostart-Delay=5\n')
print('Installed desktop cards at login. No GNOME settings were changed.')
