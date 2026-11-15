"""X11 overlay window: a click-through transparent layer over the game."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

from . import _x11
from .draw import Canvas

CWColormap = 1 << 13
CWOverrideRedirect = 1 << 9


@dataclass
class OverlayStats:
    frames: int = 0
    fps: float = 0.0
    width: int = 0
    height: int = 0
    present_errors: int = 0


class Overlay:
    """Transparent full-screen window that follows the game window.

    Transparency depends on a running compositor. Without one the window
    shows an opaque background, so keep picom, GNOME, KDE or Xfce
    compositing enabled.
    """

    def __init__(self, *, fps: int = 144, click_through: bool = True,
                 topmost: bool = True, name: str = "minecraft-tweaks") -> None:
        self.fps = fps
        self.click_through = click_through
        self.topmost = topmost
        self.name = name
        self.stats = OverlayStats()

        self._client: Optional[_x11.XClient] = None
        self._visual: Optional[_x11.ARGBVisual] = None
        self._win: Optional[int] = None
        self._gc = None
        self._canvas: Optional[Canvas] = None
        self._w = 0
        self._h = 0
        self._hint = name

    @property
    def canvas(self) -> Canvas:
        if self._canvas is None:
            raise RuntimeError("call open() first")
        return self._canvas

    @property
    def hwnd(self) -> Optional[int]:
        return self._win

    @property
    def visible(self) -> bool:
        return self._win is not None

    def open(self) -> "Overlay":
        if self._win is not None:
            return self
        client = _x11.default_client()
        visual = _x11.ARGBVisual(client)
        width, height = client.screen_size()
        win = _x11.create_overlay_window(client, visual, 0, 0, width, height)
        gc = _x11.x11.XCreateGC(client.display, win, 0, None)
        self._client = client
        self._visual = visual
        self._win = win
        self._gc = gc
        self._canvas = Canvas(width, height)
        self._w, self._h = width, height
        self.stats.width, self.stats.height = width, height
        _x11.x11.XMapRaised(client.display, win)
        _x11.x11.XFlush(client.display)
        return self

    def close(self) -> None:
        client = self._client
        if client is None:
            return
        try:
            if self._gc:
                _x11.x11.XFreeGC(client.display, self._gc)
            if self._win:
                _x11.x11.XDestroyWindow(client.display, self._win)
            _x11.x11.XFlush(client.display)
        finally:
            self._gc = None
            self._win = None
            self._canvas = None

    def __enter__(self) -> "Overlay":
        return self.open()

    def __exit__(self, *exc) -> None:
        self.close()

    def follow(self, mc=None) -> bool:
        if self._client is None or self._win is None:
            return False
        if mc is None:
            from . import process

            mc = process.find(self._hint)
        if mc is None:
            return False
        x, y, w, h = mc.rect()
        if w <= 0 or h <= 0:
            return False
        if w != self._w or h != self._h:
            client = self._client
            _x11.x11.XMoveResizeWindow(client.display, self._win, int(x), int(y), int(w), int(h))
            self._canvas = Canvas(int(w), int(h))
            self._w, self._h = int(w), int(h)
            self.stats.width, self.stats.height = int(w), int(h)
            return True
        client = self._client
        _x11.x11.XMoveResizeWindow(client.display, self._win, int(x), int(y), int(w), int(h))
        return True

    def present(self) -> bool:
        client = self._client
        if client is None or self._win is None or self._canvas is None:
            return False
        try:
            _x11.put_buffer(client, self._visual, self._win, self._gc,
                            self._canvas.buf, self._w, self._h)
            self.stats.frames += 1
            return True
        except Exception:
            self.stats.present_errors += 1
            return False

    def hide(self) -> None:
        client = self._client
        if client is None or self._win is None:
            return
        _x11.x11.XUnmapWindow(client.display, self._win)
        _x11.x11.XFlush(client.display)

    def loop(self, render: Callable[[Canvas, "Overlay"], None], *,
             follow: bool = True, hide_unfocused: bool = True,
             hide_when: Optional[Callable[[], bool]] = None,
             should_stop: Optional[Callable[[], bool]] = None,
             duration: Optional[float] = None) -> OverlayStats:
        from . import process

        self.open()
        started = time.perf_counter()
        budget = 1.0 / max(1, self.fps)
        window_start = started
        frames_since = 0
        hidden = False
        try:
            while True:
                if should_stop is not None and should_stop():
                    break
                if duration is not None and time.perf_counter() - started >= duration:
                    break

                mc = process.find(self._hint)
                hide = mc is None
                if hide_unfocused and not hide:
                    hide = not mc.focused()
                if hide_when is not None and hide_when():
                    hide = True

                if hide:
                    if not hidden:
                        self.hide()
                        hidden = True
                    time.sleep(0.1)
                    continue

                hidden = False
                if follow:
                    self.follow(mc)
                frame_start = time.perf_counter()
                render(self._canvas, self)
                self.present()

                frames_since += 1
                now = time.perf_counter()
                if now - window_start >= 0.5:
                    self.stats.fps = frames_since / (now - window_start)
                    window_start = now
                    frames_since = 0
                spent = now - frame_start
                if spent < budget:
                    time.sleep(budget - spent)
        finally:
            self.close()
        return self.stats


__all__ = ["Overlay", "OverlayStats"]
