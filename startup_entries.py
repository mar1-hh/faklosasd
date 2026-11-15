"""Identify this project's startup entries without touching unrelated applications."""
import configparser
from pathlib import Path
import shlex

def fields(text):
 parser=configparser.ConfigParser(interpolation=None)
 parser.optionxform=str
 try:
  parser.read_string(text);return dict(parser['Desktop Entry'])
 except (configparser.Error,KeyError):return {}
def widget_target(text):
 data=fields(text)
 try:args=shlex.split(data.get('Exec',''))
 except ValueError:return None
 for arg in args:
  if Path(arg).name in ('desktop-widgets.py','dashboard.py') and Path(arg).is_absolute():return Path(arg)
 return None
def is_widget_entry(text):
 data=fields(text)
 return widget_target(text) is not None and (data.get('X-Neon-Widgets-Managed')=='true' or data.get('Name')=='Neon Desktop Widgets')
def is_enabled(text):
 data=fields(text)
 return data.get('Hidden','false').lower()!='true' and data.get('X-GNOME-Autostart-enabled','true').lower()!='false'
