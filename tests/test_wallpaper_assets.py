"""Bundled anime images must be actual 4K files, with provenance and no upscaling."""
import hashlib,json
from pathlib import Path
import unittest
import gi
gi.require_version('GdkPixbuf','2.0')
from gi.repository import GdkPixbuf
ROOT=Path(__file__).resolve().parents[1]
class AssetTests(unittest.TestCase):
 def test_ten_anime_wallpapers_are_real_4k_landscapes(self):
  entries=json.loads((ROOT/'wallpapers/SOURCES.json').read_text())
  self.assertEqual(len(entries),10)
  for item in entries:
   with self.subTest(file=item['file']):
    path=ROOT/'wallpapers'/item['file'];info=GdkPixbuf.Pixbuf.get_file_info(str(path));self.assertIsNotNone(info[0])
    self.assertEqual(info[1:],(item['width'],item['height']))
    self.assertGreaterEqual(info[1],3840);self.assertGreaterEqual(info[2],2160);self.assertGreater(info[1],info[2])
    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),item['sha256'])
    self.assertTrue(item['source'].startswith('https://github.com/'))
 def test_original_six_landscapes_are_preserved(self):
  files=list((ROOT/'wallpapers').glob('[0-9][0-9]-*.png'));self.assertEqual(len(files),6)
if __name__=='__main__':unittest.main()
