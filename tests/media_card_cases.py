"""Rendering and interaction regressions; run GTK cases on a real display."""
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
from media_card import MediaCard, cover_geometry, paint_cover
from preferences import normalize
from widget_styles import media_css


class CoverRenderingTests(unittest.TestCase):
    def test_aspect_fill_centers_square_portrait_and_landscape(self):
        for sw, sh in ((200, 200), (100, 200), (300, 100)):
            factor, x, y = cover_geometry(sw, sh, 140, 100)
            self.assertGreaterEqual(sw*factor, 140)
            self.assertGreaterEqual(sh*factor, 100)
            self.assertAlmostEqual(x*2+sw*factor, 140)
            self.assertAlmostEqual(y*2+sh*factor, 100)

    def test_cover_crops_center_and_has_transparent_rounded_corners(self):
        source = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 200)
        ctx = cairo.Context(source)
        for color, y, height in (((1, 0, 0), 0, 65), ((0, 1, 0), 65, 70), ((0, 0, 1), 135, 65)):
            ctx.set_source_rgb(*color); ctx.rectangle(0, y, 100, height); ctx.fill()
        pix = Gdk.pixbuf_get_from_surface(source, 0, 0, 100, 200)
        for dpi in (1, 2):
            target = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100*dpi, 70*dpi)
            target.set_device_scale(dpi, dpi)
            paint_cover(cairo.Context(target), pix, 100, 70, 15)
            output = Gdk.pixbuf_get_from_surface(target, 0, 0, 100*dpi, 70*dpi)
            data = output.get_pixels(); stride = output.get_rowstride()
            self.assertEqual(data[3], 0)
            center = 35*dpi*stride+50*dpi*4
            self.assertEqual(tuple(data[center:center+4]), (0, 255, 0, 255))
            top = 10*dpi*stride+50*dpi*4
            self.assertGreater(data[top+1], 245)  # Top/bottom source bands were cropped.

    def test_css_has_no_button_containers_and_has_keyboard_focus(self):
        css = media_css()
        self.assertIn('background: transparent; background-image: none; border: none;', css)
        self.assertIn('button.media-icon-button:focus', css)
        for removed in ('media-header', 'media-player-combo', 'media-status-footer', 'media-rect-btn'):
            self.assertNotIn(removed, css)


class FakeManager:
    def __init__(self):
        self.snapshot = dict(player_name='org.mpris.MediaPlayer2.test', title='A real title',
                             artist='An artist', album='An album', status='Paused', length=194,
                             position=17, progress=17/194, track_id='/track/1', can_control=True,
                             can_play=True, can_pause=True, can_prev=True, can_next=True, can_seek=True)
        self.actions = []
    def start(self): pass
    def stop(self): self.actions.append('stop')
    def get_snapshot(self): return dict(self.snapshot)
    def play_pause(self): self.actions.append('play_pause')
    def previous_track(self): self.actions.append('previous')
    def next_track(self): self.actions.append('next')
    def set_position(self, track_id, seconds): self.actions.append((track_id, seconds))


class Host:
    def card(self, parent, title):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.get_style_context().add_class('card')
        parent.pack_start(card, False, False, 0)
        return card


