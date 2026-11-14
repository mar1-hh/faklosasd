"""Validated, atomically saved preferences for Neon Studio and desktop cards."""
import json
import math
import os
import re
import tempfile
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILE=ROOT/'state/preferences.json'
WIDGETS={'logtime':'Logtime','links':'Quick links','clock':'Clock','system':'System monitor','calendar':'Calendar','notes':'Notes','launcher':'App launcher'}
ACCENTS={'Rose':'#dfa1c6','Violet':'#b9a0fa','Teal':'#73d7c2','Amber':'#ebbd7e','Blue':'#8ebff0'}
DEFAULTS={'scale':1.3,'opacity':0.92,'margin':24,'target_hours':120,'accent':'Rose','auto_accent':True,'accent_color':'#dfa1c6','active_wallpaper':'','clock_seconds':False,'arrange':False,'keep_awake_enabled':True,'notes':'Make something meaningful.\nOne session at a time.','username':'','wallpaper_folder':str(ROOT/'wallpapers'),'visible':{name:True for name in WIDGETS},'positions':{}}
def normalize(data):
 if not isinstance(data,dict):data={}
 result=deepcopy(DEFAULTS)
 for key,lo,hi in [('scale',0.8,1.8),('opacity',0.3,1),('margin',0,200),('target_hours',1,1000)]:
  try:
   value=float(data.get(key,result[key]))
   if math.isfinite(value):result[key]=max(lo,min(hi,value))
  except (TypeError,ValueError):pass
 result['margin']=int(result['margin'])
 for key in ('clock_seconds','arrange','auto_accent','keep_awake_enabled'):result[key]=data.get(key,DEFAULTS[key]) is True
 for key,limit in [('notes',2000),('username',64),('wallpaper_folder',4096),('active_wallpaper',4096)]:
  if isinstance(data.get(key),str):result[key]=data[key][:limit]
 if not re.fullmatch(r'[a-zA-Z0-9_-]*',result['username']):result['username']=''
 if data.get('accent') in ACCENTS:result['accent']=data['accent']
 if isinstance(data.get('accent_color'),str) and re.fullmatch(r'#[0-9a-fA-F]{6}',data['accent_color']):result['accent_color']=data['accent_color'].lower()
 visible=data.get('visible',{})
 if isinstance(visible,dict):result['visible']={key:visible.get(key,True) is not False for key in WIDGETS}
 positions=data.get('positions',{})
 if isinstance(positions,dict):
  for key,value in positions.items():
   if key in WIDGETS and isinstance(value,list) and len(value)==2:
    try:
     pair=[int(v) for v in value]
     result['positions'][key]=[max(0,min(20000,v)) for v in pair]
    except (ValueError,TypeError,OverflowError):pass
 return result
def load():
 try:return normalize(json.loads(FILE.read_text()))
 except (OSError,ValueError):return normalize({})
def save(data):
 FILE.parent.mkdir(exist_ok=True)
 fd,name=tempfile.mkstemp(prefix='.preferences-',suffix='.tmp',dir=FILE.parent)
 try:
  with os.fdopen(fd,'w') as stream:json.dump(normalize(data),stream,indent=2)
  os.replace(name,FILE)
 finally:
  if os.path.exists(name):os.unlink(name)
def update(changes):
 data=load();data.update(changes);save(data)

def effective_accent(prefs):
 return prefs['accent_color'] if prefs['auto_accent'] else ACCENTS[prefs['accent']]
