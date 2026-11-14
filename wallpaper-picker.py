#!/usr/bin/python3
import gi
from pathlib import Path
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, GdkPixbuf, Gio
root=Path(__file__).resolve().parent
window=Gtk.Window(title='Neon · 4K wallpaper collection')
window.set_default_size(880,480)
window.set_border_width(18)
window.connect('destroy',Gtk.main_quit)
grid=Gtk.Grid(column_spacing=14,row_spacing=14)
window.add(grid)
def choose(button,path):
 settings=Gio.Settings.new('org.gnome.desktop.background')
 for key in ('picture-uri','picture-uri-dark'): settings.set_string(key,path.as_uri())
 settings.set_string('picture-options','zoom')
 Gio.Settings.sync()
settings=Gio.Settings.new('org.gnome.desktop.background')
writable=all(settings.is_writable(key) for key in ('picture-uri','picture-uri-dark'))
if not writable:
 window.set_title('Wallpapers · background locked by administrator')
for i,path in enumerate(sorted((root/'wallpapers').glob('*.png'))):
 box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
 pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path),260,146,True)
 box.pack_start(Gtk.Image.new_from_pixbuf(pixbuf),True,True,0)
 box.pack_start(Gtk.Label(label=path.stem[3:].replace('-',' ').title()),False,False,0)
 button=Gtk.Button(); button.add(box); button.connect('clicked',choose,path)
 button.set_sensitive(writable)
 if not writable: button.set_tooltip_text('Administrator policy locks the desktop background. These images are available in the wallpapers folder.')
 grid.attach(button,i%3,i//3,1,1)
window.show_all()
Gtk.main()
