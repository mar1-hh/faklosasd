"""Shared styles and unified design system for Neon Studio desktop widgets."""

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
 .desktop-widget calendar.highlight {{color:{accent};font-weight:800;text-shadow:0 0 3px alpha({accent},0.5);}}
 .desktop-widget calendar:selected {{color:{accent};font-weight:700;background-color:transparent;}}
 .desktop-widget calendar:indeterminate {{color:alpha(#e9e2eb,0.38);}}
 '''


def design_system_css(scale=1.0, accent="#dfa1c6"):
    """Unified dark charcoal design system for Now Playing and Application Launcher."""
    s = scale
    return f"""
    /* Charcoal Card Containers matching Reference Mockup */
    .desktop-widget .launcher-dock-card {{
        background: rgba(30, 30, 32, 0.94);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: {round(24 * s)}px;
        padding: {round(18 * s)}px;
        box-shadow: 0 10px 32px rgba(0, 0, 0, 0.40);
    }}

    /* Application Launcher Refined Styles */
    .desktop-widget .launcher-title-icon {{
        color: #f5f5f7;
        margin-right: {round(6 * s)}px;
    }}

    .desktop-widget .launcher-title-label {{
        font-size: {round(13 * s)}px;
        font-weight: 600;
        color: #f5f5f7;
        letter-spacing: 0.2px;
    }}

    .desktop-widget .launcher-search-box {{
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: {round(12 * s)}px;
        padding: {round(4 * s)}px {round(10 * s)}px;
    }}

    .desktop-widget .launcher-search-box:focus-within {{
        background: rgba(255, 255, 255, 0.07);
        border-color: alpha({accent}, 0.50);
    }}

    .desktop-widget .launcher-search-icon {{
        color: #8e8e93;
        margin-right: {round(6 * s)}px;
    }}

    .desktop-widget .launcher-search-entry-inner {{
        background: transparent;
        border: none;
        box-shadow: none;
        color: #f5f5f7;
        font-size: {round(12 * s)}px;
        padding: 0;
    }}

    .desktop-widget .launcher-search-entry-inner:focus {{
        background: transparent;
        border: none;
        box-shadow: none;
    }}

    .desktop-widget .launcher-esc-badge {{
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: {round(4 * s)}px;
        color: #8e8e93;
        font-size: {round(9 * s)}px;
        font-family: monospace, Sans;
        font-weight: 600;
        padding: 1px 5px;
        margin-left: {round(6 * s)}px;
    }}

    .desktop-widget .launcher-app-btn {{
        border-radius: {round(14 * s)}px;
        padding: {round(8 * s)}px {round(6 * s)}px;
        background: transparent;
        border: 1px solid transparent;
        min-width: {round(64 * s)}px;
    }}

    .desktop-widget .launcher-app-btn:hover {{
        background: rgba(255, 255, 255, 0.07);
        border-color: rgba(255, 255, 255, 0.12);
    }}

    .desktop-widget .launcher-app-label {{
        font-size: {round(11 * s)}px;
        color: #e5e5ea;
        font-weight: 400;
        margin-top: {round(4 * s)}px;
    }}
    """


def media_css(scale=1.0, accent='#dfa1c6', compact=False, opacity=1.0):
    """Scoped card styles also used by the standalone dashboard."""
    s = scale
    text = s * (.86 if compact else 1)
    return f'''
    .media-widget-card {{
        background: rgba(25, 24, 43, {0.97*opacity:.3f});
        border: 1px solid rgba(221, 216, 239, 0.24);
        border-radius: {round(24*s)}px;
        padding: {round(11*s)}px;
        box-shadow: none;
    }}
    .media-widget-card label {{ text-shadow: none; }}
    .media-widget-card .media-track-title {{
        color: #faf9ff; font-size: {round(16*text)}px; font-weight: 800;
    }}
    .media-widget-card .media-track-artist {{
        color: {accent}; font-size: {round(14*text)}px; font-weight: 400;
        margin-top: {round(2*s)}px;
    }}
    .media-widget-card .media-track-album {{
        color: #9390a8; font-size: {round(11*text)}px; font-weight: 400;
        letter-spacing: {s:.2f}px; margin-top: {round(2*s)}px;
    }}
    .media-widget-card .media-progress-scale {{
        padding: {round(5*s)}px 0; min-height: {round(10*s)}px;
    }}
    .media-widget-card .media-progress-scale trough {{
        background: rgba(184, 179, 209, .36); min-height: {max(3, round(4*s))}px;
        border-radius: 99px; border: none; box-shadow: none;
    }}
    .media-widget-card .media-progress-scale highlight {{
        background: {accent}; min-height: 0;
        border-radius: 99px; border: none; box-shadow: none;
    }}
    .media-widget-card .media-progress-scale slider {{
        background: #f6f4ff; min-width: {round(10*s)}px; min-height: {round(10*s)}px;
        border-radius: 50%; border: none; box-shadow: none;
        margin: -{round(3*s)}px 0;
    }}
    .media-widget-card .media-progress-scale:disabled slider {{ opacity: 0; }}
    .media-widget-card .media-time-label {{
        color: #b9b4ce; font-family: Monospace; font-size: {round(9*text)}px;
        font-weight: 400;
    }}
    .media-widget-card button.media-icon-button {{
        background: transparent; background-image: none; border: none;
        border-radius: 0; outline-width: 0; box-shadow: none; text-shadow: none;
        padding: 0; margin: 0; min-width: 44px; min-height: 44px;
        color: #faf9ff;
    }}
    .media-widget-card button.media-icon-button:hover {{ color: {accent}; }}
    .media-widget-card button.media-icon-button:active {{ color: alpha({accent}, .72); }}
    .media-widget-card button.media-icon-button:disabled {{ color: rgba(250, 249, 255, .23); }}
    .media-widget-card button.media-icon-button:focus {{
        outline: 2px dotted alpha({accent}, .9); outline-offset: -5px;
    }}
    '''
