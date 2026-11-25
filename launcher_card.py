"""Smart Application Dock and Search card for Neon Studio desktop widgets.

Features:
- Dark charcoal aesthetic (#1E1E20) matching the reference mockup
- Modern "Launcher" header with four-square app grid icon
- Integrated search bar with search icon, "Search applications..." placeholder, and Esc badge
- Evenly spaced horizontal row of native high-res application icons
- Centered labels with 2-line word wrapping to avoid mid-word truncation
- Instant fuzzy search with Enter-to-launch and Escape-to-clear shortcuts
- Intelligent pagination concealed when all applications fit
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

from app_launcher import AppLauncherModel, AppEntry
from preferences import load as load_preferences, update as update_preferences


class LauncherCard:
    def __init__(self, host, parent, model=None, page_size=6):
        self.host = host
        self.model = model or AppLauncherModel()
        self.page_size = page_size
        self.current_page = 0
        self.search_query = ""
        self.displayed_apps = []
        self.scale = 1.0

        prefs = load_preferences()
        self.custom_favorites = prefs.get("launcher_favorites", None)
        self.icon_size = prefs.get("launcher_icon_size", 36)
        self.orientation = prefs.get("launcher_orientation", "horizontal")

        # Container card
        self.card = host.card(parent, "")
        self.card.get_style_context().add_class("launcher-dock-card")
        self.card.get_accessible().set_name("Application Launcher Dock")

        # Main box
        self.box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL if self.orientation == "horizontal" else Gtk.Orientation.HORIZONTAL,
            spacing=10,
        )
        self.card.pack_start(self.box, True, True, 0)

        # Header title: Four-square grid icon + "Launcher" in modern medium typography
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.box.pack_start(header, False, False, 0)

        grid_icon = Gtk.Image.new_from_icon_name("view-app-grid-symbolic", Gtk.IconSize.MENU)
        grid_icon.get_style_context().add_class("launcher-title-icon")
        header.pack_start(grid_icon, False, False, 0)

        title = Gtk.Label(label="Launcher")
        title.get_style_context().add_class("launcher-title-label")
        title.set_xalign(0.0)
        header.pack_start(title, False, False, 0)

        # Search field row: Search icon + entry + "Esc" badge
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_box.get_style_context().add_class("launcher-search-box")
        self.box.pack_start(search_box, False, False, 0)

        search_icon = Gtk.Image.new_from_icon_name("system-search-symbolic", Gtk.IconSize.MENU)
        search_icon.get_style_context().add_class("launcher-search-icon")
        search_box.pack_start(search_icon, False, False, 0)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search applications...")
        self.search_entry.get_style_context().add_class("launcher-search-entry-inner")
        self.search_entry.set_has_frame(False)
        self.search_entry.connect("changed", self._on_search_changed)
        self.search_entry.connect("key-press-event", self._on_search_key_press)
        search_box.pack_start(self.search_entry, True, True, 0)

        self.esc_badge = Gtk.Label(label="Esc")
        self.esc_badge.get_style_context().add_class("launcher-esc-badge")
        search_box.pack_end(self.esc_badge, False, False, 0)

        # Dock icons row
        self.dock_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL if self.orientation == "horizontal" else Gtk.Orientation.VERTICAL,
            spacing=6,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        self.box.pack_start(self.dock_row, True, True, 0)

        # Bottom navigation row: Prev, Page indicator, Next (only shown when multi-page)
        self.nav_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.CENTER)
        self.nav_row.set_no_show_all(True)
        self.box.pack_start(self.nav_row, False, False, 0)

        self.prev_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.MENU)
        self.prev_btn.get_style_context().add_class("round-action")
        self.prev_btn.set_tooltip_text("Previous apps page")
        self.prev_btn.connect("clicked", lambda _: self._change_page(-1))
        self.nav_row.pack_start(self.prev_btn, False, False, 0)

        self.page_label = Gtk.Label(label="1/1")
        self.page_label.get_style_context().add_class("small")
        self.nav_row.pack_start(self.page_label, False, False, 0)

        self.next_btn = Gtk.Button.new_from_icon_name("go-next-symbolic", Gtk.IconSize.MENU)
        self.next_btn.get_style_context().add_class("round-action")
        self.next_btn.set_tooltip_text("Next apps page")
        self.next_btn.connect("clicked", lambda _: self._change_page(1))
        self.nav_row.pack_start(self.next_btn, False, False, 0)

        self.status_label = Gtk.Label(label="")
        self.status_label.get_style_context().add_class("small")
        self.status_label.set_no_show_all(True)
        self.box.pack_start(self.status_label, False, False, 0)

        self.refresh()

    def _on_search_changed(self, entry):
        self.search_query = entry.get_text().strip()
        self.current_page = 0
        self.refresh()

    def _on_search_key_press(self, entry, event):
        keyval = event.keyval
        if keyval == Gdk.KEY_Escape:
            entry.set_text("")
            self.search_query = ""
            self.current_page = 0
            self.refresh()
            return True
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if self.displayed_apps:
                self._launch_app(self.displayed_apps[0], event.time)
                entry.set_text("")
                self.search_query = ""
                self.refresh()
            return True
        return False

    def _change_page(self, delta):
        total_pages = max(1, (len(self.displayed_apps) + self.page_size - 1) // self.page_size)
        new_page = max(0, min(total_pages - 1, self.current_page + delta))
        if new_page != self.current_page:
            self.current_page = new_page
            self._render_icons()

    def _launch_app(self, app_entry, timestamp=0):
        ok, msg = self.model.launch(app_entry, timestamp)
        self.status_label.set_text(msg)
        self.status_label.show()
        def clear_status():
            self.status_label.set_text("")
            self.status_label.hide()
            return False
        GLib.timeout_add_seconds(3, clear_status)

    def refresh(self):
        """Update app lists based on search or favorites."""
        if self.search_query:
            self.displayed_apps = self.model.search(self.search_query, limit=24)
            if not self.displayed_apps:
                self.status_label.set_text("No matching applications found")
                self.status_label.show()
            else:
                self.status_label.set_text(f"{len(self.displayed_apps)} apps found")
                self.status_label.show()
        else:
            self.displayed_apps = self.model.get_favorites(self.custom_favorites)
            self.status_label.set_text("")
            self.status_label.hide()

        total_pages = max(1, (len(self.displayed_apps) + self.page_size - 1) // self.page_size)
        self.current_page = max(0, min(total_pages - 1, self.current_page))
        self._render_icons()

    def _render_icons(self):
        # Clear existing buttons
        for child in self.dock_row.get_children():
            self.dock_row.remove(child)

        total_pages = max(1, (len(self.displayed_apps) + self.page_size - 1) // self.page_size)
        self.page_label.set_text(f"{self.current_page + 1}/{total_pages}")
        self.prev_btn.set_sensitive(self.current_page > 0)
        self.next_btn.set_sensitive(self.current_page < total_pages - 1)
        if total_pages > 1:
            self.nav_row.show_all()
        else:
            self.nav_row.hide()

        start_idx = self.current_page * self.page_size
        page_items = self.displayed_apps[start_idx : start_idx + self.page_size]

        cell_width = round(64 * self.scale)

        for app in page_items:
            btn = Gtk.Button()
            btn.get_style_context().add_class("launcher-app-btn")
            btn.set_size_request(cell_width, -1)
            btn.set_tooltip_text(f"{app.display_name}\n{app.description}" if app.description else app.display_name)
            btn.get_accessible().set_name(app.display_name)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.set_halign(Gtk.Align.CENTER)

            icon = Gtk.Image()
            gicon = app.app_info.get_icon()
            if gicon:
                icon.set_from_gicon(gicon, Gtk.IconSize.LARGE_TOOLBAR)
                icon.set_pixel_size(self.icon_size)
            else:
                icon.set_from_icon_name(app.icon_name, Gtk.IconSize.LARGE_TOOLBAR)
                icon.set_pixel_size(self.icon_size)

            box.pack_start(icon, False, False, 0)

            # Format display label cleanly: 2-line word wrapping without mid-word breaks
            lbl = Gtk.Label(label=app.display_name)
            lbl.get_style_context().add_class("launcher-app-label")
            lbl.set_line_wrap(True)
            lbl.set_line_wrap_mode(Pango.WrapMode.WORD)
            lbl.set_max_width_chars(11)
            lbl.set_justify(Gtk.Justification.CENTER)
            lbl.set_xalign(0.5)
            box.pack_start(lbl, False, False, 0)

            btn.add(box)
            btn.connect("clicked", lambda _, chosen=app: self._launch_app(chosen))
            self.dock_row.pack_start(btn, False, False, 0)

        self.dock_row.show_all()
