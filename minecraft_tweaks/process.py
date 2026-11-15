"""Minecraft window lookup.

Windows walks top-level windows through win32. Linux walks the X11 tree and
maps windows to processes through _NET_WM_PID.
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from ._process_win import (TITLE_HINT, MinecraftWindow, find, is_running,
                               wait, wait_world, windows)
else:
    from ._process_x11 import (TITLE_HINT, MinecraftWindow, find, is_running,
                               wait, wait_world, windows)

__all__ = ["MinecraftWindow", "windows", "find", "is_running", "wait", "wait_world", "TITLE_HINT"]
