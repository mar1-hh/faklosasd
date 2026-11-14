#!/usr/bin/env bash
# Install Neon Studio for the current user. No system packages or sudo.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
case "${1:-}" in ''|--no-start) ;; *) echo 'Usage: bash install.sh [--no-start]' >&2; exit 1;; esac
/usr/bin/python3 - <<'PY'
import gi
gi.require_version('Gtk','4.0');gi.require_version('Adw','1')
from gi.repository import Gtk,Adw
PY
/usr/bin/python3 - <<'PY'
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GdkPixbuf
PY
mkdir -p state
TRACKER_PYTHON=
for candidate in "${NEON_LOGTIME_PYTHON:-}" /usr/bin/python3 "$(command -v python3 || true)"; do
  [[ -n "$candidate" && -x "$candidate" ]] || continue
  if selected=$("$candidate" -c 'import requests,sys; print(sys.executable)' 2>/dev/null); then
    TRACKER_PYTHON="$selected"
    break
  fi
done
if [[ -z "$TRACKER_PYTHON" ]]; then
  echo 'No Python interpreter with requests was found. See README.md → Dependencies.' >&2
  exit 1
fi
ln -sfn -- "$TRACKER_PYTHON" python
/usr/bin/python3 -c 'from studio_backend import backup_preferences; backup_preferences()'
/usr/bin/python3 install-settings.py
printf '\nNeon Studio is ready. Open it from Applications or run:\n/usr/bin/python3 "%s/control-center.py"\n' "$PWD"
if [[ ${1:-} != --no-start ]]; then
  /usr/bin/python3 - <<'PY'
from studio_backend import start_widgets
try:print(start_widgets())
except RuntimeError as error:print(error)
PY
  /usr/bin/python3 -c 'from studio_backend import start_studio; print(start_studio())'
fi
