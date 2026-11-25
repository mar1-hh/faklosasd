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
WIDGETS={'logtime':'Logtime','links':'Quick links','clock':'Clock','system':'System monitor','calendar':'Calendar','notes':'Notes','launcher':'App launcher','pomodoro':'Pomodoro','collection':'Desktop collection','media':'Now playing','search':'File search'}
ACCENTS={'Rose':'#dfa1c6','Violet':'#b9a0fa','Teal':'#73d7c2','Amber':'#ebbd7e','Blue':'#8ebff0'}
DEFAULTS={'keep_awake_minutes':0,'widget_borders':True,'collection_folder':str(Path.home()/'Desktop'),'file_search_root':str(Path.home()/'Documents'),'pomodoro_focus':25,'pomodoro_short':5,'pomodoro_long':15,'pomodoro_notifications':True,'pomodoro_sound':False,'pomodoro_auto_start':False,'scale':1.3,'opacity':0.92,'margin':24,'target_hours':120,'accent':'Rose','auto_accent':True,'accent_color':'#dfa1c6','active_wallpaper':'','clock_seconds':False,'arrange':False,'keep_awake_enabled':True,'keep_awake_method':'mouse','terminal_match':False,'terminal_transparency':25,'studio_transparency':8,'notes':'Make something meaningful.\nOne session at a time.','username':'','wallpaper_folder':str(ROOT/'wallpapers'),'visible':{name:name not in ('collection','media','search') for name in WIDGETS},'positions':{},'widget_scales':{},'grid_snap':True,'grid_size':24,'media_compact':False,'media_show_progress':True,'media_show_album':True,'launcher_icon_size':36,'launcher_orientation':'horizontal','launcher_favorites':[],'rotate_hours':0,'theme_mode':'dark'}
def normalize(data):
 if not isinstance(data,dict):data={}
 result=deepcopy(DEFAULTS)
 for key,lo,hi in [('keep_awake_minutes',0,1440),('pomodoro_focus',1,180),('pomodoro_short',1,60),('pomodoro_long',1,120),('scale',0.8,1.8),('opacity',0.3,1),('margin',0,200),('target_hours',1,1000),('terminal_transparency',0,100),('studio_transparency',0,70),('grid_size',8,64),('launcher_icon_size',20,64),('rotate_hours',0,168)]:
  try:
   value=float(data.get(key,result[key]))
   if math.isfinite(value):result[key]=max(lo,min(hi,value))
  except (TypeError,ValueError):pass
 result['margin']=int(result['margin'])
 result['grid_size']=int(result['grid_size'])
 result['launcher_icon_size']=int(result['launcher_icon_size'])
 result['terminal_transparency']=round(result['terminal_transparency'])
 for key in ('widget_borders','pomodoro_notifications','pomodoro_sound','pomodoro_auto_start','clock_seconds','arrange','auto_accent','keep_awake_enabled','terminal_match','grid_snap','media_compact','media_show_progress','media_show_album'):result[key]=data.get(key,DEFAULTS[key]) is True
 for key,limit in [('collection_folder',4096),('file_search_root',4096),('notes',2000),('username',64),('wallpaper_folder',4096),('active_wallpaper',4096)]:
  if isinstance(data.get(key),str):result[key]=data[key][:limit]
 if data.get('keep_awake_method') in ('mouse','inhibit','shift'):result['keep_awake_method']=data['keep_awake_method']
 if data.get('launcher_orientation') in ('horizontal','vertical'):result['launcher_orientation']=data['launcher_orientation']
 if data.get('theme_mode') in ('dark','light','auto'):result['theme_mode']=data['theme_mode']
 if isinstance(data.get('launcher_favorites'),list):result['launcher_favorites']=[str(f)[:128] for f in data['launcher_favorites'] if isinstance(f,str)][:32]
 if not re.fullmatch(r'[a-zA-Z0-9_-]*',result['username']):result['username']=''
 if data.get('accent') in ACCENTS:result['accent']=data['accent']
 if isinstance(data.get('accent_color'),str) and re.fullmatch(r'#[0-9a-fA-F]{6}',data['accent_color']):result['accent_color']=data['accent_color'].lower()
 visible=data.get('visible',{})
 if isinstance(visible,dict):result['visible']={key:visible.get(key,DEFAULTS['visible'].get(key,True)) is not False for key in WIDGETS}
 positions=data.get('positions',{})
 if isinstance(positions,dict):
  for key,value in positions.items():
   if key in WIDGETS and isinstance(value,list) and len(value)==2:
    try:
     pair=[int(v) for v in value]
     result['positions'][key]=[max(0,min(20000,v)) for v in pair]
    except (ValueError,TypeError,OverflowError):pass
 widget_scales=data.get('widget_scales',{})
 if isinstance(widget_scales,dict):
  for key,value in widget_scales.items():
   if key in WIDGETS:
    try:
     sc=float(value)
     if math.isfinite(sc):result['widget_scales'][key]=max(0.5,min(2.5,sc))
    except (ValueError,TypeError):pass
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
