"""Compact, text-free GTK 3 Logtime card with a native open progress arc."""
import math
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk
from logtime_orbit import ring_geometry
from preferences import load, effective_accent

class Orbit:
 def __init__(self,host,parent,refresh,settings):
  self.fraction=0;self.scale=None;self.accent=effective_accent(load());self.period='';self.status='Loading logtime…'
  self.card=host.card(parent,'');self.card.get_style_context().add_class('orbit-card')
  self.card.get_accessible().set_name('42 Logtime')
  overlay=Gtk.Overlay();self.card.pack_start(overlay,False,False,0)
  self.ring=Gtk.DrawingArea();self.ring.set_halign(Gtk.Align.CENTER);self.ring.connect('draw',self.draw);overlay.add(self.ring)
  self.total=Gtk.Label(label='—:—',halign=Gtk.Align.CENTER,valign=Gtk.Align.CENTER)
  self.total.get_style_context().add_class('orbit-total');overlay.add_overlay(self.total)
  footer=Gtk.Box(spacing=14,halign=Gtk.Align.CENTER);self.card.pack_start(footer,False,False,0)
  self.icons=[]
  for name,description in (('today','Today’s logtime'),('session','Current session duration')):
   group=Gtk.Box(spacing=6,halign=Gtk.Align.CENTER);footer.pack_start(group,False,False,0)
   icon=Gtk.DrawingArea();icon.set_tooltip_text(description);icon.get_accessible().set_name(description)
   icon.connect('draw',self.draw_icon,name);group.pack_start(icon,False,False,0);self.icons.append(icon)
   value=Gtk.Label(label='—:—' if name=='today' else '—:—:—')
   value.get_style_context().add_class('orbit-value');value.set_tooltip_text(description);group.pack_start(value,False,False,0)
   setattr(self,name,value)
  actions=Gtk.Box(spacing=10,halign=Gtk.Align.CENTER);self.card.pack_start(actions,False,False,0)
  self.refresh=Gtk.Button.new_from_icon_name('view-refresh-symbolic',Gtk.IconSize.BUTTON)
  self.refresh.set_halign(Gtk.Align.CENTER);self.refresh.get_style_context().add_class('round-action')
  self.refresh.set_tooltip_text('Refresh logtime');self.refresh.get_accessible().set_name('Refresh logtime')
  self.refresh.connect('clicked',refresh);actions.pack_start(self.refresh,False,False,0)
  self.settings=Gtk.Button.new_from_icon_name('emblem-system-symbolic',Gtk.IconSize.BUTTON)
  self.settings.get_style_context().add_class('round-action')
  self.settings.set_tooltip_text('Open Neon Studio settings');self.settings.get_accessible().set_name('Open Neon Studio settings')
  self.settings.connect('clicked',settings);actions.pack_start(self.settings,False,False,0)
  self.resize(1)
 def set_period(self,text):
  self.period=text;self.set_status(self.status)
 def set_status(self,text):
  self.status=text;self.card.set_tooltip_text('\n'.join(filter(None,(self.period,text))))
  self.refresh.set_tooltip_text('Refresh logtime\n'+text)
 def resize(self,scale):
  if scale==self.scale:return
  self.scale=scale;size=round(200*scale);self.ring.set_size_request(size,size)
  for icon in self.icons:icon.set_size_request(round(19*scale),round(19*scale))
 def set_accent(self,accent):
  if accent!=self.accent:
   self.accent=accent;self.ring.queue_draw()
 def draw(self,widget,cr):
  x,y,radius,stroke=ring_geometry(widget.get_allocated_width(),widget.get_allocated_height())
  if radius<=0:return False
  rgb=tuple(int(self.accent[i:i+2],16)/255 for i in (1,3,5))
  start=math.pi*.75;sweep=math.pi*1.5
  cr.set_line_width(stroke);cr.set_line_cap(1);cr.set_source_rgba(*rgb,.18)
  cr.arc(x,y,radius,start,start+sweep);cr.stroke()
  if self.fraction>0:
   cr.set_source_rgba(*rgb,.90)
   cr.arc(x,y,radius,start,start+sweep*max(0,min(1,self.fraction)));cr.stroke()
  return False
 def draw_icon(self,widget,cr,name):
  size=min(widget.get_allocated_width(),widget.get_allocated_height())
  cr.save();cr.translate((widget.get_allocated_width()-size)/2,(widget.get_allocated_height()-size)/2);cr.scale(size/24,size/24)
  color=widget.get_style_context().get_color(Gtk.StateFlags.NORMAL)
  cr.set_source_rgba(color.red,color.green,color.blue,color.alpha);cr.set_line_width(1.6);cr.set_line_cap(1);cr.set_line_join(1)
  if name=='today':
   cr.rectangle(3,5,18,16);cr.move_to(3,10);cr.line_to(21,10)
   for x in (7,17):cr.move_to(x,3);cr.line_to(x,7)
  else:
   cr.arc(12,14,8,0,math.pi*2);cr.move_to(12,6);cr.line_to(12,2)
   cr.move_to(9,2);cr.line_to(15,2);cr.move_to(18,7);cr.line_to(20,5)
   cr.move_to(12,14);cr.line_to(12,9)
  cr.stroke();cr.restore();return False
 def render(self,values,scale):
  self.resize(scale)
  for name in ('total','today','session'):getattr(self,name).set_text(values[name])
  self.total.set_tooltip_text('Accumulated logtime · '+values['target']+' · '+values['percent']+'\n'+values['remaining'])
  self.total.get_accessible().set_name('Accumulated logtime '+values['total'])
  self.today.get_accessible().set_name('Today’s logtime '+values['today'])
  self.session.get_accessible().set_name('Current session '+values['session']+(' · active' if values['active'] else ' · inactive'))
  if self.fraction!=values['fraction']:
   self.fraction=values['fraction'];self.ring.queue_draw()
  self.ring.get_accessible().set_name('Logtime completion '+values['percent'])
