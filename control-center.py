#!/usr/bin/python3
"""Neon Studio: a native GTK 4 control panel for your personal desktop."""
import json
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import gi
gi.require_version('Gtk','4.0')
gi.require_version('Adw','1')
gi.require_version('GdkPixbuf','2.0')
from gi.repository import Gtk,Adw,Gdk,GdkPixbuf,Gio,GLib
from preferences import ROOT,WIDGETS,ACCENTS,load,update,effective_accent
import studio_backend as backend
from wallpaper_collection import collection_paths,import_image
from wallpaper_palette import from_image
from live_logtime import live_hours,format_hours
from native_wallpaper import NativeWallpaper

CSS=b'''
window {background:#131018;color:#eee5ee;}
.studio-sidebar {background:#1b161f;border-right:1px solid #352a3c;padding:14px;}
.studio-sidebar row {border-radius:10px;margin:3px 0;}
.studio-sidebar row:selected {background:#48334c;}
.brand {font-size:24px;font-weight:700;letter-spacing:-1px;}
.eyebrow {font-size:11px;font-weight:600;letter-spacing:2px;color:#dba5c9;}
.hero-title {font-size:32px;font-weight:700;letter-spacing:-1px;}
.muted {color:#b8a8ba;}
.panel {background:#211b28;border:1px solid #3b2f42;border-radius:16px;padding:20px;}
.wall-tile {background:#211b28;border:1px solid #3b2f42;border-radius:12px;padding:8px;}
.wall-tile:hover {border-color:#dda3c8;}
.accent-button {background:#dba5c9;color:#231725;font-weight:600;}
.number {font-size:48px;font-weight:300;color:#e5b1d5;}
.preview {border-radius:16px;background:#0b0910;}
.status {background:#27202e;border-radius:12px;padding:12px;}
'''

def label(text='',css=None):
 item=Gtk.Label(label=text,xalign=0,wrap=True)
 if css:item.add_css_class(css)
 return item

def button(text,callback,css=None):
 item=Gtk.Button(label=text)
 if css:item.add_css_class(css)
 item.connect('clicked',callback)
 return item

