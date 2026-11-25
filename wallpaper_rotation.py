"""Automatic wallpaper rotation, history, and favorites for Neon Studio."""
import json
import os
from pathlib import Path
import random
import time
from typing import List, Optional

from preferences import ROOT, load, update
from wallpaper_collection import collection_paths

HISTORY_FILE = ROOT / "state" / "wallpaper-history.json"
FAVORITES_FILE = ROOT / "state" / "wallpaper-favorites.json"
MAX_HISTORY = 50


def load_json_list(path: Path) -> List[str]:
    try:
        data = json.loads(path.read_text())
        return [str(p) for p in data if isinstance(p, str)]
    except Exception:
        return []


def save_json_list(path: Path, items: List[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(items, indent=2))
    temp.replace(path)


class WallpaperRotationManager:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.history_file = HISTORY_FILE
        self.favorites_file = FAVORITES_FILE
        self.last_rotate_time = time.time()

    def get_history(self) -> List[str]:
        return load_json_list(self.history_file)

    def get_favorites(self) -> List[str]:
        return load_json_list(self.favorites_file)

    def is_favorite(self, path: str) -> bool:
        resolved = str(Path(path).resolve())
        return resolved in self.get_favorites()

    def toggle_favorite(self, path: str) -> bool:
        resolved = str(Path(path).resolve())
        favs = self.get_favorites()
        if resolved in favs:
            favs.remove(resolved)
            status = False
        else:
            favs.append(resolved)
            status = True
        save_json_list(self.favorites_file, favs)
        return status

    def record_history(self, path: str):
        resolved = str(Path(path).resolve())
        hist = self.get_history()
        if hist and hist[-1] == resolved:
            return
        hist.append(resolved)
        if len(hist) > MAX_HISTORY:
            hist = hist[-MAX_HISTORY:]
        save_json_list(self.history_file, hist)

    def get_previous(self) -> Optional[str]:
        hist = self.get_history()
        current = str(Path(load().get("active_wallpaper", "")).resolve()) if load().get("active_wallpaper") else ""
        if len(hist) >= 2:
            if hist[-1] == current:
                return hist[-2]
            return hist[-1]
        return None

    def get_next(self, randomized: bool = True) -> Optional[str]:
        prefs = load()
        folder = prefs.get("wallpaper_folder", str(self.root / "wallpapers"))
        paths = collection_paths(folder)
        if not paths:
            return None
        current = str(Path(prefs.get("active_wallpaper", "")).resolve()) if prefs.get("active_wallpaper") else ""
        candidates = [str(p.resolve()) for p in paths if str(p.resolve()) != current]
        if not candidates:
            return str(paths[0].resolve())
        if randomized:
            return random.choice(candidates)
        # Sequential
        all_resolved = [str(p.resolve()) for p in paths]
        if current in all_resolved:
            idx = all_resolved.index(current)
            return all_resolved[(idx + 1) % len(all_resolved)]
        return all_resolved[0]

    def should_rotate(self) -> bool:
        prefs = load()
        interval_hours = float(prefs.get("rotate_hours", 0))
        if interval_hours <= 0:
            return False
        interval_seconds = interval_hours * 3600.0
        return (time.time() - self.last_rotate_time) >= interval_seconds

    def check_rotation(self, apply_callback=None) -> Optional[str]:
        if not self.should_rotate():
            return None
        self.last_rotate_time = time.time()
        next_wall = self.get_next()
        if next_wall and apply_callback:
            apply_callback(next_wall)
        return next_wall
