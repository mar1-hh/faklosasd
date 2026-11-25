"""Campus goinfre storage detection and non-destructive asset relocation for 42 iMacs."""
import os
from pathlib import Path
import shutil
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
RELOCATION_RECORD = ROOT / "state" / "goinfre-relocations.json"


def find_goinfre_root() -> Optional[Path]:
    """Discover student goinfre storage on 42 / 1337 workstations."""
    username = os.environ.get("USER", "")
    candidates = [
        Path.home() / "goinfre",
        Path(f"/goinfre/{username}"),
        Path("/goinfre") / username if username else None,
    ]
    for c in candidates:
        if c and c.is_dir() and os.access(c, os.W_OK | os.R_OK):
            return c.resolve()
    return None


def get_goinfre_status() -> Dict:
    root = find_goinfre_root()
    if not root:
        return {"available": False, "path": None, "free_gb": 0.0, "total_gb": 0.0}
    try:
        usage = shutil.disk_usage(str(root))
        return {
            "available": True,
            "path": str(root),
            "free_gb": usage.free / (1024**3),
            "total_gb": usage.total / (1024**3),
        }
    except Exception:
        return {"available": True, "path": str(root), "free_gb": 0.0, "total_gb": 0.0}


def relocate_directory(source_dir: Path, target_base: Path) -> Tuple[bool, str]:
    """Safely move a bulky data directory to goinfre and link it back."""
    source_dir = Path(source_dir).resolve()
    if not source_dir.exists():
        return (False, f"Source directory {source_dir} does not exist.")
    if source_dir.is_symlink():
        return (False, f"{source_dir} is already relocated / symlinked.")

    target_dir = target_base / source_dir.name
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    try:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir, symlinks=False)
        shutil.rmtree(source_dir)
        source_dir.symlink_to(target_dir)
        return (True, f"Relocated {source_dir.name} to {target_dir}")
    except Exception as exc:
        return (False, f"Relocation failed: {exc}")


def restore_directory(source_symlink: Path) -> Tuple[bool, str]:
    """Restore a relocated symlink back to a local home directory."""
    source_symlink = Path(source_symlink)
    if not source_symlink.is_symlink():
        return (False, f"{source_symlink} is not a symlink.")
    target_dir = source_symlink.resolve()
    if not target_dir.is_dir():
        return (False, f"Target {target_dir} is invalid.")

    try:
        source_symlink.unlink()
        shutil.copytree(target_dir, source_symlink, symlinks=False)
        return (True, f"Restored {source_symlink.name} back to local storage.")
    except Exception as exc:
        return (False, f"Restoration failed: {exc}")
