"""Оверлей поверх Minecraft: настоящее per-pixel alpha, без дёрганья.

Способ тот же, что используют нормальные читы-оверлеи без инжекта:
слоёное окно (WS_EX_LAYERED) + 32-битный DIB + ``UpdateLayeredWindow``.
DWM композитит его каждый кадр монитора, поэтому картинка не «плывёт»
относительно игры, а прозрачность честная (пиксельная, а не color key).
"""

from __future__ import annotations

import ctypes
import os
import time
from dataclasses import dataclass
from typing import Callable, Optional

from . import process
from ._win import (
    AC_SRC_ALPHA,
    AC_SRC_OVER,
    BI_RGB,
    BLENDFUNCTION,
    BITMAPINFO,
    BITMAPINFOHEADER,
    DIB_RGB_COLORS,
    SIZE,
    SW_HIDE,
    SW_SHOWNOACTIVATE,
    ULW_ALPHA,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    WS_EX_TOPMOST,
    WS_EX_TRANSPARENT,
    WS_POPUP,
    WNDCLASSEXW,
    WNDPROC,
    gdi32,
    kernel32,
    set_dpi_aware,
    user32,
    wt,
)
from .draw import Canvas

__all__ = ["Overlay", "OverlayStats"]

_CLASS_COUNTER = 0


@dataclass
class OverlayStats:
    frames: int = 0
    fps: float = 0.0
    width: int = 0
    height: int = 0
    present_errors: int = 0


