"""Thread-safe MPRIS media player provider for Neon Studio.

Discovers media players (Spotify, VLC, browsers, etc.) exposing org.mpris.MediaPlayer2
over the session D-Bus, queries playback state, metadata, and position, and dispatches
playback/volume/seek controls without blocking the GTK UI thread.
"""
import hashlib
from pathlib import Path
import threading
import time
import urllib.parse
import urllib.request

PREFIX = "org.mpris.MediaPlayer2."
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
OBJECT_PATH = "/org/mpris/MediaPlayer2"
ARTWORK_CACHE = Path(__file__).resolve().parent / "state" / "cache" / "artwork"


class MprisSessionBus:
    """Session D-Bus wrapper using Gio with timeout and error handling."""

    def __init__(self):
        from gi.repository import Gio, GLib
        self.Gio = Gio
        self.GLib = GLib
        self.cancellable = Gio.Cancellable()
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, self.cancellable)

    def call(self, destination, path, interface, method, signature=None, args=(), timeout_ms=1500):
        params = self.GLib.Variant(signature, args) if signature else None
        reply = self.bus.call_sync(
            destination,
            path,
            interface,
            method,
            params,
            None,
            self.Gio.DBusCallFlags.NO_AUTO_START,
            timeout_ms,
            self.cancellable,
        )
        return reply.unpack()

    def list_players(self):
        """Return list of active MPRIS service names."""
        try:
            names = self.call(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "ListNames",
            )[0]
            return sorted(n for n in names if n.startswith(PREFIX))
        except Exception:
            return []

    def get_owner(self, name):
        """Resolve a well-known service name to its unique connection name."""
        try:
            return self.call(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "GetNameOwner",
                "(s)",
                (name,),
            )[0]
        except Exception:
            return None

    def get_player_properties(self, destination):
        """Retrieve all properties from org.mpris.MediaPlayer2.Player."""
        try:
            return self.call(
                destination,
                OBJECT_PATH,
                "org.freedesktop.DBus.Properties",
                "GetAll",
                "(s)",
                (PLAYER_INTERFACE,),
            )[0]
        except Exception:
            return {}

    def command(self, destination, method, signature=None, args=()):
        """Execute a method on the Player interface."""
        self.call(destination, OBJECT_PATH, PLAYER_INTERFACE, method, signature, args)

    def set_property(self, destination, prop_name, variant_type, value):
        """Set a property on the Player interface via org.freedesktop.DBus.Properties."""
        self.call(
            destination,
            OBJECT_PATH,
            "org.freedesktop.DBus.Properties",
            "Set",
            "(ssv)",
            (PLAYER_INTERFACE, prop_name, self.GLib.Variant(variant_type, value)),
        )

    def close(self):
        if hasattr(self, "cancellable") and self.cancellable:
            self.cancellable.cancel()


