"""Import durability, collision safety and real image validation."""
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gi
gi.require_version('GdkPixbuf','2.0')
from gi.repository import GdkPixbuf
from wallpaper_collection import import_image,image_info,collection_paths
class CollectionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.imports=self.root/'imported'
 def tearDown(self):self.tmp.cleanup()
 def image(self,path,color):
  path.parent.mkdir(parents=True,exist_ok=True)
  pix=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,False,8,20,12);pix.fill(color);pix.savev(str(path),'png',[],[]);return path
 def test_import_survives_original_removal(self):
  source=self.image(self.root/'source.png',0xff0000ff);target=import_image(source,self.imports);source.unlink()
  self.assertEqual(image_info(target),(20,12))
 def test_imported_content_is_deduplicated(self):
  source=self.image(self.root/'one.png',0xff0000ff);other=self.root/'two.png';other.write_bytes(source.read_bytes())
  self.assertEqual(import_image(source,self.imports),import_image(other,self.imports))
 def test_filename_collision_never_overwrites(self):
  first=self.image(self.root/'a/same.png',0xff0000ff);second=self.image(self.root/'b/same.png',0x00ff00ff)
  a=import_image(first,self.imports);b=import_image(second,self.imports)
  self.assertNotEqual(a,b);self.assertEqual(a.name,'same.png');self.assertEqual(b.name,'same-2.png')
  self.assertEqual(a.read_bytes(),first.read_bytes());self.assertEqual(b.read_bytes(),second.read_bytes())
 def test_invalid_image_is_not_added(self):
  source=self.root/'broken.png';source.write_text('not an image')
  with self.assertRaises(ValueError):import_image(source,self.imports)
  self.assertFalse(self.imports.exists())
 def test_gallery_combines_imports_without_duplicate_paths(self):
  source=self.image(self.root/'source.png',0xff0000ff);imported=import_image(source,self.imports)
  self.assertEqual(len(collection_paths(self.root,self.imports,self.root/'missing')),2)
  self.assertEqual(collection_paths(self.imports,self.imports,self.root/'missing'),[imported])
if __name__=='__main__':unittest.main()
