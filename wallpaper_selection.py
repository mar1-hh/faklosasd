"""Debounce gallery clicks while keeping startup previews side-effect free."""
class ClickApply:
 def __init__(self,scheduler,apply,delay=180):
  self.scheduler=scheduler;self.apply=apply;self.delay=delay;self.source=None;self.closed=False
 def clicked(self,path):
  if self.closed:return
  if self.source is not None:self.scheduler.source_remove(self.source)
  def run():
   self.source=None
   if not self.closed:self.apply(path)
   return False
  self.source=self.scheduler.timeout_add(self.delay,run)
 def close(self):
  self.closed=True
  if self.source is not None:self.scheduler.source_remove(self.source);self.source=None
