"""Overlay window backend.

Windows uses a layered window with UpdateLayeredWindow. Linux uses an X11
ARGB window with XPutImage. Both expose the same Overlay class.
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from ._overlay_win import Overlay, OverlayStats
else:
    from ._overlay_x11 import Overlay, OverlayStats

__all__ = ["Overlay", "OverlayStats"]