class Studio(Adw.ApplicationWindow):
 def __init__(self,app):
  super().__init__(application=app,title='Neon Studio',default_width=1120,default_height=820)
  self.snapshot=None;self.snapshot_stale=False;self.busy=False;self.closed=False;self.sources=[];self.selected=None;self.bindings={};self.widget_switches={}
  self.connect('close-request',self.on_close)
  backend.backup_preferences()
  provider=Gtk.CssProvider();provider.load_from_data(CSS)
  Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
  Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
  root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL);self.set_content(root)
  header=Adw.HeaderBar();header.set_title_widget(Adw.WindowTitle(title='Neon Studio',subtitle='Your desktop, your rhythm'))
  root.append(header)
  self.toast_overlay=Adw.ToastOverlay();root.append(self.toast_overlay)
  body=Gtk.Box(vexpand=True);self.toast_overlay.set_child(body)
  sidebar=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10,width_request=205);sidebar.add_css_class('studio-sidebar');body.append(sidebar)
  sidebar.append(label('NEON / STUDIO','eyebrow'));sidebar.append(label('Make it yours.','brand'))
  self.stack=Gtk.Stack(hexpand=True,vexpand=True,transition_type=Gtk.StackTransitionType.CROSSFADE)
  navigation=Gtk.StackSidebar();navigation.set_stack(self.stack);navigation.set_vexpand(True);sidebar.append(navigation)
  self.running_label=label('Desktop cards stopped','muted');sidebar.append(self.running_label)
  sidebar.append(button('Start desktop cards',lambda _:self.action(backend.start_widgets)))
  sidebar.append(button('Stop desktop cards',lambda _:self.action(backend.stop_widgets)))
  body.append(self.stack)
  self.make_wallpapers();self.make_appearance();self.make_widgets();self.make_logtime();self.make_tools()
  self.tick();self.fetch_logtime()
  self.sources.append(GLib.timeout_add_seconds(1,self.tick))
  self.sources.append(GLib.timeout_add_seconds(300,self.fetch_logtime))
 def page(self,name,title,subtitle):
  scroll=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
  content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20,margin_top=28,margin_bottom=28,margin_start=30,margin_end=30)
  content.append(label(title,'hero-title'));content.append(label(subtitle,'muted'))
  scroll.set_child(content);self.stack.add_titled(scroll,name,title);return content
 def panel(self,parent,title=None):
  box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14);box.add_css_class('panel');parent.append(box)
  if title:box.append(label(title,'eyebrow'))
  return box
 def row(self,parent,title,control,subtitle=None):
  row=Gtk.Box(spacing=20);text=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5,hexpand=True)
  text.append(label(title))
  if subtitle:text.append(label(subtitle,'muted'))
  row.append(text);control.set_valign(Gtk.Align.CENTER);row.append(control);parent.append(row)
 def notify(self,message):
  if not self.closed:self.toast_overlay.add_toast(Adw.Toast.new(str(message)))
 def action(self,callback):
  try:
   message=callback()
   if message:self.notify(message)
  except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error:self.notify(str(error))
 def switch(self,parent,title,key,subtitle=None):
  item=Gtk.Switch(active=load()[key]);item.connect('notify::active',lambda control,_:update({key:control.get_active()}));self.row(parent,title,item,subtitle);self.bindings[key]=(item,'switch',1);return item
 def slider(self,parent,title,key,low,high,step,multiplier=1):
  control=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,low,high,step)
  control.set_size_request(230,-1);control.set_digits(0);control.set_value(load()[key]*multiplier)
  control.connect('value-changed',lambda item:self.action(lambda:update({key:item.get_value()/multiplier})))
  self.row(parent,title,control)
  self.bindings[key]=(control,'slider',multiplier)
 def make_wallpapers(self):
  page=self.page('wallpapers','Wallpapers','A quiet backdrop. A different mood. Original landscapes, ten 4K anime wallpapers, and your own imports.')
  hero=self.panel(page)
  self.preview=Gtk.Picture(can_shrink=True,keep_aspect_ratio=True,height_request=260);self.preview.add_css_class('preview');hero.append(self.preview)
  self.wall_title=label('Choose a scene','brand');hero.append(self.wall_title)
  self.wall_info=label('3840 × 2160 · original collection','muted');hero.append(self.wall_info)
  actions=Gtk.Box(spacing=10);hero.append(actions)
  self.apply_button=button('Apply wallpaper',lambda _:self.action(self.apply_wallpaper),'accent-button');actions.append(self.apply_button)
  actions.append(button('Match widget accent',lambda _:self.match_accent()))
  actions.append(button('Open image…',lambda _:self.choose(False)))
  self.import_button=button('Add to collection…',lambda _:self.add_to_collection(),'accent-button')
  hero.append(self.import_button)
  self.bg=NativeWallpaper()
  self.wall_status=label('','status');page.append(self.wall_status)
  folders=Gtk.Box(spacing=10);page.append(folders)
  self.folder_label=label(load()['wallpaper_folder'],'muted');self.folder_label.set_hexpand(True);self.folder_label.set_ellipsize(3);folders.append(self.folder_label)
  folders.append(button('Change folder…',lambda _:self.choose(True)))
  folders.append(button('Refresh',lambda _:self.fill_gallery()))
  self.gallery=Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,min_children_per_line=1,max_children_per_line=3,column_spacing=12,row_spacing=12,homogeneous=True)
  page.append(self.gallery);self.fill_gallery()
 def texture(self,path,width,height):
  pix=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path),width,height,True)
  return Gdk.Texture.new_for_pixbuf(pix)
 def fill_gallery(self):
  child=self.gallery.get_first_child()
  while child:
   following=child.get_next_sibling();self.gallery.remove(child);child=following
  folder=load()['wallpaper_folder'];self.folder_label.set_text(folder)
  paths=collection_paths(folder)
  for path in paths:
   try:
    box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=9)
    image=Gtk.Picture.new_for_paintable(self.texture(path,240,135));image.set_size_request(190,107);image.set_can_shrink(True);box.append(image)
    import re
    title=label(re.sub(r'^(?:anime-)?\d{2}-','',path.stem).replace('-',' ').title())
    title.set_ellipsize(3);title.set_max_width_chars(24);box.append(title)
    tile=Gtk.Button(child=box);tile.add_css_class('wall-tile');tile.connect('clicked',lambda _,chosen=path:self.select(chosen));self.gallery.insert(tile,-1)
   except GLib.Error:continue
  if paths:
   if self.selected not in paths:self.select(paths[0])
  else:self.gallery.insert(label('No readable images found. Choose another folder.'),-1)
 def select(self,path):
  try:
   self.preview.set_paintable(self.texture(path,1000,560));self.selected=path
   import re
   self.wall_title.set_text(re.sub(r'^(?:anime-)?\d{2}-','',path.stem).replace('-',' ').title())
   info=GdkPixbuf.Pixbuf.get_file_info(str(path))
   if info and info[0]:self.wall_info.set_text(f'{info[1]} × {info[2]} · '+('4K' if info[1]>=3840 and info[2]>=2160 else 'Image'))
  except GLib.Error as error:self.notify('Could not open image: '+str(error))
 def choose(self,folder):
  chooser=Gtk.FileChooserNative.new('Choose wallpaper folder' if folder else 'Choose an image',self,Gtk.FileChooserAction.SELECT_FOLDER if folder else Gtk.FileChooserAction.OPEN,'Choose','Cancel')
  if not folder:
   filter=Gtk.FileFilter();filter.set_name('Images')
   for suffix in backend.IMAGE_SUFFIXES:filter.add_pattern('*'+suffix)
   chooser.add_filter(filter)
  def respond(dialog,response):
   if response==Gtk.ResponseType.ACCEPT:
    file=dialog.get_file();path=file.get_path() if file else None
    if path:
     if folder:update({'wallpaper_folder':path});self.fill_gallery()
     else:self.select(Path(path))
   dialog.destroy()
  chooser.connect('response',respond);chooser.show();self.chooser=chooser
 def add_to_collection(self):
  chooser=Gtk.FileChooserNative.new('Add wallpapers to your collection',self,Gtk.FileChooserAction.OPEN,'Add','Cancel')
  chooser.set_select_multiple(True)
  filter=Gtk.FileFilter();filter.set_name('Images')
  for suffix in backend.IMAGE_SUFFIXES:filter.add_pattern('*'+suffix)
  chooser.add_filter(filter)
  def respond(dialog,response):
   if response==Gtk.ResponseType.ACCEPT:
    files=dialog.get_files();paths=[files.get_item(i).get_path() for i in range(files.get_n_items())]
    self.import_button.set_sensitive(False)
    def worker():
     added=[];errors=[]
     for path in paths:
      if path is None:continue
      try:added.append(import_image(path))
      except (OSError,ValueError,GLib.Error) as error:errors.append(str(error))
     GLib.idle_add(self.import_finished,added,errors)
    threading.Thread(target=worker,daemon=True).start()
   dialog.destroy()
  chooser.connect('response',respond);chooser.show();self.chooser=chooser
 def import_finished(self,added,errors):
  if self.closed:return GLib.SOURCE_REMOVE
  self.import_button.set_sensitive(True);self.fill_gallery()
  if added:self.select(added[-1]);self.notify(f'{len(added)} wallpaper(s) ready in your collection.')
  if errors:self.notify('Some files could not be added: '+errors[0])
  return GLib.SOURCE_REMOVE
 def wallpaper_writable(self):return all(self.bg.is_writable(key) for key in ('picture-uri','picture-uri-dark'))
 def apply_wallpaper(self):
  if not self.selected:return
  if not self.selected.is_file():self.notify('That image was moved or deleted. Refresh the collection.');return
  if not self.wallpaper_writable():self.notify('GNOME has locked wallpaper changes for this session.');return
  backup=ROOT/'state/wallpaper-before.json'
  if not backup.exists():backup.write_text(json.dumps({key:(self.bg.get_original(key) if hasattr(self.bg,'get_original') else self.bg.get_string(key)) for key in ('picture-uri','picture-uri-dark','picture-options')}))
  if hasattr(self.bg,'ensure_setup'):self.bg.ensure_setup()
  old={key:self.bg.get_string(key) for key in ('picture-uri','picture-uri-dark')}
  done=[]
  try:
   for key in old:
    if not self.bg.set_string(key,self.selected.resolve().as_uri()):raise RuntimeError('GNOME rejected the wallpaper change.')
    done.append(key)
   if self.bg.is_writable('picture-options'):self.bg.set_string('picture-options','zoom')
   Gio.Settings.sync()
   update({'active_wallpaper':str(self.selected.resolve())})
   if load()['auto_accent']:self.match_accent(silent=True)
   if getattr(self.bg,'pending_login',False):self.notify('Wallpaper saved. Log out and back in once to activate your personal wallpaper profile.')
   else:self.notify('Wallpaper applied.')
  except RuntimeError as error:
   for key in done:
    try:self.bg.set_string(key,old[key])
    except RuntimeError:pass
   self.notify(str(error))
 def match_accent(self,silent=False,path=None):
  image=path or self.selected
  if image is None:return
  try:
   color=from_image(image)
   update({'auto_accent':True,'accent_color':color})
   if hasattr(self,'auto_color_switch') and not self.auto_color_switch.get_active():
    self.auto_color_switch.handler_block_by_func(self.auto_color_changed)
    self.auto_color_switch.set_active(True)
    self.auto_color_switch.handler_unblock_by_func(self.auto_color_changed)
   if not silent:self.notify('Widget color matched: '+color)
  except (OSError,ValueError,GLib.Error) as error:self.notify('Could not read the wallpaper colors: '+str(error))
 def choose_preset(self,name):
  update({'accent':name,'auto_accent':False})
  if hasattr(self,'auto_color_switch'):self.auto_color_switch.set_active(False)
  self.notify('Fixed accent: '+name)
 def auto_color_changed(self,control,_):
  enabled=control.get_active();update({'auto_accent':enabled})
  if enabled:
   active=load()['active_wallpaper']
   image=Path(active) if active and Path(active).is_file() else self.selected
   if image:self.match_accent(silent=True,path=image)
 def make_appearance(self):
  page=self.page('appearance','Appearance','Soft surfaces, readable type, and an accent that feels like you.')
  group=self.panel(page,'COLOR')
  colors=Gtk.Box(spacing=10);group.append(colors)
  for name,color in ACCENTS.items():
   item=button(name,lambda _,chosen=name:self.choose_preset(chosen))
   item.set_tooltip_text(color);colors.append(item)
  self.auto_color_switch=Gtk.Switch(active=load()['auto_accent'])
  self.auto_color_switch.connect('notify::active',self.auto_color_changed)
  self.row(group,'Automatically match wallpaper',self.auto_color_switch,'Use the strongest wallpaper hue when applying an image. A fixed preset turns this off.')
  self.bindings['auto_accent']=(self.auto_color_switch,'switch',1)
  self.accent_readout=label('','muted');group.append(self.accent_readout)
  group.append(label('Colors apply to your widgets. Other applications keep their existing theme.','muted'))
  sizing=self.panel(page,'SCALE & TRANSPARENCY')
  self.slider(sizing,'Widget size (%)','scale',80,180,5,100)
  self.slider(sizing,'Opacity (%)','opacity',30,100,1,100)
  self.slider(sizing,'Screen margin (px)','margin',0,200,2)
  self.switch(sizing,'Show clock seconds','clock_seconds')
 def make_widgets(self):
  page=self.page('widgets','Widgets','Choose your essentials. Move them into place. Changes save automatically.')
  group=self.panel(page,'YOUR DESKTOP')
  for key,title in WIDGETS.items():
   item=Gtk.Switch(active=load()['visible'][key])
   def toggled(control,_,name=key):
    prefs=load();prefs['visible'][name]=control.get_active();update({'visible':prefs['visible']})
   item.connect('notify::active',toggled);self.row(group,title,item);self.widget_switches[key]=item
  arrange=self.panel(page,'LAYOUT')
  self.arrange_switch=self.switch(arrange,'Arrange widgets','arrange','Cards rise above windows. Drag their title or empty area, then turn this off.')
  arrange.append(button('Reset card positions',lambda _:self.action(lambda:(update({'positions':{}}),'Card positions reset.')[1])))
  self.autostart=Gtk.Switch(active=backend.autostart_enabled());self.autostart.connect('notify::active',self.autostart_changed)
  self.row(arrange,'Start cards when I log in',self.autostart)
  notes=self.panel(page,'YOUR NOTE')
  self.note_buffer=Gtk.TextBuffer();self.note_buffer.set_text(load()['notes'])
  editor=Gtk.TextView(buffer=self.note_buffer,wrap_mode=Gtk.WrapMode.WORD_CHAR,height_request=120,top_margin=10,bottom_margin=10,left_margin=10,right_margin=10)
  notes.append(editor);notes.append(button('Save note',lambda _:self.save_note(),'accent-button'))
 def autostart_changed(self,control,_):
  enabled=control.get_active()
  try:backend.set_autostart(enabled);self.notify('Login startup '+('enabled.' if enabled else 'disabled.'))
  except (OSError,subprocess.SubprocessError) as error:
   self.notify(str(error));control.handler_block_by_func(self.autostart_changed);control.set_active(not enabled);control.handler_unblock_by_func(self.autostart_changed)
 def save_note(self):
  start,end=self.note_buffer.get_bounds();update({'notes':self.note_buffer.get_text(start,end,False)});self.notify('Note saved.')
 def make_logtime(self):
  page=self.page('logtime','Logtime','Your 1337 progress, with a live estimate of the current session.')
  group=self.panel(page,'CURRENT PERIOD')
  self.log_value=label('—','number');group.append(self.log_value)
  self.log_bar=Gtk.ProgressBar();group.append(self.log_bar)
  self.log_details=label('Loading…','muted');group.append(self.log_details)
  group.append(button('Refresh logtime',lambda _:self.fetch_logtime()))
  settings=self.panel(page,'ACCOUNT & GOAL')
  self.username=Gtk.Entry(text=load()['username'],placeholder_text='Your Linux login (automatic)');self.row(settings,'1337 username',self.username)
  self.goal=Gtk.SpinButton.new_with_range(1,1000,1);self.goal.set_value(load()['target_hours']);self.row(settings,'Period target (hours)',self.goal)
  settings.append(button('Save logtime settings',lambda _:self.save_logtime(),'accent-button'))
  settings.append(label('Period: the 28th through the following 27th. The live session is an estimate until the campus API confirms it.','muted'))
 def save_logtime(self):
  name=self.username.get_text().strip()
  import re
  if not re.fullmatch(r'[A-Za-z0-9_-]*',name):self.notify('Use letters, numbers, underscore or hyphen for the username.');return
  update({'username':name,'target_hours':self.goal.get_value()});self.snapshot=None;self.fetch_logtime();self.notify('Logtime settings saved.')
 def fetch_logtime(self):
  if self.busy:return GLib.SOURCE_CONTINUE
  self.busy=True
  def worker():
   try:
    result=subprocess.run([str(ROOT/'python'),str(ROOT/'logtime-widget.py')],capture_output=True,text=True,timeout=40)
    if result.returncode:raise ValueError(result.stderr[-400:])
    data=json.loads(result.stdout);GLib.idle_add(self.receive_logtime,data,None)
   except (OSError,ValueError,subprocess.SubprocessError) as error:GLib.idle_add(self.receive_logtime,None,str(error))
  threading.Thread(target=worker,daemon=True).start();return GLib.SOURCE_CONTINUE
 def receive_logtime(self,data,error):
  self.busy=False
  if self.closed:return GLib.SOURCE_REMOVE
  if data:self.snapshot=data;self.snapshot_stale=False
  else:
   self.snapshot_stale=True
   if not self.snapshot:self.log_details.set_text('Logtime unavailable. Check your connection and username, then Refresh.')
  return GLib.SOURCE_REMOVE
 def make_tools(self):
  page=self.page('tools','Tools','Simple controls. A clear way back.')
  group=self.panel(page,'DESKTOP CARDS')
  group.append(button('Start desktop cards',lambda _:self.action(backend.start_widgets),'accent-button'))
  group.append(button('Stop desktop cards',lambda _:self.action(backend.stop_widgets)))
  group.append(button('Open package folder',lambda _:Gtk.show_uri(self,(ROOT).as_uri(),Gdk.CURRENT_TIME)))
  restore=self.panel(page,'RESTORE')
  restore.append(label('Restore the widget preferences saved before opening Neon Studio. Your files and wallpaper collection stay here.','muted'))
  restore.append(button('Restore previous widget settings',lambda _:self.restore_widgets()))
  restore.append(button('Restore previous wallpaper',lambda _:self.restore_wallpaper()))
  restore.append(button('Disable personal wallpaper setup',lambda _:self.action(self.bg.disable_setup)))
  diagnostics=self.panel(page,'DIAGNOSTICS')
  self.diagnostics=label('','muted');self.diagnostics.set_selectable(True);diagnostics.append(self.diagnostics)
  diagnostics.append(button('Refresh diagnostics',lambda _:self.refresh_diagnostics()));self.refresh_diagnostics()
  page.append(label('Neon Studio · Built for your desktop\nInspired by TrpStrata. Uses native GTK controls and your supplied logtime tracker.','muted'))
 def restore_widgets(self):
  try:
   message=backend.restore_preferences();prefs=load()
   for key,(control,kind,multiplier) in self.bindings.items():
    if kind=='switch':
     if key=='auto_accent':control.handler_block_by_func(self.auto_color_changed)
     control.set_active(prefs[key])
     if key=='auto_accent':control.handler_unblock_by_func(self.auto_color_changed)
    else:control.set_value(prefs[key]*multiplier)
   for key,control in self.widget_switches.items():control.set_active(prefs['visible'][key])
   self.note_buffer.set_text(prefs['notes']);self.username.set_text(prefs['username']);self.goal.set_value(prefs['target_hours'])
   self.fill_gallery();self.notify(message)
  except (OSError,RuntimeError,ValueError) as error:self.notify(str(error))
 def restore_wallpaper(self):
  path=ROOT/'state/wallpaper-before.json'
  if not path.exists():self.notify('No wallpaper was changed by Neon Studio.');return
  try:
   saved=json.loads(path.read_text())
   if not all(self.bg.is_writable(key) for key in saved):raise RuntimeError('GNOME has locked these background settings.')
   previous={key:self.bg.get_string(key) for key in saved};completed=[]
   try:
    for key,value in saved.items():
     if not self.bg.set_string(key,value):raise RuntimeError('GNOME could not restore '+key)
     completed.append(key)
   except RuntimeError:
    for key in reversed(completed):self.bg.set_string(key,previous[key])
    raise
   Gio.Settings.sync();path.unlink();self.notify('Previous wallpaper restored.')
  except (OSError,ValueError,RuntimeError) as error:self.notify(str(error))
 def refresh_diagnostics(self):
  lines=['Widgets: '+('running' if backend.widget_pids() else 'stopped'),'Wallpaper profile: '+str(self.bg.profile),'Wallpaper status: '+self.bg.status_text(),'Python tracker: '+('ready' if (ROOT/'python').exists() else 'run install.sh'),'Package: '+str(ROOT)]
  log=ROOT/'state/widgets.log'
  if log.exists():lines+=['','Recent widget log:',log.read_text(errors='replace')[-1500:]]
  self.diagnostics.set_text('\n'.join(lines))
 def tick(self):
  if self.closed:return GLib.SOURCE_REMOVE
  prefs=load();self.accent_readout.set_text(('Wallpaper dominant color · ' if prefs['auto_accent'] else 'Fixed accent · ')+effective_accent(prefs))
  running=bool(backend.widget_pids());self.running_label.set_text('● Desktop cards running' if running else '○ Desktop cards stopped')
  writable=self.wallpaper_writable();self.apply_button.set_sensitive(writable and self.selected is not None)
  self.wall_status.set_text(self.bg.status_text() if writable else (self.bg.last_error or 'The personal wallpaper profile could not be prepared. See Tools → Diagnostics.'))
  if self.snapshot:
   h=live_hours(self.snapshot);target=load()['target_hours'];self.log_value.set_text(format_hours(h['projected']));self.log_bar.set_fraction(max(0,min(1,h['projected']/target)))
   state='API offline · last total + live session' if self.snapshot_stale else 'Live session included' if self.snapshot.get('session_detected') else 'API total · session not detected'
   self.log_details.set_text(f"{self.snapshot['period']['start']} → {self.snapshot['period']['end']}\nTarget · {target:g} h   /   Session · {format_hours(h['session'])}\n{state}")
  return GLib.SOURCE_CONTINUE
 def on_close(self,*_):
  self.closed=True
  for source in self.sources:GLib.source_remove(source)
  return False

class App(Adw.Application):
 def __init__(self):
  super().__init__(application_id='local.neon.Studio',flags=Gio.ApplicationFlags.FLAGS_NONE)
  self.startup_failed=False
 def do_activate(self):
  window=self.get_active_window()
  try:
   if window is None:window=Studio(self)
   window.present()
  except Exception:
   import traceback
   traceback.print_exc();self.startup_failed=True;self.quit()
if __name__=='__main__':
 print('Starting Neon Studio control panel…',flush=True)
 app=App();code=app.run(sys.argv)
 sys.exit(1 if app.startup_failed else code)
