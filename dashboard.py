#!/usr/bin/python3
"""Standalone dashboard: never modifies managed GNOME settings."""
import gi
import calendar
import json
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from live_logtime import format_hours, live_hours
from launchers import available_apps
from external_actions import ExternalActions
from preferences import load as load_preferences
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
  log=self.card(left,'42 / LOGTIME')
  self.hours=self.label(log,'— h','hours'); self.bar=Gtk.ProgressBar(); log.pack_start(self.bar,False,False,0)
  self.period=self.label(log,'28th → 27th','small'); self.detail=self.label(log,'Target · 120 h','small')
  self.status=self.label(log,'Loading your logtime…','small')
  self.button(log,'Refresh',lambda _:self.refresh())
  self.button(log,'Settings',lambda _:subprocess.Popen(['/usr/bin/python3',str(ROOT/'control-center.py')]))
  links=self.card(left,'QUICK LINKS')
  self.button(links,'42 Intra ↗',lambda _:self.open_link('https://profile.intra.42.fr/'))
  self.button(links,'GitHub ↗',lambda _:self.open_link('https://github.com/'))
  self.link_status=self.label(links,'','small')
  clock=self.card(middle,''); self.clock=self.label(clock,'','clock'); self.date=self.label(clock,'','small')
  spacer=Gtk.Box(); middle.pack_start(spacer,True,True,0)
  notice=self.card(middle,'NOTES')
  self.notes_text=self.label(notice,load_preferences()['notes'],'small')
  self.notes_text.set_lines(6);self.notes_text.set_ellipsize(3)
  launcher=self.card(middle,'YOUR APPS')
  app_row=Gtk.Box(spacing=8);launcher.pack_start(app_row,False,False,0)
  for title,app in available_apps():
   self.button(app_row,title,lambda _,selected=app:self.open_app(selected))
  stats=self.card(right,'SYSTEM'); self.stats=self.label(stats,'','small')
  cal=self.card(right,'CALENDAR'); cal.pack_start(Gtk.Calendar(),False,False,0)
  papers=self.card(right,'4K WALLPAPER COLLECTION')
  self.choice=Gtk.ComboBoxText(); self.paths=sorted((ROOT/'wallpapers').glob('*.png'))
  for path in self.paths:self.choice.append_text(path.stem[3:].replace('-',' ').title())
  papers.pack_start(self.choice,False,False,0)
  self.label(papers,'Preview · desktop background is managed','small')
  self.choice.connect('changed',self.select_wallpaper)
  self.art.connect('size-allocate',self.resize_art)
  self.choice.set_active(0)
  self.desktop_cards = [log,links,clock,stats,cal,notice,launcher]
  self.tick(); self.refresh()
  self.timers.append(GLib.timeout_add_seconds(1,self.tick))
  self.timers.append(GLib.timeout_add_seconds(300,self.refresh))
 def opened(self,error):
  if not self.alive:return
  if error:
   self.link_status.set_text('Could not open · try again')
   self.link_status.set_tooltip_text(error)
   print('External launch failed: '+error,flush=True)
  else:self.link_status.set_text('')
 def open_link(self,uri):
  self.link_status.set_text('Opening browser…')
  self.external_actions.open_uri(uri,self.opened)
 def open_app(self,app):
  self.external_actions.open_app(app,self.opened)
 def card(self,parent,title):
  box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12); box.get_style_context().add_class('card')
  parent.pack_start(box,False,False,0)
  if title:self.label(box,title,'heading')
  return box
 def label(self,parent,text,style):
  label=Gtk.Label(label=text,xalign=0); label.get_style_context().add_class(style)
  label.set_line_wrap(True); label.set_max_width_chars(34)
  parent.pack_start(label,False,False,0); return label
 def button(self,parent,text,callback):
  b=Gtk.Button(label=text);b.connect('clicked',callback);parent.pack_start(b,False,False,0)
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
  self.render_logtime()
  now=datetime.now();prefs=load_preferences();self.notes_text.set_text(prefs['notes']);self.clock.set_text(now.strftime('%H:%M:%S' if prefs['clock_seconds'] else '%H:%M'));self.date.set_text(now.strftime('%A, %d %B'))
  try:
   info={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
   used=100*(1-info['MemAvailable']/info['MemTotal'])
   load=Path('/proc/loadavg').read_text().split()[0]
   self.stats.set_text(f'Memory     {used:.0f}%\n\nLoad · 1 minute     {load}')
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
  if not self.log_snapshot:return
  data=self.log_snapshot; h=live_hours(data)
  h['target']=load_preferences()['target_hours']
  self.hours.set_text(format_hours(h['projected']))
  self.hours.set_tooltip_text('Projected total · hours:minutes:seconds')
  self.bar.set_fraction(max(0,min(1,h['projected']/h['target'])) if h['target']>0 else 1)
  self.detail.set_text(f"Target · {h['target']:g} h\nToday · {format_hours(h['today']+h['session'])}\nSession · {format_hours(h['session'])}")
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
