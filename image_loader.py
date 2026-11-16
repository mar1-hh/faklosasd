"""Bounded asynchronous image decoding; delivery always happens on the UI loop."""
from collections import OrderedDict
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

class ImageLoader:
 def __init__(self,schedule,decode,capacity=96):
  self.schedule=schedule;self.decode=decode;self.capacity=capacity
  self.cache=OrderedDict();self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='wallpaper')
  self.closed=False;self._lock=Lock()
 def request(self,path,width,height,callback):
  if self.closed:return
  def work():
   stat=path.stat();key=(str(path),stat.st_mtime_ns,stat.st_size,width,height)
   # Cache access is serialized separately from potentially slow decoding.
   with self.lock:
    if key in self.cache:
     self.cache.move_to_end(key);return self.cache[key]
   value=self.decode(path,width,height)
   with self.lock:
    self.cache[key]=value
    while len(self.cache)>self.capacity:self.cache.popitem(last=False)
   return value
  future=self.pool.submit(work)
  def done(result):
   try:value=result.result()
   except Exception:value=None
   if not self.closed:self.schedule(self.deliver,callback,value)
  future.add_done_callback(done)
 def deliver(self,callback,value):
  if not self.closed:callback(value)
  return False
 def close(self):
  self.closed=True;self.pool.shutdown(wait=False,cancel_futures=True)
 @property
 def lock(self):
  return self._lock
