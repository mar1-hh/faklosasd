#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
/usr/bin/python3 updater.py uninstall
/usr/bin/python3 desktop_icons.py restore
/usr/bin/python3 terminal_theme.py restore
/usr/bin/python3 keep_awake.py disable
/usr/bin/python3 -c 'from studio_backend import stop_widgets; print(stop_widgets())'
gnome-extensions disable neon-desktop@local 2>/dev/null || true
/usr/bin/python3 - <<'PYCODE'
import os
from pathlib import Path
root=Path.cwd()
entry=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'autostart/neon-dashboard.desktop'
launcher=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'applications/neon-desktop-settings.desktop'
if launcher.exists() and any(str(root/name) in launcher.read_text() for name in ('settings.py','control-center.py')):launcher.unlink()
backup=root/'state/dashboard-autostart-before'
if backup.exists():
 entry.write_bytes(backup.read_bytes()); backup.unlink()
elif entry.exists() and any(str(root/name) in entry.read_text() for name in ('dashboard.py','desktop-widgets.py')):
 entry.unlink()
PYCODE
/usr/bin/python3 native_wallpaper.py disable
/usr/bin/python3 configure.py uninstall
