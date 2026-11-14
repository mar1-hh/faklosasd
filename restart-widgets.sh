#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
/usr/bin/python3 -c 'from studio_backend import stop_widgets; print(stop_widgets())'
for attempt in {1..20}; do
  if /usr/bin/python3 -c 'from studio_backend import widget_pids; import sys; sys.exit(0 if not widget_pids() else 1)'; then break; fi
  sleep 0.1
done
exec bash ./install.sh
