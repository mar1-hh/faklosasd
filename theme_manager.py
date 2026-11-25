"""Theme manager and external script hooks executor for Neon Studio."""
import colorsys
import os
from pathlib import Path
import subprocess
import time
from typing import Dict, List, Tuple

from preferences import ROOT, load, effective_accent

HOOKS_DIR = ROOT / "state" / "hooks"


def hex_to_rgb(hex_code: str) -> Tuple[float, float, float]:
    clean = hex_code.lstrip("#")
    if len(clean) != 6:
        return (0.8, 0.6, 0.8)
    return tuple(int(clean[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        round(max(0.0, min(1.0, r)) * 255),
        round(max(0.0, min(1.0, g)) * 255),
        round(max(0.0, min(1.0, b)) * 255),
    )


def relative_luminance(rgb: Tuple[float, float, float]) -> float:
    def adjust(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (adjust(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


class ThemeManager:
    def __init__(self, hooks_dir=HOOKS_DIR):
        self.hooks_dir = Path(hooks_dir)
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

    def resolve_mode(self, mode: str = None) -> str:
        chosen = mode or load().get("theme_mode", "dark")
        if chosen in ("dark", "light"):
            return chosen
        # Auto mode: 07:00 to 19:00 is light
        hour = time.localtime().tm_hour
        return "light" if 7 <= hour < 19 else "dark"

    def build_palette(self, accent_hex: str, mode: str = "dark") -> Dict[str, str]:
        r, g, b = hex_to_rgb(accent_hex)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)

        # Contrast check for text on accent
        lum = relative_luminance((r, g, b))
        on_accent = "#131018" if lum > 0.35 else "#ffffff"

        if mode == "light":
            paper = "#faf8fb"
            paper2 = "#ece7ef"
            ink = "#1a1620"
            muted = "#6e6475"
            border = "rgba(0, 0, 0, 0.12)"
        else:
            paper = "#131018"
            paper2 = "#1f1925"
            ink = "#f5f0f6"
            muted = "#a89eb0"
            border = "rgba(255, 255, 255, 0.12)"

        return {
            "mode": mode,
            "accent": accent_hex,
            "on_accent": on_accent,
            "paper": paper,
            "paper2": paper2,
            "ink": ink,
            "muted": muted,
            "border": border,
        }

    def execute_hooks(self, palette: Dict[str, str], wallpaper_path: str = "") -> List[str]:
        """Run all executable scripts in state/hooks/ with NEON_* env vars."""
        results = []
        if not self.hooks_dir.is_dir():
            return results

        env = dict(os.environ)
        env.update({
            "NEON_MODE": palette.get("mode", "dark"),
            "NEON_ACCENT": palette.get("accent", "#dfa1c6"),
            "NEON_ON_ACCENT": palette.get("on_accent", "#ffffff"),
            "NEON_PAPER": palette.get("paper", "#131018"),
            "NEON_PAPER2": palette.get("paper2", "#1f1925"),
            "NEON_INK": palette.get("ink", "#f5f0f6"),
            "NEON_MUTED": palette.get("muted", "#a89eb0"),
            "NEON_WALLPAPER": str(wallpaper_path),
        })

        for script in sorted(self.hooks_dir.iterdir()):
            if script.is_file() and os.access(script, os.X_OK) and not script.name.startswith("."):
                try:
                    proc = subprocess.run(
                        [str(script.resolve())],
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5,
                        text=True,
                    )
                    status = "OK" if proc.returncode == 0 else f"Failed (exit {proc.returncode})"
                    results.append(f"{script.name}: {status}")
                except subprocess.TimeoutExpired:
                    results.append(f"{script.name}: Timed out (5s)")
                except Exception as exc:
                    results.append(f"{script.name}: Error ({exc})")

        return results
