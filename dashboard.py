#!/usr/bin/python3
"""Standalone dashboard: never modifies managed GNOME settings."""
import gi
import calendar
import json
import subprocess
import threading
import math
import shutil
from pomodoro import Pomodoro
from orbit_card import Orbit
from desktop_collection import entries as collection_entries
from logtime_orbit import values as orbit_values
from datetime import datetime
from pathlib import Path
from live_logtime import format_hours, live_hours
from launchers import available_apps
from external_actions import ExternalActions
from preferences import load as load_preferences, effective_accent
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GdkPixbuf,GLib,Gio
ROOT=Path(__file__).resolve().parent
class Dashboard(Gtk.Window):
 def __init__(self):
  super().__init__(title='Neon · Campus dashboard')
  self.set_default_size(1180,760)
  self.set_position(Gtk.WindowPosition.CENTER)
  self.alive=True; self.busy=False; self.timers=[]; self.log_snapshot=None; self.log_stale=False
  self.external_actions=ExternalActions()
  self.connect('destroy',self.close)
  css=Gtk.CssProvider()
  css.load_from_data(b'''
  window {background:#0c0913;color:#e8d4e3;}
  .card {background:rgba(29,23,35,0.94);border:1px solid #725269;border-radius:16px;padding:20px;}
  .heading {color:#bd91ae;font-size:11px;letter-spacing:2px;}
  .hours {color:#e2a9cf;font-size:36px;font-weight:300;}
  .clock {color:#e2a9cf;font-size:52px;font-weight:300;}
  .small {color:#c2aabe;font-size:12px;}
  button,combobox {background:#302334;color:#ead9e8;border-radius:10px;padding:6px;}
  progressbar progress {background:#d08bb8;min-height:7px;}
  progressbar trough {background:#423046;min-height:7px;}
  ''')
  Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
  overlay=Gtk.Overlay(); self.add(overlay)
  self.art=Gtk.Image(); self.art.set_hexpand(True); self.art.set_vexpand(True); overlay.add(self.art)
  layout=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=24)
  layout.set_border_width(24); overlay.add_overlay(layout)
  left=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18); left.set_size_request(265,-1); layout.pack_start(left,False,False,0)
  middle=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18); layout.pack_start(middle,True,True,0)
  right=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18); right.set_size_request(265,-1); layout.pack_start(right,False,False,0)
  self.orbit=Orbit(self,left,lambda _:self.refresh(),lambda _:subprocess.Popen(['/usr/bin/python3',str(ROOT/'control-center.py')]))
  log=self.orbit.card;self.period=self.orbit.period;self.status=self.orbit.status
  links=self.card(left,'QUICK LINKS')
  link_row=Gtk.Box(spacing=8,halign=Gtk.Align.CENTER);links.pack_start(link_row,False,False,0)
  self.button(link_row,'42 Intra ↗',lambda _:self.open_link('https://profile.intra.42.fr/'))
  self.button(link_row,'GitHub ↗',lambda _:self.open_link('https://github.com/'))
  self.link_status=self.label(links,'','small');self.link_status.set_no_show_all(True)
  clock=self.card(middle,''); self.clock=self.label(clock,'','clock'); self.date=self.label(clock,'','small')
  spacer=Gtk.Box(); middle.pack_start(spacer,True,True,0)
  notice=self.card(middle,'NOTES')
  self.notes_text=self.label(notice,load_preferences()['notes'],'small')
  self.notes_text.set_lines(6);self.notes_text.set_ellipsize(3)
  launcher=self.card(middle,'YOUR APPS')
  app_row=Gtk.Box(spacing=8,halign=Gtk.Align.CENTER);launcher.pack_start(app_row,False,False,0)
  for title,app in available_apps():
   self.button(app_row,title,lambda _,selected=app:self.open_app(selected))
  stats=self.card(right,'SYSTEM'); self.stats=self.label(stats,'Memory','small')
  self.memory_bar=Gtk.ProgressBar();stats.pack_start(self.memory_bar,False,False,0)
  self.system_load=self.label(stats,'Load · —','small')
  cal=self.card(right,'CALENDAR'); calendar_view=Gtk.Calendar(halign=Gtk.Align.CENTER);self.calendar_view=calendar_view;cal.pack_start(calendar_view,False,False,0)
  calendar_view.connect('month-changed',lambda *_:self.mark_today())
  self.calendar_day=None
  pomo=self.card(left,'POMODORO');self.pomodoro_card=pomo
  self.pomodoro=Pomodoro(load_preferences())
  modes=Gtk.Box(spacing=4,halign=Gtk.Align.CENTER);pomo.pack_start(modes,False,False,0)
  for title,mode in [('Focus','focus'),('Short','short'),('Long','long')]:
   self.button(modes,title,lambda _,chosen=mode:self.pomodoro_action(lambda:self.pomodoro.mode(chosen)))
  self.pomo_mode=self.label(pomo,'Focus','small')
  self.countdown=self.label(pomo,'25:00','hours')
  self.pomo_bar=Gtk.ProgressBar();pomo.pack_start(self.pomo_bar,False,False,0)
  self.pomo_rounds=self.label(pomo,'○ ○ ○ ○','small')
  controls=Gtk.Box(spacing=5,halign=Gtk.Align.CENTER);pomo.pack_start(controls,False,False,0)
  self.pomo_start=self.button(controls,'Start',lambda _:self.pomodoro_action(self.pomodoro.toggle))
  self.button(controls,'Reset',lambda _:self.pomodoro_action(self.pomodoro.reset))
  self.button(controls,'Skip',lambda _:self.pomodoro_action(self.pomodoro.skip))
  papers=self.card(right,'4K WALLPAPER COLLECTION')
  self.choice=Gtk.ComboBoxText(); self.paths=sorted((ROOT/'wallpapers').glob('*.png'))
  for path in self.paths:self.choice.append_text(path.stem[3:].replace('-',' ').title())
  papers.pack_start(self.choice,False,False,0)
  self.label(papers,'Preview · desktop background is managed','small')
  self.choice.connect('changed',self.select_wallpaper)
  self.art.connect('size-allocate',self.resize_art)
  self.choice.set_active(0)
  collection=self.card(right,'DESKTOP COLLECTION')
  self.collection_list=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);collection.pack_start(self.collection_list,False,False,0)
  self.collection_status=self.label(collection,'Loading…','small')
  actions=Gtk.Box(spacing=6,halign=Gtk.Align.CENTER);collection.pack_start(actions,False,False,0)
  self.button(actions,'Previous',lambda _:self.collection_page_change(-1))
  self.button(actions,'Next',lambda _:self.collection_page_change(1))
  self.button(actions,'Files ↗',lambda _:self.open_link(Path(load_preferences()['collection_folder']).expanduser().absolute().as_uri()))
  self.collection_paths=[];self.collection_page=0;self.collection_busy=False;self.collection_folder=None
  self.desktop_cards = [log,links,clock,stats,cal,notice,launcher,pomo,collection]
  self.refresh_collection();self.timers.append(GLib.timeout_add_seconds(5,self.refresh_collection))
  self.tick(); self.refresh()
  self.timers.append(GLib.timeout_add_seconds(1,self.tick))
  self.timers.append(GLib.timeout_add_seconds(300,self.refresh))
 def refresh_collection(self):
  prefs=load_preferences()
  if self.collection_busy or not prefs['visible']['collection']:return GLib.SOURCE_CONTINUE
  self.collection_busy=True;folder=prefs['collection_folder']
  def worker():
   try:paths=collection_entries(folder);error=None
   except OSError as exc:paths=[];error=str(exc)
   GLib.idle_add(self.collection_ready,folder,paths,error)
  threading.Thread(target=worker,daemon=True).start()
  return GLib.SOURCE_CONTINUE
 def collection_ready(self,folder,paths,error):
  self.collection_busy=False
  if not self.alive:return GLib.SOURCE_REMOVE
  if folder!=load_preferences()['collection_folder']:return GLib.SOURCE_REMOVE
  if paths!=self.collection_paths or folder!=self.collection_folder or error:
   if folder!=self.collection_folder:self.collection_page=0
   self.collection_paths=paths;self.collection_folder=folder;self.collection_page_change(0)
  if error:self.collection_status.set_text('Folder unavailable');self.collection_status.set_tooltip_text(error)
  return GLib.SOURCE_REMOVE
 def collection_page_change(self,step):
  pages=max(1,(len(self.collection_paths)+5)//6)
  self.collection_page=max(0,min(pages-1,self.collection_page+step))
  for child in self.collection_list.get_children():self.collection_list.remove(child)
  for path in self.collection_paths[self.collection_page*6:self.collection_page*6+6]:
   item=self.button(self.collection_list,path.name,lambda _,chosen=path:self.open_link(chosen.absolute().as_uri()))
   item.get_child().set_ellipsize(3);item.get_child().set_max_width_chars(25);item.set_tooltip_text(str(path))
  self.collection_list.show_all()
  self.collection_status.set_text(f'{len(self.collection_paths)} items · {self.collection_page+1}/{pages}' if self.collection_paths else 'Folder is empty')
 def mark_today(self):
  now=datetime.now();year,month,day=self.calendar_view.get_date()
  self.calendar_view.clear_marks()
  if (year,month+1)==(now.year,now.month):self.calendar_view.mark_day(now.day)
 def pomodoro_action(self,action):
  self.pomodoro.prefs=load_preferences();action();self.render_pomodoro()
 def render_pomodoro(self):
  self.pomodoro.prefs=load_preferences();ended=self.pomodoro.tick()
  s=self.pomodoro.state;remaining=math.ceil(self.pomodoro.remaining())
  self.countdown.set_text(f'{remaining//60:02d}:{remaining%60:02d}')
  self.pomo_mode.set_text({'focus':'Focus','short':'Short Break','long':'Long Break · four focus sessions complete' if s['completed']==4 else 'Long Break'}[s['mode']])
  self.pomo_start.set_label('Pause' if s['running'] else 'Start')
  self.pomo_bar.set_fraction(max(0,min(1,1-self.pomodoro.remaining()/s['duration'])))
  self.pomo_rounds.set_text(' '.join('●' if i<s['completed'] else '○' for i in range(4)))
  context=self.pomodoro_card.get_style_context()
  context.remove_class('focus-mode' if s['mode']!='focus' else 'break-mode')
  context.add_class('focus-mode' if s['mode']=='focus' else 'break-mode')
  if ended:
   prefs=self.pomodoro.prefs
   def alert():
    try:
     if prefs['pomodoro_notifications'] and shutil.which('notify-send'):
      subprocess.run(['notify-send','--app-name=Neon Studio','Pomodoro session complete',{'focus':'Focus complete. Time for a break.','short':'Break complete. Ready to focus?','long':'Long break complete. Ready for a new cycle?'}[ended]],timeout=5,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
     sound=Path('/usr/share/sounds/freedesktop/stereo/complete.oga')
     if prefs['pomodoro_sound'] and sound.exists() and shutil.which('paplay'):
      subprocess.run(['paplay',str(sound)],timeout=5,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except (OSError,subprocess.SubprocessError):pass
   threading.Thread(target=alert,daemon=True).start()
 def opened(self,error):
  if not self.alive:return
  if error:
   self.link_status.set_text('Could not open · try again')
   self.link_status.set_tooltip_text(error)
   print('External launch failed: '+error,flush=True)
  else:self.link_status.set_text('')
  self.link_status.set_visible(bool(error))
 def open_link(self,uri):
  self.link_status.set_text('Opening browser…');self.link_status.show()
  self.external_actions.open_uri(uri,self.opened)
 def open_app(self,app):
  self.external_actions.open_app(app,self.opened)
 def card(self,parent,title):
  box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12); box.get_style_context().add_class('card')
  parent.pack_start(box,False,False,0)
  if title:self.label(box,title,'heading')
  return box
 def label(self,parent,text,style):
  label=Gtk.Label(label=text,xalign=0.5,justify=Gtk.Justification.CENTER); label.get_style_context().add_class(style)
  label.set_line_wrap(True); label.set_max_width_chars(34)
  parent.pack_start(label,False,False,0); return label
 def button(self,parent,text,callback):
  b=Gtk.Button(label=text);b.connect('clicked',callback);parent.pack_start(b,False,False,0);return b
 def icon_button(self,parent,icon,title,callback):
  b=Gtk.Button.new_from_icon_name(icon,Gtk.IconSize.BUTTON);b.set_tooltip_text(title);b.get_accessible().set_name(title);b.connect('clicked',callback);parent.pack_start(b,False,False,0)
 def select_wallpaper(self,*_):
  self.pixbuf=GdkPixbuf.Pixbuf.new_from_file(str(self.paths[self.choice.get_active()]))
  self.render_art()
 def resize_art(self,*_):self.render_art()
 def render_art(self):
  if not hasattr(self,'pixbuf'):return
  w=max(1,self.get_allocated_width()); h=max(1,self.get_allocated_height())
  # Fit without changing the image widget's natural size or creating resize loops.
  scaled=self.pixbuf.scale_simple(w,h,GdkPixbuf.InterpType.BILINEAR)
  self.art.set_from_pixbuf(scaled)
  self.art.set_size_request(1,1)
 def tick(self):
  self.render_logtime();self.render_pomodoro()
  now=datetime.now();prefs=load_preferences();self.notes_text.set_text(prefs['notes']);self.clock.set_text(now.strftime('%H:%M:%S' if prefs['clock_seconds'] else '%H:%M'));self.date.set_text(now.strftime('%A, %d %B'))
  if self.calendar_day!=now.date():self.calendar_day=now.date();self.mark_today()
  try:
   info={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
   used=100*(1-info['MemAvailable']/info['MemTotal'])
   load=Path('/proc/loadavg').read_text().split()[0]
   self.stats.set_text(f'Memory · {used:.0f}%');self.memory_bar.set_fraction(max(0,min(1,used/100)))
   self.system_load.set_text(f'Load average · {load}  /  1 min')
  except (OSError,ValueError,KeyError):self.stats.set_text('System readings unavailable')
  return GLib.SOURCE_CONTINUE
 def refresh(self):
  if self.busy:return GLib.SOURCE_CONTINUE
  self.busy=True;self.status.set_text('Refreshing…')
  threading.Thread(target=self.fetch,daemon=True).start()
  return GLib.SOURCE_CONTINUE
 def fetch(self):
  try:
   p=subprocess.run([str(ROOT/'python'),str(ROOT/'logtime-widget.py')],capture_output=True,text=True,timeout=40)
   if p.returncode:raise ValueError(p.stderr)
   data=json.loads(p.stdout);GLib.idle_add(self.result,data)
  except (OSError,ValueError,subprocess.TimeoutExpired):GLib.idle_add(self.result,None)
 def result(self,data):
  self.busy=False
  if not self.alive:return GLib.SOURCE_REMOVE
  if data:
   self.log_snapshot=data; self.log_stale=False
   self.period.set_text(data['period']['start']+' → '+data['period']['end'])
  else:self.log_stale=True
  self.render_logtime()
  if not data and not self.log_snapshot:self.status.set_text('Logtime unavailable · try Refresh')
  return GLib.SOURCE_REMOVE
 def render_logtime(self):
  prefs=load_preferences()
  self.orbit.resize(prefs['scale']);self.orbit.set_accent(effective_accent(prefs))
  if not self.log_snapshot:return
  data=self.log_snapshot
  self.orbit.render(orbit_values(data,prefs.get('target_hours')),prefs['scale'])
  if self.busy:self.status.set_text('Refreshing API · session continues')
  elif self.log_stale:self.status.set_text('API offline · cached total + live session')
  elif not data.get('session_detected'):self.status.set_text('Session not detected · API total only')
  elif data.get('session_source')=='desktop process estimate':self.status.set_text('Live · session estimated from desktop')
  else:self.status.set_text('Live · includes active session')
 def close(self,*_):
  self.alive=False
  self.external_actions.close()
  for timer in self.timers:GLib.source_remove(timer)
  Gtk.main_quit()
if __name__=='__main__':
 window=Dashboard();window.show_all();Gtk.main()
