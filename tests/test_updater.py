import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from updater import Updater, UpdateError, Busy, DAY, expected_url, run
import update_runtime

class Runtime:
    def __init__(self): self.events=[]
    def capture(self): self.events.append('capture')
    def stop_workers(self): self.events.append('stop')
    def restart_workers(self): self.events.append('workers')
    def restart_studio(self): self.events.append('studio')

class Updates(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.source=self.base/'source';self.source.mkdir()
        self.remote=self.base/'remote.git';self.root=self.base/'installed'
        self.git(self.source,'init','-b','main')
        (self.source/'.gitignore').write_text('/state/*\n!/state/.gitkeep\n/python\n/keep-awake-python\n.env*\n*.private\n')
        (self.source/'state').mkdir();(self.source/'state/.gitkeep').touch()
        (self.source/'version').write_text('one')
        (self.source/'install.sh').write_text('#!/bin/bash\nset -e\nprintf damaged > state/preferences.json\nprintf installed > state/installed\n')
        self.commit('initial')
        self.git(self.base,'clone','--bare',str(self.source),str(self.remote))
        self.git(self.base,'clone',str(self.remote),str(self.root))
        self.runtime=Runtime();self.now=200000.;self.notices=[]
        self.u=Updater(self.root,str(self.remote),clock=lambda:self.now,
                       notifier=lambda message:self.notices.append(message) or True,runtime=self.runtime)
    def git(self,root,*args):
        env=dict(os.environ,GIT_AUTHOR_NAME='Test',GIT_AUTHOR_EMAIL='test@example.com',
                 GIT_COMMITTER_NAME='Test',GIT_COMMITTER_EMAIL='test@example.com')
        return subprocess.check_output(['git',*args],cwd=root,env=env,stderr=subprocess.DEVNULL).decode().strip()
    def commit(self,message):
        self.git(self.source,'add','-A');self.git(self.source,'commit','-m',message)
        return self.git(self.source,'rev-parse','HEAD')
    def feature(self):
        (self.source/'version').write_text('two');target=self.commit('feature')
        self.git(self.source,'push',str(self.remote),'main');return target
    def test_current_and_available(self):
        self.assertEqual(self.u.check()['status'],'current')
        target=self.feature();state=self.u.check(force=True)
        self.assertEqual(state['target'],target);self.assertTrue(state['can_update'])
        self.assertEqual(state['status'],'available');self.assertEqual(len(self.notices),1)
    def test_daily_checks_and_notification_dedup_across_restarts(self):
        target=self.feature();self.u.check()
        with patch.object(self.u,'fetch',side_effect=AssertionError('too soon')):
            self.u.check();self.now+=DAY-1;self.u.check()
        self.now+=1;self.u.check()
        self.u.check(force=True)
        self.assertEqual(len(self.notices),1)
        self.assertIn(target,Updater(self.root).state()['notified_commits'])
    def test_offline_is_rate_limited_and_manual_check_can_retry(self):
        with patch.object(self.u,'fetch',side_effect=UpdateError('Offline')) as fetch:
            self.assertEqual(self.u.check()['message'],'Offline')
            self.u.check();self.assertEqual(fetch.call_count,1)
        self.assertEqual(self.u.check(force=True)['status'],'current')
    def test_dirty_and_untracked_never_overwritten(self):
        target=self.feature()
        for path in ('version','untracked.txt'):
            with self.subTest(path=path):
                file=self.root/path;file.write_text('personal')
                state=self.u.check(force=True);self.assertEqual(state['status'],'blocked')
                self.u.install(target)
                self.assertEqual(file.read_text(),'personal');self.assertEqual(self.runtime.events,[])
                if path=='version':self.git(self.root,'restore','version')
                else:file.unlink()
    def test_staged_change_is_protected(self):
        target=self.feature();(self.root/'version').write_text('mine');self.git(self.root,'add','version')
        self.u.install(target)
        self.assertEqual((self.root/'version').read_text(),'mine');self.assertEqual(self.runtime.events,[])
    def test_divergent_and_ahead_history_blocked(self):
        (self.root/'local').write_text('mine');self.git(self.root,'add','local');self.git(self.root,'commit','-m','local')
        self.assertEqual(self.u.check(force=True)['status'],'error')
        self.feature();self.assertEqual(self.u.check(force=True)['status'],'error')
        self.assertIn('diverge',self.u.state()['message'])
    def test_wrong_branch_and_remote(self):
        self.git(self.root,'switch','-c','personal')
        self.assertIn('main branch',self.u.check(force=True)['message'])
        self.git(self.root,'switch','main');self.git(self.root,'remote','set-url','origin','https://example.com/other.git')
        self.assertIn('Unexpected origin',self.u.check(force=True)['message'])
    def test_remote_changed_after_click_requires_another_click(self):
        target=self.feature();self.u.check()
        (self.source/'new').write_text('new');self.commit('another');self.git(self.source,'push',str(self.remote),'main')
        self.u.install(target)
        self.assertIn('Main changed',self.u.state()['message']);self.assertEqual(self.runtime.events,[])
    def test_fast_forward_preserves_preferences_wallpapers_credentials_and_pins(self):
        target=self.feature();self.u.check()
        prefs=b'{"notes":"my note", "keep_awake_enabled":false}\n'
        (self.root/'state/preferences.json').write_bytes(prefs)
        (self.root/'state/wallpapers').mkdir();(self.root/'state/wallpapers/mine.png').write_bytes(b'personal wallpaper')
        (self.root/'.env').write_text('TOKEN=personal')
        (self.root/'python').symlink_to('/usr/bin/python3')
        config=(self.root/'.git/config').read_bytes()
        result=self.u.install(target)
        self.assertEqual(result['status'],'current');self.assertEqual(self.git(self.root,'rev-parse','HEAD'),target)
        self.assertEqual((self.root/'state/preferences.json').read_bytes(),prefs)
        self.assertEqual((self.root/'state/wallpapers/mine.png').read_bytes(),b'personal wallpaper')
        self.assertEqual((self.root/'.env').read_text(),'TOKEN=personal')
        self.assertEqual((self.root/'python').resolve(),Path('/usr/bin/python3').resolve())
        self.assertEqual((self.root/'.git/config').read_bytes(),config)
        self.assertEqual(self.runtime.events,['capture','stop','workers','studio'])
    def test_personal_state_symlinks_survive_restore(self):
        target=self.feature()
        outside=self.base/'personal-note';outside.write_text('private')
        (self.root/'state/note-link').symlink_to(outside)
        self.assertEqual(self.u.install(target)['status'],'current')
        self.assertTrue((self.root/'state/note-link').is_symlink())
        self.assertEqual(outside.read_text(),'private')
    def test_detached_head_is_explained(self):
        self.git(self.root,'checkout','--detach')
        self.assertIn('main branch',self.u.check(force=True)['message'])
    def test_installer_failure_restores_data_and_can_retry(self):
        (self.source/'install.sh').write_text('printf damaged > state/preferences.json\nexit 1\n')
        self.commit('broken installer');target=self.feature()
        (self.root/'state/preferences.json').write_text('personal notes')
        result=self.u.install(target)
        self.assertEqual(result['status'],'error');self.assertTrue(result['repair_needed'])
        self.assertEqual((self.root/'state/preferences.json').read_text(),'personal notes')
        self.assertEqual(self.runtime.events,['capture','stop','workers'])
        self.assertEqual(self.u.check(force=True)['status'],'repair')
        # Installer-only retry for an already fast-forwarded checkout.
        original_run=run
        def retry(args,*a,**kw):
            if args[0]=='bash':return ''
            return original_run(args,*a,**kw)
        with patch('updater.run',side_effect=retry):result=self.u.install(target)
        self.assertEqual(result['status'],'current');self.assertFalse(result['repair_needed'])
    def test_incoming_state_or_ignored_files_are_protected(self):
        (self.source/'state/preferences.json').write_text('hostile')
        self.git(self.source,'add','-f','state/preferences.json');self.commit('tracked private state')
        self.git(self.source,'push',str(self.remote),'main')
        self.assertIn('protected personal-data',self.u.check(force=True)['message'])
    def test_ignored_collision_is_protected(self):
        (self.root/'mine.private').write_text('personal')
        (self.source/'mine.private').write_text('upstream');self.git(self.source,'add','-f','mine.private');self.commit('collision')
        self.git(self.source,'push',str(self.remote),'main')
        state=self.u.check(force=True)
        self.assertIn('ignored local file',state['message']);self.assertEqual((self.root/'mine.private').read_text(),'personal')
    def test_concurrent_checks_and_updates_are_excluded(self):
        target=self.feature()
        with self.u.lock():
            other=Updater(self.root,str(self.remote))
            with self.assertRaises(Busy):other.install(target)
            with patch.object(other,'fetch',side_effect=AssertionError('must not fetch')):other.check(force=True)
    def test_git_failure_does_not_stop_running_apps(self):
        target=self.feature()
        with patch.object(self.u,'fetch',side_effect=UpdateError('Network failure')):result=self.u.install(target)
        self.assertEqual(result['status'],'error');self.assertEqual(self.runtime.events,[])
    def test_stop_failure_attempts_to_restart_partially_stopped_apps(self):
        target=self.feature()
        with patch.object(self.runtime,'stop_workers',side_effect=RuntimeError('still running')):
            self.u.install(target)
        self.assertIn('workers',self.runtime.events);self.assertNotIn('studio',self.runtime.events)
    def test_timeout_is_bounded(self):
        with self.assertRaisesRegex(UpdateError,'timed out'):
            run(['/usr/bin/python3','-c','import time;time.sleep(10)'],self.root,timeout=.05)
    def test_expected_urls(self):
        self.assertTrue(expected_url('git@github.com:mar1-hh/faklosasd.git'))
        self.assertFalse(expected_url('https://github.com/other/faklosasd.git'))
        self.assertFalse(expected_url('https://token@github.com/mar1-hh/faklosasd.git'))

class Startup(unittest.TestCase):
    def test_register_uninstall_and_foreign_entry_protection(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'XDG_CONFIG_HOME':directory}):
            root=Path(directory)/'checkout';root.mkdir()
            update_runtime.register(root)
            text=update_runtime.entry_path().read_text()
            self.assertIn('updater.py" watch',text);self.assertIn(update_runtime.MARKER,text)
            with patch.object(update_runtime,'processes',return_value=[]):update_runtime.uninstall(root)
            self.assertFalse(update_runtime.entry_path().exists())
            update_runtime.entry_path().write_text('unrelated')
            with self.assertRaises(RuntimeError):update_runtime.register(root)
            with patch.object(update_runtime,'processes',return_value=[]):update_runtime.uninstall(root)
            self.assertEqual(update_runtime.entry_path().read_text(),'unrelated')
    def test_real_watcher_is_singleton_and_uninstall_stops_it(self):
        import shutil
        import sys
        import time
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'XDG_CONFIG_HOME':directory}):
            root=Path(directory)/'checkout';root.mkdir()
            shutil.copy2(Path(__file__).resolve().parents[1]/'updater.py',root/'updater.py')
            state=root/'state/updater';state.mkdir(parents=True)
            cached={'last_check':time.time(),'status':'current','message':'Cached result'}
            (state/'status.json').write_text(json.dumps(cached))
            update_runtime.register(root)
            child=subprocess.Popen([sys.executable,str(root/'updater.py'),'watch'])
            try:
                deadline=time.monotonic()+3
                while not (state/'watcher.lock').exists() and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue((state/'watcher.lock').exists())
                second=subprocess.run([sys.executable,str(root/'updater.py'),'watch'],timeout=3)
                self.assertEqual(second.returncode,0)
                self.assertIsNone(child.poll())
                self.assertEqual(json.loads((state/'status.json').read_text()),cached)
                update_runtime.uninstall(root)
                self.assertEqual(child.wait(timeout=3),0)
                self.assertFalse(update_runtime.entry_path().exists())
            finally:
                if child.poll() is None:child.terminate()
                child.wait(timeout=3)
    def test_process_restart_preserves_roles_and_remaining_awake_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);runtime=update_runtime.Runtime(root)
            runtime.items=[(1,'a','widgets'),(2,'b','awake'),(3,'c','studio')]
            end=__import__('time').time()+100;runtime.awake={'ends_at':end}
            with patch.object(update_runtime,'processes',return_value=[]),patch.object(update_runtime,'spawn') as spawn,patch.object(update_runtime,'restart',side_effect=lambda *args: spawn(*args)):
                runtime.restart_workers()
                calls=spawn.call_args_list
                self.assertEqual(len(calls),3)
                self.assertEqual(calls[1].args[3]['NEON_KEEP_AWAKE_UNTIL'],str(end))
                self.assertFalse(any('control-center.py' in str(c) for c in calls))
    def test_process_discovery_excludes_other_checkouts(self):
        import sys
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'ours';other=Path(directory)/'other'
            root.mkdir();other.mkdir()
            children=[]
            try:
                for folder in (root,other):
                    script=folder/'desktop-widgets.py'
                    script.write_text('import time; time.sleep(30)')
                    children.append(subprocess.Popen([sys.executable,str(script)]))
                found=update_runtime.processes(root)
                self.assertIn(children[0].pid,[p[0] for p in found])
                self.assertNotIn(children[1].pid,[p[0] for p in found])
                update_runtime.stop_processes(found)
                children[0].wait(timeout=2)
                self.assertIsNone(children[1].poll())
            finally:
                for child in children:
                    if child.poll() is None:child.terminate()
                    child.wait(timeout=2)
    def test_recycled_pid_is_not_signalled(self):
        with patch.object(update_runtime,'identity',return_value='different'),patch.object(os,'kill') as kill:
            update_runtime.stop_processes([(123,'original','widgets')])
            kill.assert_not_called()

if __name__=='__main__':unittest.main()
