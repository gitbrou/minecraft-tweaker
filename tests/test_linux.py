"""Linux/X11 checks. Runs on Windows too, but only the pure parts execute there.

    python tests/test_linux.py
    PYTHONPATH=. python3 tests/test_linux.py      (inside WSL)
"""

from __future__ import annotations

import sys
import traceback

import minecraft_tweaks as mt
from minecraft_tweaks import _x11


def check(name: str, ok: bool, extra: str = "") -> bool:
    print(("OK   " if ok else "FAIL ") + name + (("  :: " + extra) if extra else ""))
    return ok


def main() -> int:
    ok = True
    print("platform", sys.platform, "python", sys.version.split()[0])
    print("package", mt.__version__)
    ok &= check("x11 module imports", True)
    ok &= check("keysym_for_vk('R')", _x11.keysym_for_vk(0x52) == 0x72, hex(_x11.keysym_for_vk(0x52)))
    ok &= check("keysym_for_vk(ALT)", _x11.keysym_for_vk(0x12) == 0xFFE9)
    ok &= check("keysym_for_vk(unknown)", _x11.keysym_for_vk(0x07) is None)
    ok &= check("is_pressed", _x11.is_pressed(b"\x01" + b"\x00" * 31, 0) is True)
    ok &= check("is_pressed empty bit", _x11.is_pressed(b"\x00" * 32, 5) is False)
    print("x11 library available:", _x11.X11_AVAILABLE)

    if not _x11.X11_AVAILABLE:
        print("RESULT ok (pure checks only, no libX11)")
        return 0 if ok else 1

    try:
        client = _x11.default_client()
        w, h = client.screen_size()
        ok &= check("X display opens", w > 0 and h > 0, f"screen {w}x{h}")
        ok &= check("keymap readable", len(client.keymap()) == 32)
        ok &= check("pointer readable", len(client.pointer()) == 3)
    except Exception:
        traceback.print_exc()
        ok &= check("X display opens", False)

    try:
        from minecraft_tweaks import process
        found = process.find()
        ok &= check("process.find() runs", True, "window: " + (found.title if found else "none"))
    except Exception:
        traceback.print_exc()
        ok &= check("process.find() runs", False)

    try:
        from minecraft_tweaks.overlay import Overlay

        overlay = Overlay(fps=60)
        overlay.open()
        with overlay:
            overlay.canvas.clear(0x00000000)
            overlay.canvas.fill_rect(10, 10, 120, 40, 0xFF7C5CFF)
            overlay.present()
            overlay.present()
        ok &= check("overlay open/present", overlay.stats.present_errors == 0,
                    f"frames={overlay.stats.frames} errors={overlay.stats.present_errors}")
    except Exception as exc:
        traceback.print_exc()
        ok &= check("overlay open/present", False, repr(exc))

    print("RESULT", "ok" if ok else "fail")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
