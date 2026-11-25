"""Automated unit tests for media_player.py MPRIS integration."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from media_player import MediaPlayerManager, display_name, format_time


class MockMprisBus:
    def __init__(self, names=None, properties=None):
        self._names = names if names is not None else ["org.mpris.MediaPlayer2.spotify"]
        self._properties = properties or {
            ":1.42": {
                "PlaybackStatus": "Playing",
                "CanControl": True,
                "CanPlay": True,
                "CanPause": True,
                "CanGoNext": True,
                "CanGoPrevious": True,
                "CanSeek": True,
                "Position": 45000000,
                "Volume": 0.85,
                "Metadata": {
                    "xesam:title": "Neon Dreams",
                    "xesam:artist": ["Synth Wave", "Retrorunner"],
                    "xesam:album": "Midnight City",
                    "mpris:artUrl": "file:///tmp/album.jpg",
                    "mpris:length": 180000000,
                    "mpris:trackid": "/org/mpris/track/1",
                },
            }
        }
        self.commands_received = []
        self.props_set = []

    def list_players(self):
        return list(self._names)

    def get_owner(self, name):
        return ":1.42" if name in self._names else None

    def get_player_properties(self, destination):
        return self._properties.get(destination, {})

    def command(self, destination, method, signature=None, args=()):
        self.commands_received.append((destination, method, signature, args))

    def set_property(self, destination, prop_name, var_type, value):
        self.props_set.append((destination, prop_name, var_type, value))

    def close(self):
        pass


class TestMediaPlayer(unittest.TestCase):
    def test_format_time(self):
        self.assertEqual(format_time(0), "0:00")
        self.assertEqual(format_time(65), "1:05")
        self.assertEqual(format_time(3665), "1:01:05")
        self.assertEqual(format_time(-1), "--:--")
        self.assertEqual(format_time(None), "--:--")

    def test_display_name(self):
        self.assertEqual(display_name("org.mpris.MediaPlayer2.spotify"), "Spotify")
        self.assertEqual(display_name("org.mpris.MediaPlayer2.vlc.instance1234"), "Vlc")
        self.assertEqual(display_name("org.mpris.MediaPlayer2.firefox"), "Firefox")

    def test_manager_snapshot_with_mock_bus(self):
        mock_bus = MockMprisBus()
        manager = MediaPlayerManager(bus_factory=lambda: mock_bus)

        # Trigger one iteration of the internal logic synchronously or via start
        manager.start()
        # Wait briefly for thread iteration
        import time
        time.sleep(0.15)

        snap = manager.get_snapshot()
        manager.stop()

        self.assertEqual(snap["player_display"], "Spotify")
        self.assertEqual(snap["status"], "Playing")
        self.assertEqual(snap["title"], "Neon Dreams")
        self.assertIn("Synth Wave", snap["artist"])
        self.assertEqual(snap["album"], "Midnight City")
        self.assertAlmostEqual(snap["position"], 45.0, places=1)
        self.assertAlmostEqual(snap["length"], 180.0, places=1)
        self.assertAlmostEqual(snap["progress"], 0.25, places=2)
        self.assertAlmostEqual(snap["volume"], 0.85, places=2)
        self.assertTrue(snap["can_control"])
        self.assertTrue(snap["can_seek"])

    def test_manager_controls_dispatch_to_bus(self):
        mock_bus = MockMprisBus()
        manager = MediaPlayerManager(bus_factory=lambda: mock_bus)
        manager.start()
        import time
        time.sleep(0.15)

        manager.play_pause()
        manager.next_track()
        manager.previous_track()
        manager.seek(15.0)
        manager.set_volume(0.5)

        time.sleep(0.15)
        manager.stop()

        methods = [cmd[1] for cmd in mock_bus.commands_received]
        self.assertIn("PlayPause", methods)
        self.assertIn("Next", methods)
        self.assertIn("Previous", methods)
        self.assertIn("Seek", methods)

        self.assertEqual(len(mock_bus.props_set), 1)
        self.assertEqual(mock_bus.props_set[0][1], "Volume")
        self.assertEqual(mock_bus.props_set[0][3], 0.5)

    def test_player_without_track_has_no_fabricated_metadata(self):
        import time
        bus = MockMprisBus(properties={":1.42": {"PlaybackStatus": "Stopped", "Metadata": {}}})
        manager = MediaPlayerManager(bus_factory=lambda: bus)
        manager.start()
        try:
            time.sleep(.15)
            snap = manager.get_snapshot()
            self.assertEqual(snap["title"], "")
            self.assertEqual(snap["artist"], "")
            self.assertEqual(snap["length"], 0)
            self.assertIsNone(snap["art_path"])
        finally:
            manager.stop()

    def test_empty_state_when_no_players(self):
        mock_bus = MockMprisBus(names=[])
        manager = MediaPlayerManager(bus_factory=lambda: mock_bus)
        manager.start()
        import time
        time.sleep(0.15)

        snap = manager.get_snapshot()
        manager.stop()

        self.assertEqual(snap["player_display"], "No Media Player")
        self.assertEqual(snap["status"], "Stopped")
        self.assertEqual(snap["title"], "Nothing playing")
        self.assertFalse(snap["can_control"])


if __name__ == "__main__":
    unittest.main()