@unittest.skipUnless(Gtk.init_check()[0], 'GTK integration requires DISPLAY (run separately on :0)')
class MediaCardTests(unittest.TestCase):
    def setUp(self):
        self.prefs = normalize({'scale': 1.0, 'opacity': 1.0})
        self.patcher = patch('media_card.load_preferences', lambda: self.prefs)
        self.patcher.start()
        self.manager = FakeManager()
        self.window = Gtk.Window(title='Media card regression test')
        self.window.set_resizable(False)
        self.root = Gtk.Box()
        self.window.add(self.root)
        self.media = MediaCard(Host(), self.root, self.manager)
        self.media.card.set_size_request(290, -1)
        self.window.show_all()
        self.drain()

    def tearDown(self):
        self.media.close()
        self.window.destroy()
        self.drain()
        self.patcher.stop()

    def drain(self):
        deadline = time.monotonic()+.12
        while time.monotonic() < deadline:
            while Gtk.events_pending(): Gtk.main_iteration_do(False)
            time.sleep(.005)

    def test_no_header_selector_or_footer(self):
        self.assertEqual(self.media.content_box.get_children(),
                         [self.media.art_image, self.media.meta_box, self.media.progress_box, self.media.controls])
        for name in ('header_box', 'player_selector', 'mode_btn', 'status_footer'):
            self.assertFalse(hasattr(self.media, name))

    def test_metadata_and_visible_timeline(self):
        self.assertEqual(self.media.title_label.get_text(), 'A real title')
        self.assertEqual(self.media.artist_label.get_text(), 'An artist')
        self.assertEqual(self.media.album_label.get_text(), 'An album')
        self.assertEqual(self.media.elapsed_label.get_text(), '0:17')
        self.assertEqual(self.media.total_label.get_text(), '3:14')
        self.assertTrue(self.media.progress_scale.is_visible())
        self.assertTrue(self.media.elapsed_label.is_visible())

    def test_play_pause_icons_and_real_actions(self):
        self.assertEqual(self.media.play_btn.get_child().symbol, 'play')
        self.manager.snapshot['status'] = 'Playing'; self.media.render()
        self.assertEqual(self.media.play_btn.get_child().symbol, 'pause')
        self.assertEqual(self.media.play_btn.get_accessible().get_name(), 'Pause')
        for button in (self.media.prev_btn, self.media.play_btn, self.media.next_btn):
            self.assertIn('media-icon-button', button.get_style_context().list_classes())
            button.clicked()
        self.assertEqual(self.manager.actions, ['previous', 'play_pause', 'next'])
        self.manager.snapshot['can_pause'] = False; self.media.render()
        self.assertFalse(self.media.play_btn.get_sensitive())

    def test_missing_and_corrupt_art_preserve_metadata_and_dimensions(self):
        before = self.media.art_image.get_allocation()
        for path in (None, '/nonexistent/art.jpg', __file__):
            self.manager.snapshot['art_path'] = path; self.media.render(); self.drain()
            self.assertIsNone(self.media.art_image.pixbuf)
            self.assertEqual(self.media.title_label.get_text(), 'A real title')
            self.assertEqual(self.media.art_image.get_allocated_height(), before.height)

    def test_disconnected_clears_art_metadata_and_disables_controls(self):
        self.manager.snapshot = {}; self.media.render(); self.window.show_all(); self.drain()
        self.assertEqual(self.media.title_label.get_text(), 'Nothing playing')
        self.assertFalse(self.media.artist_label.get_visible())
        self.assertFalse(self.media.album_label.get_visible())
        self.assertFalse(self.media.progress_box.get_visible())
        self.assertEqual(self.media.elapsed_label.get_text(), '--:--')
        for button in (self.media.prev_btn, self.media.play_btn, self.media.next_btn, self.media.progress_scale):
            self.assertFalse(button.get_sensitive())
        self.media._seek(.5)
        self.assertEqual(self.manager.actions, [])

    def test_unknown_duration_and_no_seek_capability(self):
        self.manager.snapshot['can_seek'] = False; self.media.render()
        self.assertFalse(self.media.progress_scale.get_sensitive())
        self.assertTrue(self.media.progress_box.get_visible())
        self.media._seek(.5); self.assertEqual(self.manager.actions, [])
        self.manager.snapshot['length'] = 0; self.media.render()
        self.assertEqual(self.media.total_label.get_text(), '--:--')
        self.assertFalse(self.media.progress_box.get_visible())

    def test_mouse_keyboard_seek_and_track_change_during_drag(self):
        self.media._on_seek_start(self.media.progress_scale, SimpleNamespace(button=1))
        self.media.progress_scale.set_value(.5)
        self.media._on_seek_finish(self.media.progress_scale, SimpleNamespace(button=1))
        self.assertEqual(self.manager.actions[-1], ('/track/1', 97))
        self.media._on_seek_change(self.media.progress_scale, Gtk.ScrollType.STEP_FORWARD, .25)
        self.assertEqual(self.manager.actions[-1], ('/track/1', 48.5))
        self.media._on_seek_start(self.media.progress_scale, SimpleNamespace(button=1))
        self.manager.snapshot['track_id'] = '/track/2'
        self.media._on_seek_finish(self.media.progress_scale, SimpleNamespace(button=1))
        self.assertEqual(len(self.manager.actions), 2)

    def test_responsive_landscape_art_and_compact_mode(self):
        for scale in (.8, 1.8, 2.5):
            for compact in (False, True):
                self.prefs.update(scale=scale, media_compact=compact)
                self.media.card.set_size_request(round(290*scale), -1)
                self.media.render(); self.window.resize(round(290*scale), 1); self.drain()
                art = self.media.art_image.get_allocation()
                self.assertAlmostEqual(art.height/art.width, .62 if compact else .715, delta=.02)
                self.assertGreaterEqual(self.media.play_btn.get_allocated_height(), 44)
                self.assertEqual(self.media.album_label.get_visible(), not compact)
                self.assertLess(art.height, self.media.card.get_allocated_height()*.6)

    def test_long_metadata_ellipsizes_without_expanding_card(self):
        before = self.media.card.get_allocated_width()
        self.manager.snapshot.update(title='Long title '*100, artist='Long artist '*100, album='Long album '*100)
        self.media.render(); self.drain()
        self.assertEqual(self.media.card.get_allocated_width(), before)

    def test_stale_snapshot_after_bus_error_is_not_actionable(self):
        self.manager.snapshot['error'] = 'Session bus disconnected'
        self.media.render()
        self.media._seek(.5)
        self.assertEqual(self.manager.actions, [])
        self.assertEqual(self.media.title_label.get_text(), 'Nothing playing')
        self.assertFalse(self.media.play_btn.get_sensitive())
        self.assertFalse(self.media.progress_scale.get_sensitive())
        self.assertFalse(self.media.progress_box.get_visible())

    def test_visibility_preferences_survive_show_all(self):
        self.prefs.update(media_show_album=False, media_show_progress=False)
        self.media.render(); self.window.show_all()
        self.assertFalse(self.media.album_label.get_visible())
        self.assertFalse(self.media.progress_box.get_visible())


if __name__ == '__main__':
    unittest.main()
