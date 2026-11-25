"""File Search desktop widget card for Neon Studio."""
import os
from pathlib import Path
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from file_search import FileSearchModel, file_icon
from preferences import load as load_preferences


class FileSearchCard:
    def __init__(self, host, parent, model=None):
        self.host = host
        prefs = load_preferences()
        search_root = prefs.get("file_search_root", str(Path.home() / "Documents"))
        self.model = model or FileSearchModel(root=search_root)
        self.last_results = None
        self.last_status = None
        self.timer_id = None

        # Container card
        self.card = host.card(parent, "")
        self.card.get_style_context().add_class("file-search-card")
        self.card.get_accessible().set_name("File Search")

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.card.pack_start(self.box, True, True, 0)

        # Header row: Title + folder path indicator + refresh button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.box.pack_start(header, False, False, 0)

        title = Gtk.Label(label="FILE SEARCH")
        title.get_style_context().add_class("heading")
        title.set_xalign(0.0)
        header.pack_start(title, True, True, 0)

        self.refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.refresh_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.refresh_btn.set_tooltip_text(f"Refresh index ({self.model.root})")
        self.refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.pack_end(self.refresh_btn, False, False, 0)

        # Search Entry
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Find files by name… (Esc to clear)")
        self.entry.get_style_context().add_class("launcher-search-entry")
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "system-search-symbolic")
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "edit-clear-symbolic")
        self.entry.connect("changed", self._on_entry_changed)
        self.entry.connect("icon-press", self._on_icon_press)
        self.entry.connect("key-press-event", self._on_key_press)
        self.box.pack_start(self.entry, False, False, 0)

        # Results container
        self.results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.box.pack_start(self.results_box, False, False, 0)

        # Status label
        self.status_label = Gtk.Label(label="Indexing files…")
        self.status_label.get_style_context().add_class("small")
        self.status_label.set_xalign(0.0)
        self.status_label.set_line_wrap(True)
        self.status_label.set_max_width_chars(36)
        self.box.pack_start(self.status_label, False, False, 0)

        self.timer_id = GLib.timeout_add(300, self._poll_updates)

    def _on_refresh_clicked(self, _btn):
        self.model.refresh()
        self.status_label.set_text("Re-indexing files…")

    def _on_entry_changed(self, entry):
        text = entry.get_text()
        self.model.set_query(text)

    def _on_icon_press(self, entry, icon_pos, _event):
        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            entry.set_text("")
            self.model.set_query("")

    def _on_key_press(self, _entry, event):
        key = Gdk.keyval_name(event.keyval)
        if key == "Escape":
            self.entry.set_text("")
            self.model.set_query("")
            return True
        if key in ("Return", "KP_Enter"):
            results, _status, _busy, _total = self.model.view()
            if results:
                self.model.launch(results[0])
            return True
        return False

    def _poll_updates(self):
        results, status, busy, _total = self.model.view()
        self.refresh_btn.set_sensitive(not busy)

        if status != self.last_status:
            self.status_label.set_text(status)
            self.last_status = status

        if results != self.last_results:
            self.last_results = results
            self._render_results(results)

        return GLib.SOURCE_CONTINUE

    def _render_results(self, results):
        for child in self.results_box.get_children():
            self.results_box.remove(child)

        if not results:
            return

        for path in results:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.get_style_context().add_class("file-search-row")

            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_tooltip_text(path)
            btn.connect("clicked", lambda _, p=path: self.model.launch(p))

            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            icon_name = file_icon(path)
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
            btn_box.pack_start(icon, False, False, 0)

            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            name_lbl = Gtk.Label(label=os.path.basename(path))
            name_lbl.set_xalign(0.0)
            name_lbl.set_ellipsize(3)
            name_lbl.set_max_width_chars(28)
            text_box.pack_start(name_lbl, False, False, 0)

            try:
                rel = os.path.relpath(os.path.dirname(path), self.model.root)
            except ValueError:
                rel = os.path.dirname(path)
            rel_lbl = Gtk.Label(label=rel if rel != "." else "")
            rel_lbl.set_xalign(0.0)
            rel_lbl.get_style_context().add_class("small")
            rel_lbl.set_ellipsize(3)
            rel_lbl.set_max_width_chars(28)
            text_box.pack_start(rel_lbl, False, False, 0)

            btn_box.pack_start(text_box, True, True, 0)
            btn.add(btn_box)
            row.pack_start(btn, True, True, 0)

            # Folder button
            folder_btn = Gtk.Button.new_from_icon_name("folder-symbolic", Gtk.IconSize.BUTTON)
            folder_btn.set_relief(Gtk.ReliefStyle.NONE)
            folder_btn.set_tooltip_text(f"Open containing folder: {os.path.dirname(path)}")
            folder_btn.connect("clicked", lambda _, p=path: self.model.launch_folder(p))
            row.pack_end(folder_btn, False, False, 0)

            self.results_box.pack_start(row, False, False, 0)

        self.results_box.show_all()

    def close(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
        self.model.close()
