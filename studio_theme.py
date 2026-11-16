"""Neon Studio surfaces follow the same validated accent as desktop widgets."""
from preferences import effective_accent, normalize

def theme_css(preferences):
 prefs=normalize(preferences);accent=effective_accent(prefs)
 rgb=tuple(int(accent[i:i+2],16) for i in (1,3,5))
 alpha=1-prefs['studio_transparency']/100
 def surface(level):
  values=','.join(str(round(channel*level)) for channel in rgb)
  return f'rgba({values},{alpha:.3f})'
 return f'''
 window.neon-studio {{background-color:{surface(.12)};background-image:none;color:#f5f1f6;}}
 .neon-studio headerbar {{background-color:{surface(.16)};background-image:none;}}
 .neon-studio .studio-sidebar {{background-color:{surface(.16)};border-color:alpha({accent},.25);}}
 .neon-studio .panel,.neon-studio .wall-tile {{background-color:{surface(.21)};border-color:alpha({accent},.28);}}
 .neon-studio .status {{background-color:{surface(.25)};}}
 .neon-studio .studio-sidebar row:selected {{background-color:alpha({accent},.22);}}
 .neon-studio .eyebrow,.neon-studio .number {{color:{accent};}}
 .neon-studio .accent-button {{background-color:{accent};background-image:none;color:#17131b;}}
 .neon-studio .wall-tile:hover,.neon-studio .wall-tile.selected {{border-color:{accent};}}
 .neon-studio .wall-tile.applied {{box-shadow:inset 0 0 0 2px {accent};}}
 .neon-studio scale highlight,.neon-studio switch:checked {{background-color:{accent};}}
 '''.encode()
