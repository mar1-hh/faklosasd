"""Durable image imports; imported private files stay under Git-ignored state/."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from preferences import ROOT
SUFFIXES={'.png','.jpg','.jpeg','.webp','.bmp'}
IMPORTS=ROOT/'state/wallpapers'

def image_info(path):
 import gi
 gi.require_version('GdkPixbuf','2.0')
 from gi.repository import GdkPixbuf
 path=Path(path).expanduser()
 if not path.is_file() or path.suffix.lower() not in SUFFIXES:raise ValueError('Choose a supported image file.')
 if path.stat().st_size>150*1024*1024:raise ValueError('Image is larger than 150 MB.')
 info=GdkPixbuf.Pixbuf.get_file_info(str(path))
 if not info[0]:raise ValueError('This image format is unreadable by the installed image loaders.')
 w,h=info[1:]
 if w<=0 or h<=0 or w*h>100_000_000:raise ValueError('Image dimensions are not supported.')
 return w,h

def digest(path):
 hasher=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):hasher.update(chunk)
 return hasher.hexdigest()

def import_image(source,destination=None):
 source=Path(source).expanduser().resolve();image_info(source)
 directory=Path(destination) if destination is not None else IMPORTS
 directory.mkdir(parents=True,exist_ok=True)
 signature=digest(source)
 for existing in directory.iterdir():
  if existing.is_file() and existing.suffix.lower() in SUFFIXES and digest(existing)==signature:return existing
 fd,temporary=tempfile.mkstemp(prefix='.import-',suffix='.part',dir=directory)
 try:
  with os.fdopen(fd,'wb') as stream,source.open('rb') as incoming:shutil.copyfileobj(incoming,stream)
  number=1
  while True:
   suffix='' if number==1 else '-'+str(number)
   target=directory/(source.stem+suffix+source.suffix.lower())
   try:
    os.link(temporary,target) # Create without replacing an existing image.
    return target
   except FileExistsError:number+=1
 finally:
  if os.path.exists(temporary):os.unlink(temporary)

def collection_paths(folder,imports=None,bundled=None):
 paths={}
 for directory in (Path(bundled) if bundled is not None else ROOT/'wallpapers',Path(folder).expanduser(),Path(imports) if imports is not None else IMPORTS):
  try:
   for path in directory.iterdir():
    if path.is_file() and path.suffix.lower() in SUFFIXES:paths[str(path.resolve())]=path
  except OSError:continue
 return sorted(paths.values(),key=lambda p:p.name.lower())[:300]
