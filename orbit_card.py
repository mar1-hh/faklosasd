"""GTK 3 Logtime view: Cairo ring with accessible native text labels."""
import math
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk
from logtime_orbit import ring_geometry
from preferences import load, effective_accent

class Orbit:
 def __init__(self,host,parent,refresh,settings):
  self.fraction=0;self.scale=None;self.accent=effective_accent(load())
  self.card=host.card(parent,'');self.card.get_style_context().add_class('orbit-card')
  header=Gtk.Box(spacing=6);self.card.pack_start(header,False,False,0)
  title=host.label(header,'42 / LOGTIME','heading');title.set_xalign(0);title.set_hexpand(True)
  host.icon_button(header,'view-refresh-symbolic','Refresh logtime',refresh)
  host.icon_button(header,'emblem-system-symbolic','Open settings',settings)
  self.live=host.label(self.card,'○ No active session','small')
  self.period=host.label(self.card,'Loading date range…','small')
  overlay=Gtk.Overlay();self.card.pack_start(overlay,False,False,0)
  self.ring=Gtk.DrawingArea();self.ring.set_halign(Gtk.Align.CENTER);self.ring.connect('draw',self.draw);overlay.add(self.ring)
  center=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5,halign=Gtk.Align.CENTER,valign=Gtk.Align.CENTER)
  overlay.add_overlay(center)
  self.percent=host.label(center,'—','orbit-percent')
  self.total=host.label(center,'—h —m','orbit-total')
  self.target=host.label(center,'Target —','small')
  self.remaining=host.label(self.card,'Loading your logtime…','small')
  footer=Gtk.Box(spacing=12,homogeneous=False);self.card.pack_start(footer,False,False,0)
  for name in ('Today','Session'):
   if name=='Session':footer.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL),False,False,0)
   column=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,hexpand=True);footer.pack_start(column,True,True,0)
   host.label(column,name,'small')
   setattr(self,name.lower(),host.label(column,'—','orbit-value'))
  self.status=host.label(self.card,'','small')
  self.resize(1)
 def resize(self,scale):
  if scale==self.scale:return
  self.scale=scale;size=round(190*scale);self.ring.set_size_request(size,size)
 def set_accent(self,accent):
  if accent!=self.accent:
   self.accent=accent;self.ring.queue_draw()
 def draw(self,widget,cr):
  x,y,radius,stroke=ring_geometry(widget.get_allocated_width(),widget.get_allocated_height())
  if radius<=0:return False
  rgb=tuple(int(self.accent[i:i+2],16)/255 for i in (1,3,5))
  cr.set_line_width(stroke);cr.set_source_rgba(*rgb,.18)
  cr.arc(x,y,radius,0,2*math.pi);cr.stroke()
  if self.fraction>0:
   cr.set_source_rgba(*rgb,1);cr.set_line_cap(1)
   cr.arc(x,y,radius,-math.pi/2,-math.pi/2+2*math.pi*self.fraction);cr.stroke()
  return False
 def render(self,values,scale):
  self.resize(scale)
  for name in ('total','target','percent','remaining','today','session'):getattr(self,name).set_text(values[name])
  self.live.set_text('● Live' if values['active'] else '○ No active session')
  context=self.live.get_style_context()
  if values['active']:context.add_class('orbit-live')
  else:context.remove_class('orbit-live')
  if self.fraction!=values['fraction']:
   self.fraction=values['fraction'];self.ring.queue_draw()
  self.ring.get_accessible().set_name('Logtime completion '+values['percent'])
