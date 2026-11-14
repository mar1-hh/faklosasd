"""A browser launch must never wait on or terminate the widget event loop."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from external_actions import ExternalActions

class Timers:
 SOURCE_REMOVE=False
 def __init__(self):self.callbacks={};self.next_id=0
 def timeout_add_seconds(self,seconds,callback):
  self.next_id+=1;self.callbacks[self.next_id]=callback;return self.next_id
 def source_remove(self,source):self.callbacks.pop(source,None)
class Cancel:
 def __init__(self):self.cancelled=False
 @classmethod
 def new(cls):return cls()
 def cancel(self):self.cancelled=True
class Browser:
 def __init__(self):self.calls=[]
 def launch_default_for_uri_async(self,uri,context,cancel,callback,data):self.calls.append((uri,cancel,callback))
 def launch_default_for_uri_finish(self,result):
  if isinstance(result,Exception):raise result
  return result
class ExternalActionsTests(unittest.TestCase):
 def setUp(self):
  self.browser=Browser();self.timers=Timers();self.messages=[]
  self.actions=ExternalActions(SimpleNamespace(AppInfo=self.browser,Cancellable=Cancel),self.timers)
 def test_launch_returns_before_browser_responds(self):
  self.actions.open_uri('https://profile.intra.42.fr/',self.messages.append)
  self.assertEqual(self.messages,[]);self.assertEqual(len(self.actions.pending),1)
  uri,cancel,callback=self.browser.calls[0]
  self.assertEqual(uri,'https://profile.intra.42.fr/')
  callback(None,True,None)
  self.assertEqual(self.messages,[None]);self.assertFalse(self.actions.pending);self.assertFalse(self.timers.callbacks)
 def test_browser_failure_is_reported_without_exception(self):
  self.actions.open_uri('https://profile.intra.42.fr/',self.messages.append)
  self.browser.calls[0][2](None,RuntimeError('No browser available'),None)
  self.assertEqual(self.messages,['No browser available']);self.assertFalse(self.actions.pending)
 def test_timeout_releases_request_without_stopping_widgets(self):
  self.actions.open_uri('https://profile.intra.42.fr/',self.messages.append)
  callback=next(iter(self.timers.callbacks.values()));callback()
  self.assertTrue(self.browser.calls[0][1].cancelled);self.assertEqual(len(self.messages),1)
  self.browser.calls[0][2](None,True,None)
  self.assertEqual(len(self.messages),1) # Late browser reply cannot call destroyed UI twice.
 def test_shutdown_cancels_requests_and_ignores_late_reply(self):
  self.actions.open_uri('https://profile.intra.42.fr/',self.messages.append);self.actions.close()
  self.browser.calls[0][2](None,True,None)
  self.assertEqual(self.messages,[]);self.assertFalse(self.timers.callbacks)
 def test_app_launcher_is_also_asynchronous(self):
  calls=[]
  app=SimpleNamespace(launch_uris_async=lambda uris,ctx,cancel,callback,data:calls.append(callback),launch_uris_finish=lambda result:True)
  self.actions.open_app(app,self.messages.append)
  self.assertEqual(self.messages,[]);self.assertEqual(len(calls),1)
  calls[0](app,True,None);self.assertEqual(self.messages,[None])
if __name__=='__main__':unittest.main()
