import tempfile
import threading
import unittest
from pathlib import Path
from image_loader import ImageLoader

class ImageLoading(unittest.TestCase):
 def test_slow_decode_does_not_block_and_delivers_on_ui_queue(self):
  started=threading.Event();release=threading.Event();queued=threading.Event();calls=[];result=[]
  def decode(*args):started.set();release.wait(3);return 'pixels'
  def schedule(*args):calls.append(args);queued.set()
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'image';path.touch();loader=ImageLoader(schedule,decode)
   try:
    loader.request(path,240,135,result.append)
    self.assertTrue(started.wait(1));self.assertEqual(result,[])
    release.set();self.assertTrue(queued.wait(1));self.assertEqual(result,[])
    callback,*args=calls.pop();callback(*args);self.assertEqual(result,['pixels'])
   finally:release.set();loader.close()
 def test_cache_invalidates_when_file_changes_and_close_discards_delivery(self):
  queued=threading.Event();calls=[];decodes=[];results=[]
  def schedule(*args):calls.append(args);queued.set()
  def decode(path,*size):decodes.append(path.read_bytes());return decodes[-1]
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'image';path.write_bytes(b'one');loader=ImageLoader(schedule,decode)
   try:
    for change in (None,None,b'changed'):
     if change:path.write_bytes(change)
     queued.clear();loader.request(path,240,135,results.append);self.assertTrue(queued.wait(1))
     callback,*args=calls.pop();callback(*args)
    self.assertEqual(decodes,[b'one',b'changed'])
    queued.clear();loader.request(path,240,135,results.append);self.assertTrue(queued.wait(1))
    loader.close();callback,*args=calls.pop();callback(*args)
    self.assertEqual(len(results),3)
   finally:loader.close()
 def test_bad_image_does_not_break_worker(self):
  queued=threading.Event();calls=[]
  def schedule(*args):calls.append(args);queued.set()
  loader=ImageLoader(schedule,lambda *args:None)
  try:
   loader.request(Path('/nonexistent/neon-image'),1,1,lambda value:self.assertIsNone(value))
   self.assertTrue(queued.wait(1));callback,*args=calls.pop();callback(*args)
  finally:loader.close()
