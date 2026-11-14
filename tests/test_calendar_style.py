"""Check the actual GTK3 parser without loading GTK3 into the GTK4 test process."""
import os,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CalendarStyleTests(unittest.TestCase):
 def test_transparent_calendar_rules_parse_with_system_gtk3(self):
  script="""
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk
from widget_styles import calendar_css
css=calendar_css('#dfa1c6')
assert 'calendar:selected' in css and 'background-color:transparent' in css
provider=Gtk.CssProvider();errors=[]
provider.connect('parsing-error',lambda _,section,error:errors.append(str(error)))
provider.load_from_data(css.encode())
assert not errors,errors
"""
  result=subprocess.run(['/usr/bin/python3','-c',script],cwd=ROOT,env=dict(os.environ,GSETTINGS_BACKEND='memory'),capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
if __name__=='__main__':unittest.main()