def format_time(seconds):
    """Format seconds into MM:SS or HH:MM:SS."""
    if seconds is None or seconds < 0:
        return "--:--"
    total_sec = int(round(seconds))
    mins, sec = divmod(total_sec, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{sec:02d}"
    return f"{mins}:{sec:02d}"


def display_name(player_name):
    """Derive user-friendly player title (e.g., 'org.mpris.MediaPlayer2.spotify' -> 'Spotify')."""
    if player_name.startswith(PREFIX):
        raw = player_name[len(PREFIX):]
        # Drop instance suffixes like .instance1234
        name = raw.split(".")[0]
        return name.replace("-", " ").replace("_", " ").title()
    return player_name


class MediaPlayerManager:
    """Thread-safe manager monitoring MPRIS players and caching track state."""

    def __init__(self, bus_factory=MprisSessionBus):
        self._bus_factory = bus_factory
        self._bus = None
        self._lock = threading.Lock()
        self._wake_event = threading.Event()
        self._stop_event = threading.Event()
        self._worker_thread = None

        self._pinned_player = None
        self._selected_player = None
        self._available_players = []
        self._snapshot = {
            "player_name": "",
            "player_display": "No Media Player",
            "players": [],
            "status": "Stopped",
            "title": "",
            "artist": "",
            "album": "",
            "art_url": "",
            "art_path": None,
            "position": 0.0,
            "length": 0.0,
            "progress": 0.0,
            "volume": 1.0,
            "can_control": False,
            "can_play": False,
            "can_pause": False,
            "can_next": False,
            "can_prev": False,
            "can_seek": False,
            "error": "",
        }
        self._pending_commands = []
        self._artwork_cache_dir = ARTWORK_CACHE
        self._artwork_cache_dir.mkdir(parents=True, exist_ok=True)

    def start(self):
        """Start background polling thread."""
        with self._lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._stop_event.clear()
                self._worker_thread = threading.Thread(
                    target=self._run, name="neon-media-worker", daemon=True
                )
                self._worker_thread.start()

    def stop(self):
        """Stop background worker."""
        self._stop_event.set()
        self._wake_event.set()
        with self._lock:
            if self._bus and hasattr(self._bus, "close"):
                try:
                    self._bus.close()
                except Exception:
                    pass
                self._bus = None

    def get_snapshot(self):
        """Return latest thread-safe playback snapshot."""
        with self._lock:
            return dict(self._snapshot)

    def select_player(self, player_name):
        """Pin a specific player or None to follow active player automatically."""
        with self._lock:
            self._pinned_player = player_name
        self._wake_event.set()

    def play_pause(self):
        self._queue_command("PlayPause")

    def play(self):
        self._queue_command("Play")

    def pause(self):
        self._queue_command("Pause")

    def next_track(self):
        self._queue_command("Next")

    def previous_track(self):
        self._queue_command("Previous")

    def seek(self, offset_seconds):
        offset_micros = int(offset_seconds * 1_000_000)
        self._queue_command("Seek", "(x)", (offset_micros,))

    def set_position(self, track_id, position_seconds):
        pos_micros = int(position_seconds * 1_000_000)
        self._queue_command("SetPosition", "(ox)", (track_id, pos_micros))

    def set_volume(self, volume):
        vol = max(0.0, min(1.0, float(volume)))
        self._queue_command("__set_property__", "Volume", ("d", vol))

    def _queue_command(self, method, signature=None, args=()):
        with self._lock:
            owner = self._selected_player.get("owner") if self._selected_player else None
            if owner:
                self._pending_commands.append((owner, method, signature, args))
        self._wake_event.set()

    def _resolve_artwork(self, art_url):
        """Resolve artUrl (file:// or http(s)://) to a local cached path."""
        if not art_url:
            return None
        parsed = urllib.parse.urlparse(art_url)
        if parsed.scheme == "file":
            local_path = Path(urllib.parse.unquote(parsed.path))
            return local_path if local_path.is_file() else None
        if not parsed.scheme and Path(art_url).is_file():
            return Path(art_url)
        if parsed.scheme in ("http", "https"):
            url_hash = hashlib.sha256(art_url.encode()).hexdigest()[:24]
            target = self._artwork_cache_dir / f"{url_hash}.jpg"
            if target.is_file():
                return target
            try:
                req = urllib.request.Request(
                    art_url, headers={"User-Agent": "NeonStudio/2.0 MediaWidget"}
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = resp.read(8 * 1024 * 1024)
                    if data:
                        target.write_bytes(data)
                        return target
            except Exception:
                return None
        return None

    def _run(self):
        while not self._stop_event.is_set():
            self._wake_event.clear()
            try:
                if self._bus is None:
                    self._bus = self._bus_factory()

                # Process queued commands first
                with self._lock:
                    commands = list(self._pending_commands)
                    self._pending_commands.clear()

                for owner, method, sig, args in commands:
                    if self._stop_event.is_set():
                        break
                    try:
                        if method == "__set_property__":
                            prop_name, var_type, val = sig, args[0], args[1]
                            self._bus.set_property(owner, prop_name, var_type, val)
                        else:
                            self._bus.command(owner, method, sig, args)
                    except Exception:
                        pass

                # Discover players
                player_names = self._bus.list_players()
                discovered = []
                for name in player_names:
                    owner = self._bus.get_owner(name)
                    if not owner:
                        continue
                    props = self._bus.get_player_properties(owner)
                    discovered.append({
                        "name": name,
                        "owner": owner,
                        "display": display_name(name),
                        "status": props.get("PlaybackStatus", "Stopped"),
                        "props": props,
                    })

                # Determine active player
                active = None
                with self._lock:
                    pinned = self._pinned_player

                if pinned:
                    for p in discovered:
                        if p["name"] == pinned or p["display"].lower() == pinned.lower():
                            active = p
                            break

                if not active and discovered:
                    # Prefer currently Playing, then Paused, then first available
                    active = min(
                        discovered,
                        key=lambda p: (
                            0 if p["status"] == "Playing" else 1 if p["status"] == "Paused" else 2,
                            p["name"],
                        ),
                    )

                with self._lock:
                    self._selected_player = active
                    self._available_players = discovered

                # Build snapshot
                if active:
                    props = active["props"]
                    meta = props.get("Metadata", {})
                    title = meta.get("xesam:title") or ("Unknown track" if meta.get("xesam:url") else "")
                    artist_data = meta.get("xesam:artist") or []
                    artist = (
                        ", ".join(artist_data)
                        if isinstance(artist_data, (list, tuple))
                        else str(artist_data)
                    )
                    album = meta.get("xesam:album") or ""
                    art_url = meta.get("mpris:artUrl") or ""
                    track_id = meta.get("mpris:trackid") or ""
                    length_us = meta.get("mpris:length") or 0
                    length_sec = length_us / 1_000_000.0 if length_us > 0 else 0.0

                    pos_us = props.get("Position") or 0
                    pos_sec = pos_us / 1_000_000.0 if pos_us > 0 else 0.0
                    progress = (pos_sec / length_sec) if length_sec > 0 else 0.0
                    progress = max(0.0, min(1.0, progress))

                    vol = props.get("Volume")
                    volume = float(vol) if vol is not None else 1.0
                    volume = max(0.0, min(1.0, volume))

                    status = active["status"]
                    can_control = bool(props.get("CanControl", True))
                    can_play = bool(props.get("CanPlay", True))
                    can_pause = bool(props.get("CanPause", True))
                    can_next = bool(props.get("CanGoNext", True))
                    can_prev = bool(props.get("CanGoPrevious", True))
                    can_seek = bool(props.get("CanSeek", False))

                    art_path = self._resolve_artwork(art_url)

                    new_snapshot = {
                        "player_name": active["name"],
                        "player_display": active["display"],
                        "players": [p["display"] for p in discovered],
                        "status": status,
                        "title": title,
                        "artist": artist,
                        "album": album,
                        "art_url": art_url,
                        "art_path": art_path,
                        "track_id": track_id,
                        "position": pos_sec,
                        "length": length_sec,
                        "progress": progress,
                        "volume": volume,
                        "can_control": can_control,
                        "can_play": can_play,
                        "can_pause": can_pause,
                        "can_next": can_next,
                        "can_prev": can_prev,
                        "can_seek": can_seek,
                        "error": "",
                    }
                else:
                    new_snapshot = {
                        "player_name": "",
                        "player_display": "No Media Player",
                        "players": [],
                        "status": "Stopped",
                        "title": "Nothing playing",
                        "artist": "Open Spotify, VLC, or a browser",
                        "album": "",
                        "art_url": "",
                        "art_path": None,
                        "track_id": "",
                        "position": 0.0,
                        "length": 0.0,
                        "progress": 0.0,
                        "volume": 1.0,
                        "can_control": False,
                        "can_play": False,
                        "can_pause": False,
                        "can_next": False,
                        "can_prev": False,
                        "can_seek": False,
                        "error": "",
                    }

                with self._lock:
                    self._snapshot = new_snapshot

            except Exception as exc:
                with self._lock:
                    self._snapshot["error"] = str(exc)
            finally:
                # Sleep 1s or until signaled by user interaction
                self._wake_event.wait(1.0)
