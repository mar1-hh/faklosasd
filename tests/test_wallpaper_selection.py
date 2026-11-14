"""Only explicit gallery clicks apply wallpapers; startup previews do not."""
from pathlib import Path
import importlib.util,sys,tempfile,unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wallpaper_selection import ClickApply
import gi
gi.require_version('GdkPixbuf','2.0')
from gi.repository import GdkPixbuf
spec=importlib.util.spec_from_file_location('selection_studio',Path(__file__).resolve().parents[1]/'control-center.py')
studio=importlib.util.module_from_spec(spec);spec.loader.exec_module(studio)
class Scheduler:
 def __init__(self):self.queue={};self.number=0
 def timeout_add(self,ms,callback):self.number+=1;self.queue[self.number]=callback;return self.number
 def source_remove(self,source):self.queue.pop(source,None)
 def flush(self):
  queued=list(self.queue.values());self.queue.clear()
  for callback in queued:callback()
class SelectionTests(unittest.TestCase):
 def test_last_rapid_click_wins(self):
  scheduler=Scheduler();applied=[];selection=ClickApply(scheduler,applied.append)
  selection.clicked('a');selection.clicked('b');selection.clicked('c');scheduler.flush()
  self.assertEqual(applied,['c'])
 def test_close_cancels_pending_apply(self):
  scheduler=Scheduler();applied=[];selection=ClickApply(scheduler,applied.append)
  selection.clicked('a');selection.close();scheduler.flush();self.assertEqual(applied,[])
 def test_queued_path_is_captured(self):
  scheduler=Scheduler();applied=[];selection=ClickApply(scheduler,applied.append)
  chosen=Path('a');selection.clicked(chosen);chosen=Path('b');scheduler.flush()
  self.assertEqual(applied,[Path('a')])
 def test_preview_does_not_apply_but_gallery_click_does(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'image.png';pix=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,False,8,20,12);pix.fill(0xff0000ff);pix.savev(str(path),'png',[],[])
   clicks=[];widget=SimpleNamespace(texture=lambda *args:None,preview=SimpleNamespace(set_paintable=lambda _:None),wall_title=SimpleNamespace(set_text=lambda _:None),wall_info=SimpleNamespace(set_text=lambda _:None),wallpaper_tiles={},selection_queue=SimpleNamespace(clicked=clicks.append),notify=lambda _:None)
   studio.Studio.select(widget,path);self.assertEqual(clicks,[])
   studio.Studio.select(widget,path,apply=True);self.assertEqual(clicks,[path])
if __name__=='__main__':unittest.main()
