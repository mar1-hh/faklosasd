"""Allowlisted safe cache cleaner for 42 student iMacs.

Safely scans and frees space from disposable compiler, browser, and editor caches
without touching configuration files, repositories, extensions, or user documents.
"""
import os
from pathlib import Path
import shutil
import stat
import subprocess
from typing import Dict, List, Optional, Tuple

ALLOWLISTED_CACHES = (
    (".config/Code/CachedExtensionVSIXs", "code", "VS Code extension package cache"),
    (".config/Code/CachedData", "code", "VS Code bytecode and compilation cache"),
    (".config/Code/Cache", "code", "VS Code application cache"),
    (".config/Code/Code Cache", "code", "VS Code JavaScript cache"),
    (".config/Code/GPUCache", "code", "VS Code shader and GPU cache"),
    (".cache/mozilla", "firefox", "Firefox web cache"),
    ("snap/firefox/common/.cache", "firefox", "Firefox snap cache"),
    (".cache/mesa_shader_cache", "shaders", "Mesa OpenGL/Vulkan shader cache"),
    (".cache/pip", "pip", "Python pip download cache"),
    ("state/cache", "neon", "Neon Studio media and thumbnail cache"),
)


def get_running_processes() -> set:
    try:
        out = subprocess.check_output(["ps", "-u", str(os.getuid()), "-o", "comm="], text=True)
        return set(out.split())
    except Exception:
        return set()


def dir_size(path: Path) -> int:
    """Calculate directory size in bytes without following symlinks."""
    total = 0
    if not path.is_dir() or path.is_symlink():
        return 0
    for root, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]
        for name in files:
            try:
                p = Path(root) / name
                info = p.lstat()
                if stat.S_ISREG(info.st_mode):
                    total += info.st_blocks * 512
            except (OSError, FileNotFoundError):
                pass
    return total


def format_size(bytes_val: int) -> str:
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KiB"
    if bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024**2):.1f} MiB"
    return f"{bytes_val / (1024**3):.2f} GiB"


class CacheCleaner:
    def __init__(self, home=None, root=None):
        self.home = Path(home or Path.home()).resolve()
        self.root = Path(root or Path(__file__).resolve().parent).resolve()

    def scan(self) -> List[Dict]:
        running = get_running_processes()
        items = []

        for rel_path, app_type, desc in ALLOWLISTED_CACHES:
            base = self.root if app_type == "neon" else self.home
            full_path = (base / rel_path).resolve()

            # Security: verify path is inside base
            try:
                full_path.relative_to(base)
            except ValueError:
                continue

            if not full_path.is_dir() or full_path.is_symlink():
                continue

            # Verify no parent component is a symlink
            is_symlink_traversal = False
            curr = full_path
            while curr != base:
                if curr.is_symlink():
                    is_symlink_traversal = True
                    break
                curr = curr.parent
            if is_symlink_traversal:
                continue

            # Check if app is running
            is_running = False
            if app_type == "code" and running & {"code", "code-insiders"}:
                is_running = True
            elif app_type == "firefox" and any("firefox" in p for p in running):
                is_running = True

            size = dir_size(full_path)
            items.append({
                "id": rel_path,
                "path": str(full_path),
                "relative": rel_path,
                "app": app_type,
                "description": desc,
                "size_bytes": size,
                "size_display": format_size(size),
                "is_running": is_running,
                "eligible": not is_running and size > 0,
            })
        return items

    def clean(self, target_paths: List[str]) -> Tuple[int, List[str]]:
        """Clean contents of approved target cache directories."""
        cleaned_bytes = 0
        log = []
        running = get_running_processes()

        for path_str in target_paths:
            p = Path(path_str).resolve()
            # Double check against allowlist
            matched = False
            app_type = ""
            for rel, app, _ in ALLOWLISTED_CACHES:
                base = self.root if app == "neon" else self.home
                if (base / rel).resolve() == p:
                    matched = True
                    app_type = app
                    break
            if not matched:
                log.append(f"Rejected unapproved path: {p}")
                continue

            if (app_type == "code" and running & {"code", "code-insiders"}) or \
               (app_type == "firefox" and any("firefox" in pr for pr in running)):
                log.append(f"Skipped running application: {p.name}")
                continue

            size = dir_size(p)
            try:
                # Remove contents, preserve root folder
                for child in p.iterdir():
                    if child.is_symlink() or not child.is_dir():
                        child.unlink()
                    else:
                        shutil.rmtree(child)
                cleaned_bytes += size
                log.append(f"Cleaned {format_size(size)}: {p}")
            except Exception as exc:
                log.append(f"Error cleaning {p}: {exc}")

        return (cleaned_bytes, log)
