"""User autostart and narrowly scoped process lifecycle for the updater."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

MARKER = 'X-Neon-Updates-Managed=true'

def entry_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'autostart/neon-updates.desktop'

def register(root):
    root = Path(root).resolve()
    path = entry_path()
    if path.exists() and MARKER not in path.read_text():
        raise RuntimeError(f'Unrelated startup entry exists: {path}; it was preserved.')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Desktop Entry quoting differs from shell quoting: escape percent field codes too.
    script = str(root / 'updater.py').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    path.write_text('[Desktop Entry]\nType=Application\nName=Neon Studio Update Checks\n'
                    f'Exec=/usr/bin/python3 "{script}" watch\nTerminal=false\n'
                    'X-GNOME-Autostart-enabled=true\n' + MARKER + '\n')

def spawn(root, args, log, env=None):
    root = Path(root)
    (root / 'state').mkdir(exist_ok=True)
    with (root / 'state' / log).open('a') as stream:
        child = subprocess.Popen(args, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    return child

def start_watcher(root):
    return spawn(root, ['/usr/bin/python3', str(Path(root) / 'updater.py'), 'watch'], 'updates.log')

def identity(pid):
    """PID plus Linux start time prevents signalling a recycled PID."""
    proc = Path('/proc') / str(pid)
    if proc.stat().st_uid != os.getuid(): return None
    raw = (proc / 'stat').read_text()
    return raw[raw.rfind(')') + 2:].split()[19]

def processes(root):
    root = Path(root).resolve()
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid(): continue
        try:
            token = identity(int(proc.name))
            if token is None: continue
            argv = (proc / 'cmdline').read_bytes().decode().split('\0')
            if len(argv) < 2 or not Path(argv[0]).name.startswith('python'): continue
            # Only Python's script argument, allowing -u. Never match a shell command string.
            index = 2 if argv[1] == '-u' else 1
            script = Path(argv[index])
            if not script.is_absolute(): script = (proc / 'cwd').resolve() / script
            script = script.resolve()
            role = None
            if script == root / 'control-center.py': role = 'studio'
            elif script == root / 'desktop-widgets.py': role = 'widgets'
            elif script == root / 'sc.py' and '--managed' in argv[index+1:]: role = 'awake'
            elif script == root / 'updater.py' and argv[index+1:index+2] == ['watch']: role = 'watcher'
            if role: found.append((int(proc.name), token, role))
        except (OSError, ValueError, IndexError): continue
    return found

def stop_processes(items):
    pending = []
    for pid, token, role in items:
        try:
            if identity(pid) == token:
                os.kill(pid, signal.SIGTERM)
                pending.append((pid, token, role))
        except ProcessLookupError: pass
    deadline = time.monotonic() + 5
    while pending and time.monotonic() < deadline:
        alive = []
        for item in pending:
            try:
                if identity(item[0]) == item[1]:
                    # A zombie has exited and needs no further signals.
                    stat = (Path('/proc') / str(item[0]) / 'stat').read_text()
                    if stat[stat.rfind(')')+2:].split()[0] != 'Z': alive.append(item)
            except OSError: pass
        pending = alive
        if pending: time.sleep(.05)
    if pending: raise RuntimeError('An app process did not stop. Close it before trying Update again.')

def uninstall(root):
    stop_processes([p for p in processes(root) if p[2] == 'watcher'])
    path = entry_path()
    if path.exists():
        text = path.read_text()
        if MARKER in text and str(Path(root).resolve() / 'updater.py').replace('%', '%%') in text:
            path.unlink()

def restart(root, args, log, env=None):
    child = spawn(root, args, log, env)
    try:
        code = child.wait(timeout=.8)
        if code: raise RuntimeError(f'{Path(args[1]).name} could not restart. See state/{log}.')
    except subprocess.TimeoutExpired: pass
    return child

class Runtime:
    def __init__(self, root):
        self.root = Path(root)
        self.items = []
        self.awake = {}

    def capture(self):
        self.items = processes(self.root)
        try: self.awake = json.loads((self.root / 'state/keep-awake-status.json').read_text())
        except (OSError, ValueError): self.awake = {}

    def stop_workers(self):
        # Keep the GUI alive to display errors. Widgets and the helper have file writers.
        stop_processes([p for p in self.items if p[2] != 'studio'])

    def restart_workers(self):
        roles = {p[2] for p in self.items}
        running = {p[2] for p in processes(self.root)}
        if 'widgets' in roles - running:
            restart(self.root, ['/usr/bin/python3', str(self.root / 'desktop-widgets.py')], 'widgets.log')
        if 'awake' in roles - running:
            env = dict(os.environ)
            ends = self.awake.get('ends_at')
            if ends is None or ends > time.time():
                env['NEON_KEEP_AWAKE_UNTIL'] = str(ends) if ends is not None else '0'
                restart(self.root, [str(self.root / 'keep-awake-python'), '-u', str(self.root / 'sc.py'), '--managed'], 'keep-awake.log', env)
        if 'watcher' not in running: start_watcher(self.root)

    def restart_studio(self):
        studios = [p for p in self.items if p[2] == 'studio']
        if studios:
            stop_processes(studios)
            restart(self.root, ['/usr/bin/python3', str(self.root / 'control-center.py')], 'studio.log')
