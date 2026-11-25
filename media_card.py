"""Artwork-first GTK 3 media card backed by the existing MPRIS manager."""
import math

import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango

from media_player import MediaPlayerManager, format_time
from preferences import load as load_preferences, effective_accent
from widget_styles import media_css


def rounded_rectangle(ctx, width, height, radius):
    radius = min(radius, width / 2, height / 2)
    ctx.new_sub_path()
    for x, y, start in ((width-radius, radius, -math.pi/2),
                        (width-radius, height-radius, 0),
                        (radius, height-radius, math.pi/2),
                        (radius, radius, math.pi)):
        ctx.arc(x, y, radius, start, start+math.pi/2)
    ctx.close_path()


def cover_geometry(source_width, source_height, width, height):
    """Aspect-fill scale and centered offsets, in the target's coordinate space."""
    factor = max(width / source_width, height / source_height)
    return factor, (width-source_width*factor)/2, (height-source_height*factor)/2


def paint_cover(ctx, pixbuf, width, height, radius):
    """Clip in logical coordinates; Cairo retains the destination's HiDPI scale."""
    ctx.save()
    rounded_rectangle(ctx, width, height, radius)
    ctx.clip()
    factor, x, y = cover_geometry(pixbuf.get_width(), pixbuf.get_height(), width, height)
    ctx.translate(x, y)
    ctx.scale(factor, factor)
    Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_BEST)
    ctx.paint()
    ctx.restore()


class CoverArt(Gtk.DrawingArea):
    """Keep the original pixels cached; crop at the actual drawing allocation."""
    def __init__(self):
        super().__init__()
        self.pixbuf = None
        self.path = None
        self.radius = 26
        self.get_accessible().set_name('Album artwork')
        self.connect('draw', self._draw)

    def set_artwork(self, path):
        path = str(path) if path else None
        if path == self.path:
            return
        self.path = path
        self.pixbuf = None
        if path:
            try:
                self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            except Exception:
                # Corrupt, missing, and unsupported images all use the same placeholder.
                pass
        self.queue_draw()

    def _draw(self, widget, ctx):
        width, height = self.get_allocated_width(), self.get_allocated_height()
        if self.pixbuf:
            paint_cover(ctx, self.pixbuf, width, height, self.radius)
            return False
        rounded_rectangle(ctx, width, height, self.radius)
        ctx.set_source_rgba(.105, .095, .155, .9)
        ctx.fill()
        # A single clean vector music note, independent of icon theme and DPI.
        ctx.save()
        size = min(width, height) * .34
        ctx.translate((width-size)/2, (height-size)/2)
        ctx.scale(size/100, size/100)
        ctx.set_source_rgba(.63, .59, .72, .7)
        ctx.set_line_width(7)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(36, 76); ctx.line_to(36, 24); ctx.line_to(78, 14); ctx.line_to(78, 66)
        ctx.stroke()
        ctx.move_to(36, 30); ctx.line_to(78, 20); ctx.line_to(78, 32); ctx.line_to(36, 42)
        ctx.close_path(); ctx.fill()
        for x, y in ((26, 78), (68, 68)):
            ctx.save(); ctx.translate(x, y); ctx.scale(14, 10)
            ctx.arc(0, 0, 1, 0, math.tau); ctx.fill(); ctx.restore()
        ctx.restore()
        return False


class TransportIcon(Gtk.DrawingArea):
    """Bold scalable media symbols; the parent remains a keyboard-accessible button."""
    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol
        self.connect('draw', self._draw)

    def _draw(self, widget, ctx):
        button = self.get_parent()
        color = button.get_style_context().get_color(button.get_state_flags())
        ctx.push_group()
        ctx.set_source_rgb(color.red, color.green, color.blue)
        width, height = self.get_allocated_width(), self.get_allocated_height()
        size = min(width*.60, height*.46) if self.symbol in ('play', 'pause') else min(width*.56, height*.36)
        ctx.translate((width-size)/2, (height-size)/2)
        ctx.scale(size/100, size/100)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_width(7)
        if self.symbol == 'pause':
            for x in (20, 60):
                ctx.rectangle(x, 4, 20, 92)
                ctx.fill()
        else:
            if self.symbol == 'previous':
                ctx.translate(100, 0); ctx.scale(-1, 1)
            triangles = ((17, 4, 91, 50, 17, 96),) if self.symbol == 'play' else (
                (3, 14, 48, 50, 3, 86), (53, 14, 98, 50, 53, 86))
            for x1, y1, x2, y2, x3, y3 in triangles:
                ctx.move_to(x1, y1); ctx.line_to(x2, y2); ctx.line_to(x3, y3)
                ctx.close_path(); ctx.fill_preserve(); ctx.stroke()
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(color.alpha)
        return False


