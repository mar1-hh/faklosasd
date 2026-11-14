"""Network-free checks for the requested series downloader."""
from io import BytesIO
from pathlib import Path
import json,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gi
gi.require_version('GdkPixbuf','2.0')
from gi.repository import GdkPixbuf
import anime_pack
class Response(BytesIO):
 def __init__(self,data,url):super().__init__(data);self.url=url
 def geturl(self):return self.url
class AnimePackTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  path=self.root/'source.png';pix=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,False,8,20,12);pix.fill(0x4433ffff);pix.savev(str(path),'png',[],[]);self.data=path.read_bytes()
  self.item={'id':'test','title':'Test anime','filename':'test.png','url':'https://4kwallpapers.com/test.png','source':'https://4kwallpapers.com/source.html','minimum_width':20,'minimum_height':12}
  self.calls=[]
 def tearDown(self):self.tmp.cleanup()
 def opener(self,request,**kwargs):
  self.calls.append(request.full_url);return Response(self.data,request.full_url)
 def test_all_four_requested_series_have_sources(self):
  entries=anime_pack.entries();self.assertEqual(len(entries),4)
  self.assertEqual({item['id'] for item in entries},{'monster-johan','mushoku-tensei','naruto-rasengan','orb-rafal'})
  for item in entries:self.assertGreaterEqual(item['minimum_width'],3840);self.assertGreaterEqual(item['minimum_height'],2160)
 def test_download_is_validated_and_receipted(self):
  destination=self.root/'collection';receipts=self.root/'receipt.json'
  available,errors=anime_pack.download_pack(manifest=[self.item],destination=destination,receipts=receipts,opener=self.opener)
  self.assertEqual(errors,[]);self.assertEqual(len(available),1)
  record=json.loads(receipts.read_text())['test'];self.assertEqual(record['width'],20);self.assertEqual(record['height'],12)
 def test_cached_image_is_not_redownloaded(self):
  kwargs=dict(manifest=[self.item],destination=self.root/'collection',receipts=self.root/'receipt.json',opener=self.opener)
  anime_pack.download_pack(**kwargs);anime_pack.download_pack(**kwargs);self.assertEqual(len(self.calls),1)
 def test_smaller_image_is_not_claimed_as_4k(self):
  item=dict(self.item,minimum_width=3840,minimum_height=2160)
  available,errors=anime_pack.download_pack(manifest=[item],destination=self.root/'collection',receipts=self.root/'receipt.json',opener=self.opener)
  self.assertEqual(available,[]);self.assertEqual(len(errors),1);self.assertIn('20×12',errors[0][1]);self.assertFalse((self.root/'receipt.json').exists())
 def test_html_response_is_not_imported(self):
  self.data=b'<html>Access denied</html>'
  available,errors=anime_pack.download_pack(manifest=[self.item],destination=self.root/'collection',receipts=self.root/'receipt.json',opener=self.opener)
  self.assertEqual(available,[]);self.assertTrue(errors)
 def test_untrusted_source_and_filename_are_rejected(self):
  for item in (dict(self.item,url='file:///etc/passwd'),dict(self.item,filename='../outside.png')):
   with self.assertRaises(ValueError):anime_pack.download(item,self.root/'collection',self.opener)
if __name__=='__main__':unittest.main()
