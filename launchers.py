"""Discover optional launcher apps without failing when desktop files are absent."""
CANDIDATES=(('firefox.desktop','Web'),('org.gnome.Nautilus.desktop','Files'),('org.gnome.Terminal.desktop','Terminal'),('code.desktop','Code'))
def available_apps(resolver=None):
 if resolver is None:
  from gi.repository import Gio
  resolver=Gio.DesktopAppInfo.new
 result=[]
 for desktop_id,title in CANDIDATES:
  try:app=resolver(desktop_id)
  except TypeError:continue
  if app is not None:result.append((title,app))
 return result