class MediaCard:
    def __init__(self, host, parent, manager=None):
        self.manager = manager or MediaPlayerManager()
        self.manager.start()
        self.scale = 1.0
        self.compact = False
        self.user_scrubbing = False
        self.seek_track = None
        self._style_key = None
        self._layout_key = None
        self._resize_source = 0
        self.card = host.card(parent, '')
        self.card.set_spacing(0)
        self.card.get_style_context().add_class('media-widget-card')
        self.card.get_accessible().set_name('Now Playing')
        self.css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(self.card.get_screen(), self.css,
                                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION+3)
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.card.pack_start(self.content_box, True, True, 0)
        self.art_image = CoverArt()
        self.content_box.pack_start(self.art_image, False, False, 0)
        self.meta_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.meta_box.set_valign(Gtk.Align.CENTER)
        self.content_box.pack_start(self.meta_box, False, False, 0)
        for name, style in (('title', 'title'), ('artist', 'artist'), ('album', 'album')):
            label = Gtk.Label(xalign=.5)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_width_chars(1)
            label.set_max_width_chars(1)
            label.set_single_line_mode(True)
            label.set_no_show_all(True)
            label.get_style_context().add_class('media-track-'+style)
            self.meta_box.pack_start(label, False, False, 0)
            setattr(self, name+'_label', label)

        self.progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.content_box.pack_start(self.progress_box, False, False, 0)
        self.progress_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, .01)
        self.progress_scale.set_draw_value(False)
        self.progress_scale.get_style_context().add_class('media-progress-scale')
        self.progress_scale.get_accessible().set_name('Playback position')
        self.progress_scale.connect('button-press-event', self._on_seek_start)
        self.progress_scale.connect('button-release-event', self._on_seek_finish)
        self.progress_scale.connect('change-value', self._on_seek_change)
        self.progress_box.pack_start(self.progress_scale, False, False, 0)
        time_row = Gtk.Box()
        self.elapsed_label = Gtk.Label(xalign=0)
        self.total_label = Gtk.Label(xalign=1)
        for label in (self.elapsed_label, self.total_label):
            label.get_style_context().add_class('media-time-label')
            time_row.pack_start(label, True, True, 0)
        self.progress_box.pack_start(time_row, False, False, 0)
        self.progress_box.show_all()
        self.progress_box.set_no_show_all(True)
        self.controls = Gtk.Box(homogeneous=True)
        self.content_box.pack_start(self.controls, True, True, 0)
        for name, symbol, description, action in (
            ('prev', 'previous', 'Previous track', self.manager.previous_track),
            ('play', 'play', 'Play', self.manager.play_pause),
            ('next', 'next', 'Next track', self.manager.next_track)):
            button = Gtk.Button()
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.get_style_context().add_class('media-icon-button')
            button.set_tooltip_text(description)
            button.get_accessible().set_name(description)
            button.add(TransportIcon(symbol))
            button.connect('clicked', lambda _, callback=action: callback())
            self.controls.pack_start(button, True, True, 0)
            setattr(self, name+'_btn', button)
        self.content_box.connect('size-allocate', self._allocated)
        self.render()

    def _allocated(self, widget, allocation):
        # GTK drops resize requests issued during allocation; defer to the next turn.
        if self._layout_key != (allocation.width, self.compact) and not self._resize_source:
            self._resize_source = GLib.idle_add(self._relayout)

    def _relayout(self):
        self._resize_source = 0
        self._layout(self.content_box.get_allocated_width())
        return GLib.SOURCE_REMOVE

    def _layout(self, width):
        if width < 10:
            return
        key = (width, self.compact)
        if key == self._layout_key:
            return
        self._layout_key = key
        unit = width/268
        self.art_image.set_size_request(-1, round(width*(.62 if self.compact else .715)))
        self.art_image.radius = 26*unit
        self.meta_box.set_margin_top(round(10*unit))
        self.meta_box.set_margin_bottom(round(10*unit))
        for widget in (self.progress_box, self.controls):
            widget.set_margin_start(round(12*unit))
            widget.set_margin_end(round(12*unit))
        self.controls.set_size_request(-1, max(48, round((60 if self.compact else 66)*unit)))
        self.art_image.queue_draw()

    @staticmethod
    def _can_seek(snap):
        return bool(not snap.get('error') and snap.get('can_control') and snap.get('can_seek') and
                    snap.get('length', 0) > 0 and snap.get('track_id') and
                    snap['track_id'] != '/org/mpris/MediaPlayer2/TrackList/NoTrack')

    def _on_seek_start(self, scale, event):
        snap = self.manager.get_snapshot()
        if event.button == 1 and self._can_seek(snap):
            self.user_scrubbing = True
            self.seek_track = snap['track_id']
        return False

    def _seek(self, value, track_id=None):
        snap = self.manager.get_snapshot()
        if self._can_seek(snap) and (track_id is None or track_id == snap['track_id']):
            self.manager.set_position(snap['track_id'], max(0, min(1, value))*snap['length'])

    def _on_seek_finish(self, scale, event):
        if self.user_scrubbing:
            self._seek(scale.get_value(), self.seek_track)
        self.user_scrubbing = False
        self.seek_track = None
        return False

    def _on_seek_change(self, scale, scroll, value):
        # Keyboard and scroll-wheel changes must seek too; programmatic updates don't.
        if not self.user_scrubbing:
            self._seek(value)
        return False

    def render(self):
        prefs = load_preferences()
        self.compact = prefs.get('media_compact', False)
        self.scale = prefs['scale']*prefs.get('widget_scales', {}).get('media', 1)
        style_key = (self.scale, self.compact, effective_accent(prefs), prefs['opacity'], prefs['widget_borders'])
        if style_key != self._style_key:
            self._style_key = style_key
            css = media_css(self.scale, style_key[2], self.compact, prefs['opacity'])
            if not prefs['widget_borders']:
                css += '\n.media-widget-card { border-color: transparent; }'
            self.css.load_from_data(css.encode())
            self._layout_key = None
            self._layout(max(self.content_box.get_allocated_width(), round(268*self.scale)))
        snap = self.manager.get_snapshot()
        has_track = bool(snap.get('player_name') and snap.get('title') and not snap.get('error'))
        title = snap.get('title') if has_track else 'Nothing playing'
        for label, text, visible in (
            (self.title_label, title, True),
            (self.artist_label, snap.get('artist', '') if has_track else '', has_track),
            (self.album_label, snap.get('album', '') if has_track else '',
             has_track and prefs.get('media_show_album', True) and not self.compact)):
            label.set_text(text)
            label.set_tooltip_text(text or None)
            label.set_visible(bool(text) and visible)
        playing = snap.get('status') == 'Playing' and not snap.get('error')
        icon = self.play_btn.get_child()
        symbol = 'pause' if playing else 'play'
        if icon.symbol != symbol:
            icon.symbol = symbol
            icon.queue_draw()
        self.play_btn.set_tooltip_text('Pause' if playing else 'Play')
        self.play_btn.get_accessible().set_name('Pause' if playing else 'Play')
        can_control = bool(snap.get('can_control') and not snap.get('error'))
        self.prev_btn.set_sensitive(can_control and snap.get('can_prev', False))
        self.next_btn.set_sensitive(can_control and snap.get('can_next', False))
        self.play_btn.set_sensitive(can_control and snap.get('can_pause' if playing else 'can_play', False))
        self.progress_scale.set_sensitive(has_track and self._can_seek(snap))
        if not self.user_scrubbing:
            self.progress_scale.set_value(snap.get('progress', 0) if has_track else 0)
        length = snap.get('length', 0)
        self.elapsed_label.set_text(format_time(snap.get('position')) if has_track else '--:--')
        self.total_label.set_text(format_time(length) if has_track and length > 0 else '--:--')
        self.progress_box.set_visible(bool(prefs.get('media_show_progress', True) and has_track and length > 0))
        self.art_image.set_artwork(snap.get('art_path') if has_track else None)

    def close(self):
        if self._resize_source:
            GLib.source_remove(self._resize_source)
            self._resize_source = 0
        self.manager.stop()
        Gtk.StyleContext.remove_provider_for_screen(self.card.get_screen(), self.css)
