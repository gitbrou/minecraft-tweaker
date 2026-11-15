"""X11 process and window lookup."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from . import _x11

TITLE_HINT = "Minecraft"


@dataclass
class MinecraftWindow:
    hwnd: int
    title: str
    pid: int
    exe: str

    @property
    def is_world(self) -> bool:
        return " - " in self.title

    @property
    def world(self) -> str | None:
        if not self.is_world:
            return None
        return self.title.split(" - ", 1)[-1].strip()

    def rect(self) -> tuple[int, int, int, int]:
        try:
            return _x11.window_geometry(_x11.default_client(), self.hwnd)
        except Exception:
            width, height = _x11.default_client().screen_size()
            return (0, 0, width, height)

    def focused(self) -> bool:
        try:
            return _x11.active_window(_x11.default_client()) == self.hwnd
        except Exception:
            return False

    def focus(self) -> bool:
        try:
            client = _x11.default_client()
            _x11.x11.XRaiseWindow(client.display, self.hwnd)
            _x11.x11.XSetInputFocus(client.display, self.hwnd, 2, 0)
            _x11.x11.XFlush(client.display)
            return True
        except Exception:
            return False


def _cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace")


def _exe_of(pid: int) -> str:
    try:
        return os.readlink(f"/proc/{pid}/exe")
    except OSError:
        return ""


def _looks_like_game(title: str, cmdline: str) -> bool:
    if TITLE_HINT.lower() in title.lower():
        return True
    text = cmdline.lower()
    return "minecraft" in text or "net.minecraft" in text


def windows(hint: str = TITLE_HINT) -> list[MinecraftWindow]:
    client = _x11.default_client()
    found: list[MinecraftWindow] = []
    try:
        roots = [client.root, *_x11.child_windows(client, client.root)]
    except Exception:
        return found
    for win in roots:
        try:
            title = _x11.window_title(client, win)
            if not title:
                continue
            pid = _x11.window_pid(client, win)
            if not pid:
                continue
            if not _looks_like_game(title, _cmdline(pid)):
                continue
            if hint and hint.lower() not in title.lower() and hint != TITLE_HINT:
                continue
            raw_hwnd = win.value if hasattr(win, "value") else win
            found.append(MinecraftWindow(hwnd=int(raw_hwnd), title=title,
                                         pid=int(pid), exe=_exe_of(int(pid))))
        except Exception:
            continue
    return found


def find(hint: str = TITLE_HINT) -> MinecraftWindow | None:
    items = windows(hint)
    if not items:
        return None
    for item in items:
        if item.is_world:
            return item
    return items[0]


def is_running(hint: str = TITLE_HINT) -> bool:
    return find(hint) is not None


def wait(timeout: float | None = None, poll: float = 0.5,
         hint: str = TITLE_HINT) -> MinecraftWindow | None:
    deadline = None if timeout is None else time.monotonic() + timeout
    while True:
        window = find(hint)
        if window is not None:
            return window
        if deadline is not None and time.monotonic() >= deadline:
            return None
        time.sleep(poll)


def wait_world(timeout: float | None = None, poll: float = 0.5,
               hint: str = TITLE_HINT) -> MinecraftWindow | None:
    deadline = None if timeout is None else time.monotonic() + timeout
    while True:
        window = find(hint)
        if window is not None and window.is_world:
            return window
        if deadline is not None and time.monotonic() >= deadline:
            return None
        time.sleep(poll)


__all__ = ["MinecraftWindow", "windows", "find", "is_running", "wait", "wait_world", "TITLE_HINT"]
