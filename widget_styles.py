"""Shared calendar overrides for GTK 3's legacy drawing states."""
def calendar_css(accent):
 return f'''
 .desktop-widget calendar,
 .desktop-widget calendar.view,
 .desktop-widget calendar.header,
 .desktop-widget calendar .view,
 .desktop-widget calendar .header,
 .desktop-widget calendar.button,
 .desktop-widget calendar button,
 .desktop-widget calendar:selected,
 .desktop-widget calendar:indeterminate,
 .desktop-widget calendar.highlight {{
  background-color:transparent;
  background-image:none;
  border-color:transparent;
  box-shadow:none;
  text-shadow:none;
 }}
 .desktop-widget calendar {{color:#e9e2eb;border-width:0;padding:4px;}}
 .desktop-widget calendar.header {{color:{accent};font-weight:600;}}
 .desktop-widget calendar.highlight {{color:{accent};}}
 .desktop-widget calendar:selected {{color:{accent};font-weight:700;background-color:transparent;}}
 .desktop-widget calendar:indeterminate {{color:alpha(#e9e2eb,0.38);}}
 '''