class Overlay:
    """Прозрачное окно-холст, которое следует за окном игры.

    Пример::

        ov = Overlay(fps=144)
        ov.loop(lambda c, o: c.text("hi", 10, 10, 0xFFFFFFFF))
    """

    def __init__(self, *, fps: int = 144, click_through: bool = True,
                 topmost: bool = True, name: str = "minecraft-tweaks") -> None:
        self.fps = fps
        self.click_through = click_through
        self.topmost = topmost
        self.name = name
        self.stats = OverlayStats()

        self._hwnd: Optional[int] = None
        self._memdc = None
        self._dib = None
        self._bits = None
        self._canvas: Optional[Canvas] = None
        self._wndproc = None
        self._class_name = ""
        self._pos = wt.POINT(0, 0)
        self._size = SIZE(0, 0)

    # -- свойства ----------------------------------------------------------
    @property
    def canvas(self) -> Canvas:
        if self._canvas is None:
            raise RuntimeError("сначала вызовите open()")
        return self._canvas

    @property
    def hwnd(self) -> Optional[int]:
        return self._hwnd

    @property
    def visible(self) -> bool:
        return bool(self._hwnd) and bool(user32.IsWindowVisible(self._hwnd))

    # -- окно --------------------------------------------------------------
    def open(self) -> "Overlay":
        set_dpi_aware()
        if self._hwnd:
            return self
        global _CLASS_COUNTER
        _CLASS_COUNTER += 1
        self._class_name = f"SsPyOverlay{os.getpid()}_{_CLASS_COUNTER}"

        self._wndproc = WNDPROC(self._on_message)
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = self._class_name
        if not user32.RegisterClassExW(ctypes.byref(wc)) and self._last_error() != 1410:
            raise ctypes.WinError(self._last_error())

        ex = WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        if self.click_through:
            ex |= WS_EX_TRANSPARENT
        if self.topmost:
            ex |= WS_EX_TOPMOST

        hwnd = user32.CreateWindowExW(
            ex, self._class_name, self.name, WS_POPUP,
            0, 0, 100, 100, None, None, wc.hInstance, None,
        )
        if not hwnd:
            raise ctypes.WinError(self._last_error())
        self._hwnd = hwnd
        self._ensure_surface(100, 100)
        return self

    def close(self) -> None:
        if self._dib:
            gdi32.DeleteObject(self._dib)
        if self._memdc:
            gdi32.DeleteDC(self._memdc)
        self._memdc = self._dib = self._bits = None
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
            self._hwnd = None

    def __enter__(self) -> "Overlay":
        return self.open()

    def __exit__(self, *exc) -> None:
        self.close()

    @staticmethod
    def _last_error() -> int:
        return ctypes.get_last_error()

    def _on_message(self, hwnd, msg, wparam, lparam):
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    # -- поверхность -------------------------------------------------------
    def _ensure_surface(self, width: int, height: int) -> None:
        width, height = max(1, int(width)), max(1, int(height))
        if self._canvas is not None and self._canvas.width == width and self._canvas.height == height:
            return
        if self._dib:
            gdi32.DeleteObject(self._dib)
            self._dib = None
        if self._memdc:
            gdi32.DeleteDC(self._memdc)
            self._memdc = None

        screen = user32.GetDC(None)
        memdc = gdi32.CreateCompatibleDC(screen)
        user32.ReleaseDC(None, screen)
        if not memdc:
            raise ctypes.WinError(self._last_error())

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height  # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        bits_ptr = ctypes.c_void_p()
        dib = gdi32.CreateDIBSection(memdc, ctypes.byref(bmi), DIB_RGB_COLORS,
                                     ctypes.byref(bits_ptr), None, 0)
        if not dib or not bits_ptr.value:
            raise ctypes.WinError(self._last_error())
        gdi32.SelectObject(memdc, dib)

        self._memdc = memdc
        self._dib = dib
        self._bits = bits_ptr
        self._canvas = Canvas(width, height)
        self._size = SIZE(width, height)
        self.stats.width, self.stats.height = width, height

    # -- кадр --------------------------------------------------------------
    def follow(self, mc: Optional[process.MinecraftWindow] = None) -> bool:
        """Подогнать окно под клиентскую область Minecraft."""
        if self._hwnd is None:
            return False
        mc = mc or process.find()
        if mc is None:
            return False
        x, y, w, h = mc.rect()
        if w <= 0 or h <= 0:
            return False
        self._ensure_surface(w, h)
        self._pos.x, self._pos.y = x, y
        return True

    def present(self) -> bool:
        """Отправить буфер в окно (UpdateLayeredWindow)."""
        if not self._hwnd or not self._bits or self._canvas is None:
            return False
        canvas = self._canvas
        ctypes.memmove(self._bits, (ctypes.c_char * len(canvas.buf)).from_buffer(canvas.buf),
                       len(canvas.buf))
        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        src = wt.POINT(0, 0)
        ok = user32.UpdateLayeredWindow(
            self._hwnd, None, ctypes.byref(self._pos), ctypes.byref(self._size),
            self._memdc, ctypes.byref(src), 0, ctypes.byref(blend), ULW_ALPHA,
        )
        if ok:
            user32.ShowWindow(self._hwnd, SW_SHOWNOACTIVATE)
            self.stats.frames += 1
        else:
            self.stats.present_errors += 1
        return bool(ok)

    def hide(self) -> None:
        if self._hwnd:
            user32.ShowWindow(self._hwnd, SW_HIDE)

    # -- цикл --------------------------------------------------------------
    def loop(self, render: Callable[[Canvas, "Overlay"], None], *,
             follow: bool = True, hide_unfocused: bool = True,
             hide_when: Callable[[], bool] | None = None,
             should_stop: Callable[[], bool] | None = None,
             duration: float | None = None) -> None:
        """Крутит кадры, пока ``should_stop()`` не вернёт True.

        render(canvas, overlay) вызывается каждый кадр; рисовать нужно
        в canvas, отправляет кадр сам loop().
        """
        self.open()
        frame_budget = 1.0 / max(1, self.fps)
        started = time.perf_counter()
        last = started
        frames_in_sec = 0

        try:
            while True:
                if should_stop is not None and should_stop():
                    break
                if duration is not None and time.perf_counter() - started > duration:
                    break

                mc = process.find() if follow else None
                if follow and mc is None:
                    self.hide()
                    time.sleep(0.1)
                    continue
                if hide_unfocused and mc is not None and not mc.focused():
                    self.hide()
                    time.sleep(0.03)
                    continue
                if hide_when is not None and hide_when():
                    self.hide()
                    time.sleep(0.03)
                    continue

                if follow:
                    self.follow(mc)

                self.canvas.clear()
                render(self.canvas, self)

                t0 = time.perf_counter()
                self.present()
                frames_in_sec += 1
                now = time.perf_counter()
                if now - last >= 1.0:
                    self.stats.fps = frames_in_sec / (now - last)
                    frames_in_sec = 0
                    last = now

                spare = frame_budget - (time.perf_counter() - t0)
                if spare > 0:
                    time.sleep(spare)
        finally:
            self.hide()
