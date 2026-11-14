"""Download the requested series into the private collection, off the UI thread."""
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from preferences import ROOT
from wallpaper_collection import import_image,image_info
MANIFEST=ROOT/'wallpapers/ANIME_PACK.json'
RECEIPTS=ROOT/'state/anime-pack.json'
ALLOWED_HOSTS={'4kwallpapers.com','images4.alphacoders.com','images8.alphacoders.com'}
MAX_BYTES=70*1024*1024

def entries():return json.loads(MANIFEST.read_text())
def load_receipts(path=RECEIPTS):
 try:
  result=json.loads(Path(path).read_text());return result if isinstance(result,dict) else {}
 except (OSError,ValueError):return {}
def write_receipts(path,data):
 from native_wallpaper import atomic_write
 atomic_write(Path(path),json.dumps(data,indent=2))
def cached(item,records):
 record=records.get(item['id'],{})
 try:
  path=Path(record['file'])
  if path.is_file():return path
 except (KeyError,TypeError):pass
 return None

def download(item,destination,opener=urlopen):
 url=item['url'];parsed=urlparse(url)
 if parsed.scheme!='https' or parsed.hostname not in ALLOWED_HOSTS:raise ValueError('Unsupported wallpaper download source.')
 filename=item['filename']
 if Path(filename).name!=filename:raise ValueError('Invalid wallpaper filename.')
 destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='.anime-download-',dir=destination) as folder:
  incoming=Path(folder)/filename
  request=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; NeonStudio/1.0)','Referer':item['source'],'Accept':'image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8'})
  with opener(request,timeout=30) as response,incoming.open('wb') as output:
   if urlparse(response.geturl()).scheme!='https':raise ValueError('The wallpaper download redirected to an insecure URL.')
   total=0
   for chunk in iter(lambda:response.read(65536),b''):
    total+=len(chunk)
    if total>MAX_BYTES:raise ValueError('Wallpaper download exceeds 70 MB.')
    output.write(chunk)
  width,height=image_info(incoming)
  import gi
  gi.require_version('GdkPixbuf','2.0')
  from gi.repository import GdkPixbuf
  GdkPixbuf.Pixbuf.new_from_file_at_scale(str(incoming),32,32,True)
  if width<item['minimum_width'] or height<item['minimum_height']:raise ValueError(f'Download was {width}×{height}; the requested original 4K image was not returned.')
  path=import_image(incoming,destination)
  return path,width,height

def download_pack(progress=None,manifest=None,destination=None,receipts=None,opener=urlopen):
 destination=Path(destination) if destination is not None else ROOT/'state/wallpapers'
 receipts=Path(receipts) if receipts is not None else RECEIPTS
 records=load_receipts(receipts);available=[];errors=[]
 for item in (manifest if manifest is not None else entries()):
  path=cached(item,records)
  if path is None:
   try:
    path,width,height=download(item,destination,opener)
    records[item['id']]={'file':str(path),'source':item['source'],'width':width,'height':height,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    write_receipts(receipts,records)
   except Exception as error:
    errors.append((item['title'],str(error)))
    if progress:progress(item,None,str(error))
    continue
  available.append(path)
  if progress:progress(item,path,None)
 return available,errors

if __name__=='__main__':
 import sys
 def report(item,path,error):
  print(('Ready: '+item['title']) if path else ('Failed: '+item['title']+' — '+str(error)),flush=True)
 available,errors=download_pack(progress=report)
 print(f'{len(available)}/4 wallpapers ready.')
 sys.exit(1 if errors else 0)
