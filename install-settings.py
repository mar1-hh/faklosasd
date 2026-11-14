#!/usr/bin/python3
import os
from pathlib import Path
root=Path(__file__).resolve().parent
folder=Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'applications'
folder.mkdir(parents=True,exist_ok=True)
script=str(root/'control-center.py').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
(folder/'neon-desktop-settings.desktop').write_text('[Desktop Entry]\nType=Application\nName=Neon Studio\nComment=Your wallpaper collection, desktop widgets and live logtime\nExec=/usr/bin/python3 "'+script+'"\nIcon=' + str(root/'assets/neon-studio.svg') + '\nTerminal=false\nCategories=Settings;DesktopSettings;\n')
print('Added Neon Studio to the applications menu.')
