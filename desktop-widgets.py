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
from widget_styles import calendar_css, design_system_css
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
  x,y=win.get_position();prefs=load()
  rx,ry=x-geometry.x,y-geometry.y
  if prefs.get('grid_snap'):
   gs=prefs.get('grid_size',24)
   rx,ry=round(rx/gs)*gs,round(ry/gs)*gs
  prefs['positions'][name]=[max(0,rx),max(0,ry)];update({'positions':prefs['positions']})
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
 .desktop-widget {{background:transparent;color:#f5fbff;font-family:Sans;font-weight:300;font-size:{round(13*scale)}px;}}
 .desktop-widget .card {{background:{surface};padding:{round(14*scale)}px;border:1px solid alpha({accent},0.30);border-radius:{round(16*scale)}px;}}
 .desktop-widget label {{text-shadow:0 1px 2px rgba(0,0,0,0.65);}}
 .desktop-widget .heading {{font-size:{round(11*scale)}px;color:{accent};}}
 .desktop-widget .small {{font-size:{round(12*scale)}px;color:#d5e5eb;}}
 .desktop-widget .hours {{font-weight:200;font-size:{round(38*scale)}px;color:{accent};}}
 .desktop-widget .clock {{font-weight:200;font-size:{round(52*scale)}px;color:{accent};}}
 .desktop-widget button {{padding:{round(6*scale)}px;background:alpha({accent},0.14);border:1px solid alpha({accent},0.30);}}
 .desktop-widget button:hover {{background:alpha({accent},0.26);}}
 .desktop-widget calendar {{font-size:{round(13*scale)}px;}}
 .desktop-widget progressbar trough {{background:rgba(255,255,255,0.12);min-height:5px;border-radius:5px;}}
 .desktop-widget progressbar progress {{background:{accent};min-height:5px;border-radius:5px;}}
 .desktop-widget .break-mode .hours,.desktop-widget .break-mode .heading {{color:#83e5ae;}}
 .desktop-widget .break-mode progressbar progress {{background:#83e5ae;}}
 .desktop-widget .orbit-card .orbit-total {{font-size:{round(38*scale)}px;font-weight:200;color:#f5edf3;}}
 .desktop-widget .orbit-value {{font-size:{round(15*scale)}px;font-weight:300;color:#e7dfe6;}}
 .desktop-widget .round-action {{border-radius:999px;padding:{round(7*scale)}px;min-height:{round(18*scale)}px;min-width:{round(18*scale)}px;border-color:transparent;}}
 .desktop-widget button.primary-action {{background:alpha({accent},0.27);font-weight:600;}}
 .desktop-widget button.current-mode {{color:{accent};border-color:{accent};background:alpha({accent},0.22);}}
 .desktop-widget .focus-mode .hours {{color:{accent};}}
 .desktop-widget button {{border-radius:8px;}}
 .desktop-widget .launcher-search-entry {{background:alpha({accent},0.08);border:1px solid alpha({accent},0.24);border-radius:10px;color:#f5fbff;font-size:{round(12*scale)}px;padding:4px 8px;}}
 .desktop-widget .launcher-app-btn {{border-radius:12px;padding:{round(6*scale)}px;background:transparent;border:1px solid transparent;}}
 .desktop-widget .launcher-app-btn:hover {{background:alpha({accent},0.20);border-color:alpha({accent},0.35);}}
 .desktop-widget .launcher-app-label {{font-size:{round(10*scale)}px;color:#e7dfe6;margin-top:2px;}}
 .desktop-widget .file-search-row {{background:alpha({accent},0.04);border-radius:8px;padding:2px;}}
 .desktop-widget .file-search-row:hover {{background:alpha({accent},0.15);}}
 '''
 restyle=previous is None or any(prefs[key]!=previous[key] for key in ('scale','accent','auto_accent','accent_color','widget_borders'))
 if not prefs['widget_borders']:style+='\n.desktop-widget .card {border-color:transparent;}'
 if restyle:css.load_from_data((style+calendar_css(accent)+design_system_css(scale,accent)).encode())
 for name,win in zip(names,windows):
  width=310 if name=='clock' else 440 if name=='launcher' else 290 if name in ('media','search') else 265
  w_scale=scale*prefs.get('widget_scales',{}).get(name,1.0)
  if previous is None or scale!=previous['scale'] or prefs.get('widget_scales')!=(previous.get('widget_scales') if previous else {}):
   win.get_child().set_spacing(round(8*w_scale));win.get_child().set_size_request(round(width*w_scale),-1)
   win.resize(round(width*w_scale),1)
  # Keep media artwork and text opaque; its surface applies the saved opacity.
  if name=='media':win.set_opacity(1.0)
  else:win.set_opacity(prefs['opacity'])
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
