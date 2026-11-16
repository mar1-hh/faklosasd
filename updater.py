#!/usr/bin/python3
"""Consent-based, user-level Git updater. No third-party Python dependencies."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import signal
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parent
REMOTE = 'https://github.com/mar1-hh/faklosasd.git'
DAY = 24 * 60 * 60

class UpdateError(RuntimeError):
    pass

class Busy(UpdateError):
    pass

def run(args, cwd, timeout=45, env=None, log=None):
    settings = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never',
                    GIT_SSH_COMMAND='ssh -oBatchMode=yes -oConnectTimeout=10')
    settings.update(env or {})
    process = subprocess.Popen(args, cwd=cwd, env=settings, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        out, err = process.communicate()
        if log is not None: write_log(log, out + err)
        raise UpdateError('The operation timed out. Check your connection and try again.')
    if log is not None: write_log(log, out + err)
    if process.returncode:
        if log is not None:
            raise UpdateError(f'Installation failed (exit {process.returncode}). See {log}; check dependencies and retry Update.')
        # Git output can contain credential-bearing URLs; keep diagnostics private.
        raise UpdateError(f'{Path(args[0]).name} failed (exit {process.returncode}). '
                          'Check your connection, repository access and Git configuration.')
    return out.decode(errors='replace').strip()

def write_log(path, contents):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'wb') as stream: stream.write(contents)

def read_json(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def expected_url(url):
    return url in (REMOTE, REMOTE[:-4], 'git@github.com:mar1-hh/faklosasd.git',
                   'git@github.com:mar1-hh/faklosasd',
                   'ssh://git@github.com/mar1-hh/faklosasd.git')

def restore_tree(source, destination):
    """Restore files without following destination symlinks or replacing directories."""
    if source.is_symlink():
        if destination.is_dir() and not destination.is_symlink():
            raise OSError(f'Cannot restore a link over directory: {destination}')
        if destination.is_symlink() or destination.exists(): destination.unlink()
        destination.symlink_to(os.readlink(source))
    elif source.is_dir():
        if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
            raise OSError(f'Cannot restore directory over changed path: {destination}')
        destination.mkdir(exist_ok=True)
        for child in source.iterdir(): restore_tree(child, destination / child.name)
    else:
        if destination.is_symlink(): destination.unlink()
        shutil.copy2(source, destination)

class Updater:
    def __init__(self, root=ROOT, remote=REMOTE, clock=time.time, notifier=None, runtime=None):
        self.root = Path(root).resolve()
        self.remote = remote  # Dependency injection for local-repository tests; CLI is fixed.
        self.directory = self.root / 'state/updater'
        self.path = self.directory / 'status.json'
        self.clock = clock
        self.notifier = notifier or desktop_notification
        self.runtime = runtime

    def state(self):
        return read_json(self.path)

    def publish(self, **values):
        state = self.state()
        state.update(values)
        write_json(self.path, state)
        return state

    @contextmanager
    def lock(self, name='operation'):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.directory / (name + '.lock')).open('a+') as stream:
            try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise Busy('An update check or installation is already running.')
            try: yield
            finally: fcntl.flock(stream, fcntl.LOCK_UN)

    def git(self, *args):
        return run(['git', *args], self.root)

    def validate(self, clean=False):
        if Path(self.git('rev-parse', '--show-toplevel')).resolve() != self.root:
            raise UpdateError('Open the app from the root of its Git checkout.')
        if self.git('branch', '--show-current') != 'main':
            raise UpdateError('Updates require the main branch. Preserve your work before switching branches.')
        urls = self.git('remote', 'get-url', '--all', 'origin').splitlines()
        if not urls or not all(expected_url(u) if self.remote == REMOTE else u == self.remote for u in urls):
            raise UpdateError('Unexpected origin remote. Expected mar1-hh/faklosasd; nothing was overwritten.')
        # Refuse in-progress merges, rebases, cherry-picks and Git worktrees in transition.
        for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply'):
            path = Path(self.git('rev-parse', '--git-path', name))
            if not path.is_absolute(): path = self.root / path
            if path.exists(): raise UpdateError('Finish or abort the existing Git operation before updating.')
        if clean and self.git('status', '--porcelain=v1', '--untracked-files=all'):
            raise UpdateError('Local modifications or untracked files exist. Commit or move them before updating; nothing was overwritten.')
        return self.git('rev-parse', 'HEAD')

    def fetch(self):
        # Public HTTPS works at login without an unlocked SSH agent. Never edits origin.
        self.git('fetch', '--no-tags', '--no-recurse-submodules', self.remote,
                 '+refs/heads/main:refs/remotes/origin/main')
        return self.git('rev-parse', 'refs/remotes/origin/main')

    def ancestor(self, older, newer):
        return self.git('merge-base', older, newer) == older

    def inspect(self, head, target):
        if head == target: return 'current', 'Neon Studio is up to date.', False
        if not self.ancestor(head, target):
            raise UpdateError('Local commits are ahead of or diverge from main. Preserve and reconcile them manually; nothing was overwritten.')
        try: self.validate(clean=True)
        except UpdateError as error: return 'blocked', str(error), False
        self.protect_paths(head, target)
        return 'available', f'Update available: {head[:8]} → {target[:8]}. Click Update to install.', True

    def protect_paths(self, head, target):
        # An incoming commit must never turn ignored personal files into tracked files.
        names = self.git('diff', '--name-only', '-z', head, target).split('\0')
        tracked = self.git('ls-tree', '-r', '--name-only', '-z', target).split('\0')
        ignored = self.git('ls-files', '--others', '--ignored', '--exclude-standard', '-z').split('\0')
        for name in names:
            if name and any(item and (name == item or item.startswith(name + '/') or name.startswith(item + '/')) for item in ignored):
                raise UpdateError('The update would replace an ignored local file. Move it to safety before updating.')
        for name in names + tracked:
            parts = Path(name).parts
            if not parts: continue
            if (parts[0] == 'state' and name != 'state/.gitkeep') or parts[0] in (
                    'python', 'keep-awake-python', '.ssh', '.aws', '.venv', 'venv') or parts[0].startswith('.env'):
                raise UpdateError('The incoming version includes a protected personal-data path. Update refused.')

    def check(self, force=False):
        try:
            with self.lock():
                previous = self.state()
                try: last_check = float(previous['last_check'])
                except (KeyError, TypeError, ValueError): last_check = None
                if not force and last_check is not None and self.clock() - last_check < DAY:
                    return previous
                self.publish(status='checking', message='Checking for updates…', can_update=False,
                             last_check=self.clock())
                try:
                    head = self.validate()
                    target = self.fetch()
                    status, message, allowed = self.inspect(head, target)
                    if previous.get('repair_needed') and head == target:
                        status, message, allowed = 'repair', 'Code is updated; installation needs retrying. Click Update.', True
                    state = self.publish(status=status, message=message, head=head,
                                         target=target, can_update=allowed)
                    notified = state.get('notified_commits', [])
                    if not isinstance(notified, list): notified = []
                    if head != target and target not in notified:
                        if self.notifier(message):
                            state = self.publish(notified_commits=notified + [target])
                    return state
                except (OSError, UpdateError) as error:
                    return self.publish(status='error', message=str(error), can_update=False)
        except Busy:
            return self.state()

    def backup(self):
        folder = self.directory / 'backups' / (str(time.time_ns()))
        folder.mkdir(parents=True, mode=0o700)
        source = self.root / 'state'
        # Refuse sockets/FIFOs: copying them can hang an update indefinitely.
        for directory, folders, files in os.walk(source, followlinks=False):
            if Path(directory) == source and 'updater' in folders: folders.remove('updater')
            for name in folders + files:
                mode = (Path(directory) / name).lstat().st_mode
                if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode) or stat.S_ISLNK(mode)):
                    raise UpdateError('Unsupported runtime file type in state/. Close its owner before updating.')
        shutil.copytree(source, folder / 'state', symlinks=True,
                        ignore=lambda path, names: [n for n in names if (Path(path) == source and n in ('updater', '.gitkeep'))
                                                   or n.endswith(('.pid', '.lock'))])
        for name in ('python', 'keep-awake-python', '.env'):
            path = self.root / name
            if path.is_symlink(): (folder / name).symlink_to(os.readlink(path))
            elif path.is_file(): shutil.copy2(path, folder / name)
        return folder

    def restore(self, folder):
        # Restore existing personal data, retaining any newly created installer backups.
        restore_tree(folder / 'state', self.root / 'state')
        for name in ('python', 'keep-awake-python', '.env'):
            path = folder / name
            if path.is_symlink() or path.is_file():
                destination = self.root / name
                if destination.is_symlink() or destination.is_file(): destination.unlink()
                if path.is_symlink(): destination.symlink_to(os.readlink(path))
                else: shutil.copy2(path, destination)

    def install(self, target):
        if not re.fullmatch(r'[0-9a-f]{40,64}', target):
            raise UpdateError('Check for updates before clicking Update.')
        with self.lock():
            runtime = self.runtime
            if runtime is None:
                from update_runtime import Runtime
                runtime = Runtime(self.root)
            snapshot = None
            stopped = False
            merged = False
            try:
                previous = self.state()
                head = self.validate(clean=True)
                latest = self.fetch()
                if latest != target:
                    raise UpdateError('Main changed since your last check. Check again and review the new update.')
                if head == target and not previous.get('repair_needed'):
                    return self.publish(status='current', message='Neon Studio is up to date.', can_update=False)
                if head != target and not self.ancestor(head, target):
                    raise UpdateError('Local commits diverge from main. Nothing was overwritten.')
                self.protect_paths(head, target)
                self.publish(status='updating', message='Installing update. Please leave settings unchanged…', can_update=False)
                runtime.capture()
                stopped = True
                runtime.stop_workers()
                snapshot = self.backup()
                self.publish(backup=str(snapshot), repair_needed=True)
                # Recheck after stopping writers and immediately before Git changes files.
                self.validate(clean=True)
                self.git('-c', 'core.hooksPath=/dev/null', 'merge', '--ff-only', '--no-edit', target)
                merged = True
                env = {}
                for name, key in (('python', 'NEON_LOGTIME_PYTHON'), ('keep-awake-python', 'NEON_KEEP_AWAKE_PYTHON')):
                    path = self.root / name
                    if path.exists(): env[key] = str(path.resolve())
                run(['bash', 'install.sh', '--no-start'], self.root, timeout=120, env=env,
                    log=self.directory / 'install.log')
                self.restore(snapshot)
                snapshot = None
                runtime.restart_workers()
                stopped = False
                self.publish(status='current', message='Update installed successfully.', head=target,
                             target=target, can_update=False, repair_needed=False)
                runtime.restart_studio()
                return self.state()
            except (OSError, UpdateError, RuntimeError) as error:
                if snapshot is not None:
                    try: self.restore(snapshot)
                    except OSError as restore_error:
                        error = UpdateError(f'{error} Personal-data restore failed: {restore_error}. Backup: {snapshot}')
                if stopped:
                    try: runtime.restart_workers()
                    except (OSError, RuntimeError) as restart_error:
                        error = UpdateError(f'{error} Restart failed: {restart_error}')
                return self.publish(status='error', message=str(error), can_update=False,
                                    repair_needed=merged or self.state().get('repair_needed', False))

def desktop_notification(message):
    if not shutil.which('notify-send'): return False
    try:
        run(['notify-send', '--app-name=Neon Studio', 'Neon Studio update',
             message + '\nOpen Neon Studio → Tools → Updates.'], ROOT, timeout=5)
        return True
    except (OSError, UpdateError): return False

def watch():
    updater = Updater()
    try:
        with updater.lock('watcher'):
            stop = threading.Event()
            signal.signal(signal.SIGTERM, lambda *_: stop.set())
            signal.signal(signal.SIGINT, lambda *_: stop.set())
            while not stop.is_set():
                updater.check()
                stop.wait(60)
    except Busy: pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('watch', 'check', 'update', 'register', 'start', 'uninstall'))
    parser.add_argument('--target')
    args = parser.parse_args()
    if args.command == 'watch': watch()
    elif args.command == 'check': print(json.dumps(Updater().check(force=True)))
    elif args.command == 'update':
        if not args.target: parser.error('update requires --target from a completed check')
        try: result = Updater().install(args.target)
        except (OSError, UpdateError) as error: print(error); return 1
        print(result.get('message', '')); return int(result.get('status') == 'error')
    else:
        from update_runtime import register, start_watcher, uninstall
        if args.command == 'register': register(ROOT)
        elif args.command == 'start': start_watcher(ROOT)
        else:
            with Updater().lock(): uninstall(ROOT)
    return 0

if __name__ == '__main__':
    try: raise SystemExit(main())
    except (OSError, UpdateError, RuntimeError) as error:
        print(str(error)); raise SystemExit(1)
