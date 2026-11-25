"""System and Hardware device controls for Neon Studio.

Provides:
- Volume control and mute toggle via pactl / wpctl.
- Screen brightness control via GNOME SettingsDaemon Power DBus.
- System metrics (CPU %, RAM %, Disk usage %).
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Tuple


class AudioController:
    """Controls default audio sink volume and mute status via pactl or wpctl."""

    def __init__(self):
        self.cmd = shutil.which("pactl") or shutil.which("wpctl")
        self.is_pulse = os.path.basename(self.cmd) == "pactl" if self.cmd else False

    def is_available(self) -> bool:
        return bool(self.cmd)

    def get_state(self) -> Tuple[int, bool]:
        """Return (volume_percent, is_muted)."""
        if not self.cmd:
            return (0, False)
        try:
            if self.is_pulse:
                res = subprocess.run(
                    [self.cmd, "get-sink-volume", "@DEFAULT_SINK@"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    env={**os.environ, "LC_ALL": "C"},
                )
                levels = [int(n) for n in re.findall(r"/\s*(\d+)%", res.stdout)]
                vol = round(sum(levels) / len(levels)) if levels else 0

                res_mute = subprocess.run(
                    [self.cmd, "get-sink-mute", "@DEFAULT_SINK@"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    env={**os.environ, "LC_ALL": "C"},
                )
                muted = "yes" in res_mute.stdout.lower()
                return (max(0, min(100, vol)), muted)
            else:
                res = subprocess.run(
                    [self.cmd, "get-volume", "@DEFAULT_AUDIO_SINK@"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    env={**os.environ, "LC_ALL": "C"},
                )
                match = re.search(r"Volume:\s*([\d.]+)", res.stdout)
                vol = round(float(match.group(1)) * 100) if match else 0
                muted = "[MUTED]" in res.stdout
                return (max(0, min(100, vol)), muted)
        except Exception:
            return (0, False)

    def set_volume(self, percent: int):
        if not self.cmd:
            return
        vol = max(0, min(100, int(percent)))
        try:
            if self.is_pulse:
                subprocess.run(
                    [self.cmd, "set-sink-volume", "@DEFAULT_SINK@", f"{vol}%"],
                    timeout=2,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.run(
                    [self.cmd, "set-volume", "@DEFAULT_AUDIO_SINK@", f"{vol/100:.2f}"],
                    timeout=2,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass

    def toggle_mute(self):
        if not self.cmd:
            return
        try:
            if self.is_pulse:
                subprocess.run(
                    [self.cmd, "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
                    timeout=2,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.run(
                    [self.cmd, "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],
                    timeout=2,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass


class BrightnessController:
    """Controls screen brightness via GNOME SettingsDaemon Power D-Bus."""

    def __init__(self):
        self.bus = None
        self.available = False
        try:
            from gi.repository import Gio
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            val = self.get_brightness()
            self.available = val is not None
        except Exception:
            self.available = False

    def get_brightness(self) -> int:
        if not self.bus:
            return None
        try:
            from gi.repository import GLib, Gio
            res = self.bus.call_sync(
                "org.gnome.SettingsDaemon.Power",
                "/org/gnome/SettingsDaemon/Power",
                "org.freedesktop.DBus.Properties",
                "Get",
                GLib.Variant("(ss)", ("org.gnome.SettingsDaemon.Power.Screen", "Brightness")),
                None,
                Gio.DBusCallFlags.NONE,
                1500,
                None,
            )
            val = res.unpack()[0]
            if 0 <= val <= 100:
                self.available = True
                return int(val)
        except Exception:
            self.available = False
        return None

    def set_brightness(self, value: int):
        if not self.bus:
            return
        val = max(0, min(100, int(value)))
        try:
            from gi.repository import GLib, Gio
            self.bus.call_sync(
                "org.gnome.SettingsDaemon.Power",
                "/org/gnome/SettingsDaemon/Power",
                "org.freedesktop.DBus.Properties",
                "Set",
                GLib.Variant("(ssv)", ("org.gnome.SettingsDaemon.Power.Screen", "Brightness", GLib.Variant("i", val))),
                None,
                Gio.DBusCallFlags.NONE,
                1500,
                None,
            )
        except Exception:
            pass


class SystemMetrics:
    """Gathers CPU, RAM, and Disk metrics without heavy external dependencies."""

    def __init__(self):
        self._last_cpu = None

    def get_metrics(self):
        # RAM
        ram_pct = 0.0
        try:
            info = {
                line.split(":")[0]: int(line.split()[1])
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith(("MemTotal:", "MemAvailable:"))
            }
            if "MemTotal" in info and "MemAvailable" in info:
                ram_pct = 100.0 * (1.0 - info["MemAvailable"] / info["MemTotal"])
        except Exception:
            pass

        # CPU load
        load_1m = "—"
        try:
            load_1m = Path("/proc/loadavg").read_text().split()[0]
        except Exception:
            pass

        # Disk
        disk_pct = 0.0
        disk_free_gb = 0.0
        try:
            usage = shutil.disk_usage(str(Path.home()))
            disk_pct = (usage.used / usage.total) * 100.0
            disk_free_gb = usage.free / (1024**3)
        except Exception:
            pass

        return {
            "ram_pct": ram_pct,
            "load_1m": load_1m,
            "disk_pct": disk_pct,
            "disk_free_gb": disk_free_gb,
        }
