"""Input state for both platforms.

Windows reads key state through GetAsyncKeyState, Linux through the X11
keymap. Only two things are needed by the rest of the library: whether a
virtual key is down, and where the cursor is.
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from ._win import user32, wt

    def down(vk_code: int) -> bool:
        return bool(user32.GetAsyncKeyState(vk_code) & 0x8001)

    def cursor() -> tuple[int, int]:
        point = wt.POINT()
        if user32.GetCursorPos(point):
            return (int(point.x), int(point.y))
        return (0, 0)

else:
    from . import _x11

    def down(vk_code: int) -> bool:
        return _x11.default_client().key_down(vk_code)

    def cursor() -> tuple[int, int]:
        x, y, _mask = _x11.default_client().pointer()
        return (int(x), int(y))


__all__ = ["down", "cursor"]
