"""Nonblocking browser/app launches, independent of hidden widget windows."""
from gi.repository import Gio,GLib

class ExternalActions:
 def __init__(self,gio=Gio,glib=GLib):
  self.gio=gio;self.glib=glib;self.pending=[];self.closed=False
 def _launch(self,start,finish,callback):
  if self.closed:return
  request={'done':False,'timer':None,'cancel':self.gio.Cancellable.new()}
  self.pending.append(request)
  def complete(message):
   if request['done']:return
   request['done']=True
   if request['timer'] is not None:
    self.glib.source_remove(request['timer']);request['timer']=None
   if request in self.pending:self.pending.remove(request)
   if not self.closed:callback(message)
  def ready(source,result,*_):
   if request['done']:return
   try:
    if not finish(result):raise RuntimeError('The application could not be opened.')
    complete(None)
   except Exception as error:complete(str(error))
  def timeout():
   request['timer']=None
   complete('The application did not respond. You can try again.')
   request['cancel'].cancel()
   return self.glib.SOURCE_REMOVE
  request['timer']=self.glib.timeout_add_seconds(15,timeout)
  try:start(request['cancel'],ready)
  except Exception as error:complete(str(error))
 def open_uri(self,uri,callback):
  self._launch(lambda cancel,ready:self.gio.AppInfo.launch_default_for_uri_async(uri,None,cancel,ready,None),self.gio.AppInfo.launch_default_for_uri_finish,callback)
 def open_app(self,app,callback):
  self._launch(lambda cancel,ready:app.launch_uris_async([],None,cancel,ready,None),app.launch_uris_finish,callback)
 def close(self):
  self.closed=True
  for request in list(self.pending):
   request['done']=True
   if request['timer'] is not None:self.glib.source_remove(request['timer'])
   request['cancel'].cancel()
  self.pending.clear()
