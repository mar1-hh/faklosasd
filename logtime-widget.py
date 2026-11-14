#!/usr/bin/env python3
"""Use the supplied tracker unchanged, keeping its files beside the setup."""
import importlib.util
import logging
import contextlib
import io
import json
import time
from session_start import graphical_start
from preferences import load as load_preferences
import os
import sys
from pathlib import Path
root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('neon_logtime', root / 'logtime-core.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
(root / 'state').mkdir(exist_ok=True)
module.Config.cache_file = property(lambda self: root / 'state' / 'logtime-cache.json')
module.Config.log_file = property(lambda self: root / 'state' / 'logtime.log')
os.environ.setdefault('LOGTIME_TIMEOUT', '12')
os.environ.setdefault('LOGTIME_MAX_RETRIES', '1')
os.environ.setdefault('LOGTIME_TARGET_HOURS',str(load_preferences()['target_hours']))
config = module.Config.from_env()
module.setup_logging(config)
tracker = module.LogTimeTracker(config,username=load_preferences()['username'] or None)
source = 'who'
if not tracker.session_tracker.sessions:
 start, source = graphical_start()
 if start is not None:
  tracker.session_tracker.sessions = [start]
output = io.StringIO()
with contextlib.redirect_stdout(output):
 code = tracker.run(export_json=True)
if code == 0:
 data = json.loads(output.getvalue())
 data['snapshot_time'] = time.time()
 data['session_detected'] = bool(tracker.session_tracker.sessions)
 data['session_source'] = source
 print(json.dumps(data))
else:
 print(output.getvalue(), file=sys.stderr)
sys.exit(code)
