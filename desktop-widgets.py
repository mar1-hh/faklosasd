#!/usr/bin/python3
"""Neon Studio's independent desktop cards. No GNOME extensions required."""
import fcntl
import importlib.util
from pathlib import Path
import signal
import sys
import os
import gi
from preferences import load,update,ACCENTS,WIDGETS,effective_accent
from widget_layout import positions as layout_positions
from wallpaper_palette import tinted_surface
from widget_styles import calendar_css
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GLib
ROOT=Path(__file__).resolve().parent
(ROOT/'state').mkdir(exist_ok=True)
lock=open(ROOT/'state/widgets.lock','a+')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:
 print('Desktop widgets are already running.');sys.exit(0)
lock.seek(0);lock.truncate();lock.write(str(os.getpid()));lock.flush()
spec=importlib.util.spec_from_file_location('neon_dashboard',ROOT/'dashboard.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
dashboard=module.Dashboard()
screen=Gdk.Screen.get_default();display=Gdk.Display.get_default()
monitor=display.get_primary_monitor() or display.get_monitor(0)
geometry=monitor.get_geometry()
windows=[]; names=list(WIDGETS); sources={}; dragging=set(); last=None; layout_source=0; allocated={}
css=Gtk.CssProvider()
Gtk.StyleContext.add_provider_for_screen(screen,css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION+2)
def position():
 global layout_source
 layout_source=0
 if len(windows)!=len(names):return GLib.SOURCE_REMOVE
 sizes={name:(max(1,w.get_allocated_width()),max(1,w.get_allocated_height())) for name,w in zip(names,windows)}
 placements=layout_positions(geometry.width,geometry.height,sizes,load())
 for name,win in zip(names,windows):
  if name in dragging:continue
  x,y=placements[name];win.move(geometry.x+x,geometry.y+y)
 return GLib.SOURCE_REMOVE
def queue_position(*args):
 global layout_source
 if layout_source:GLib.source_remove(layout_source)
 layout_source=GLib.timeout_add(50,position)
 return False
def resized(win,allocation,name):
 size=(allocation.width,allocation.height)
 if allocated.get(name)!=size:
  allocated[name]=size;queue_position()
def save_position(name,win):
 sources.pop(name,None)
 if name in dragging and load()['arrange']:
  x,y=win.get_position();prefs=load();prefs['positions'][name]=[max(0,x-geometry.x),max(0,y-geometry.y)];update({'positions':prefs['positions']})
 dragging.discard(name)
 return GLib.SOURCE_REMOVE
def queue_save(name,win):
 if name in sources:GLib.source_remove(sources[name])
 sources[name]=GLib.timeout_add(300,save_position,name,win)
def configured(win,event,name):
 if name in dragging:queue_save(name,win)
 return False
def drag(win,event,name):
 if load()['arrange'] and event.button==1:
  dragging.add(name);queue_save(name,win)
  win.begin_move_drag(event.button,int(event.x_root),int(event.y_root),event.time)
  return True
 return False
for name,card in zip(names,dashboard.desktop_cards):
 card.get_parent().remove(card)
 win=Gtk.Window(type=Gtk.WindowType.TOPLEVEL,title='Neon Studio · '+WIDGETS[name])
 win.set_wmclass('neon-desktop-widgets','NeonStudioWidgets')
 win.get_style_context().add_class('desktop-widget')
 win.set_decorated(False);win.set_resizable(False)
 win.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
 win.set_skip_taskbar_hint(True);win.set_skip_pager_hint(True)
 win.set_keep_below(True);win.set_accept_focus(False);win.stick();win.set_app_paintable(True)
 if screen.get_rgba_visual():win.set_visual(screen.get_rgba_visual())
 win.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
 win.connect('button-press-event',drag,name)
 win.connect('configure-event',configured,name)
 win.connect('size-allocate',resized,name)
 win.connect('map-event',queue_position)
 win.add(card);windows.append(win)
def apply():
 global last
 prefs=load()
 if prefs==last:return GLib.SOURCE_CONTINUE
 previous=last;last=prefs
 scale=prefs['scale'];accent=effective_accent(prefs);surface=tinted_surface(accent)
 style=f'''
 .desktop-widget {{background:transparent;color:#f5fbff;font-family:Sans;font-size:{round(13*scale)}px;}}
 .desktop-widget .card {{background:{surface};padding:{round(14*scale)}px;border:1px solid alpha({accent},0.45);border-radius:{round(16*scale)}px;}}
 .desktop-widget label {{text-shadow:0 1px 2px rgba(0,0,0,0.65);}}
 .desktop-widget .heading {{font-size:{round(11*scale)}px;color:{accent};}}
 .desktop-widget .small {{font-size:{round(12*scale)}px;color:#d5e5eb;}}
 .desktop-widget .hours {{font-size:{round(27*scale)}px;color:{accent};}}
 .desktop-widget .clock {{font-size:{round(52*scale)}px;color:{accent};}}
 .desktop-widget button {{padding:{round(6*scale)}px;background:alpha({accent},0.14);border:1px solid alpha({accent},0.30);}}
 .desktop-widget button:hover {{background:alpha({accent},0.26);}}
 .desktop-widget calendar {{font-size:{round(13*scale)}px;}}
 .desktop-widget progressbar trough {{background:rgba(255,255,255,0.12);min-height:5px;border-radius:5px;}}
 .desktop-widget progressbar progress {{background:{accent};min-height:5px;border-radius:5px;}}
 .desktop-widget .break-mode .hours,.desktop-widget .break-mode .heading {{color:#83e5ae;}}
 .desktop-widget .break-mode progressbar progress {{background:#83e5ae;}}
 .desktop-widget .orbit-card .orbit-total {{font-size:{round(25*scale)}px;font-weight:700;color:#f5fbff;}}
 .desktop-widget .orbit-card .orbit-percent {{font-size:{round(16*scale)}px;color:{accent};font-weight:600;}}
 .desktop-widget .orbit-card .orbit-value {{font-size:{round(15*scale)}px;color:#f5fbff;}}
 .desktop-widget .orbit-card .orbit-live {{color:#83e5ae;}}
 .desktop-widget .orbit-card separator {{background:alpha({accent},.22);min-width:1px;}}
 .desktop-widget .orbit-card button {{padding:{round(3*scale)}px;min-height:16px;min-width:16px;}}
 .desktop-widget .focus-mode .hours {{color:{accent};}}
 .desktop-widget button {{border-radius:8px;}}

 '''
 restyle=previous is None or any(prefs[key]!=previous[key] for key in ('scale','accent','auto_accent','accent_color'))
 if restyle:css.load_from_data((style+calendar_css(accent)).encode())
 for name,win in zip(names,windows):
  width=430 if name=='launcher' else 310 if name=='clock' else 265
  if previous is None or scale!=previous['scale']:
   win.get_child().set_spacing(round(8*scale));win.get_child().set_size_request(round(width*scale),-1)
   win.resize(round(width*scale),1)
  win.set_opacity(prefs['opacity'])
  if prefs['visible'][name]:win.show_all()
  else:win.hide()
  win.set_keep_below(not prefs['arrange']);win.set_keep_above(prefs['arrange']);win.set_accept_focus(prefs['arrange'])
  win.set_type_hint(Gdk.WindowTypeHint.NORMAL if prefs['arrange'] else Gdk.WindowTypeHint.DESKTOP)
 if previous and prefs['username']!=previous['username']:dashboard.refresh()
 queue_position()
 return GLib.SOURCE_CONTINUE
def monitor_changed(*args):
 global geometry
 monitor=display.get_primary_monitor() or display.get_monitor(0)
 geometry=monitor.get_geometry();queue_position()
screen.connect('monitors-changed',monitor_changed)
apply()
dashboard.timers.append(GLib.timeout_add_seconds(1,apply))
def quit_widgets(*args):
 dashboard.alive=False
 dashboard.external_actions.close()
 for timer in dashboard.timers:GLib.source_remove(timer)
 for source in sources.values():GLib.source_remove(source)
 if layout_source:GLib.source_remove(layout_source)
 for win in windows:win.destroy()
 Gtk.main_quit();return GLib.SOURCE_REMOVE
GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGTERM,quit_widgets)
GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGINT,quit_widgets)
print('Neon Studio desktop cards started.',flush=True)
Gtk.main()
