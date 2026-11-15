"""Поиск окна и процесса Minecraft.

Без psutil: всё через Win32, чтобы библиотека работала «из коробки».
"""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass

from ._win import (
    HWND_TOPMOST,
    PROCESS_QUERY_LIMITED_INFORMATION,
    SWP_NOACTIVATE,
    SWP_NOZORDER,
    SW_RESTORE,
    WNDENUMPROC,
    kernel32,
    user32,
    wt,
)

TITLE_HINT = "Minecraft"


@dataclass(frozen=True)
class MinecraftWindow:
    hwnd: int
    title: str
    pid: int
    exe: str = ""

    @property
    def is_world(self) -> bool:
        """В мире заголовок выглядит как 'Minecraft 1.20.4 - Singleplayer'."""
        return " - " in self.title

    @property
    def world(self) -> str:
        return self.title.split(" - ", 1)[1] if " - " in self.title else ""

    def rect(self) -> tuple[int, int, int, int]:
        """(x, y, w, h) клиентской области в экранных координатах."""
        r = wt.RECT()
        if not user32.GetClientRect(self.hwnd, ctypes.byref(r)):
            return (0, 0, 0, 0)
        origin = wt.POINT(0, 0)
        user32.ClientToScreen(self.hwnd, ctypes.byref(origin))
        return (origin.x, origin.y, r.right - r.left, r.bottom - r.top)

    def focused(self) -> bool:
        return user32.GetForegroundWindow() == self.hwnd

    def focus(self) -> bool:
        """Вывести окно вперёд (использовать только по явному желанию игрока)."""
        if not self.hwnd:
            return False
        user32.ShowWindow(self.hwnd, SW_RESTORE)
        user32.SetWindowPos(self.hwnd, wt.HWND(HWND_TOPMOST), 0, 0, 0, 0,
                            SWP_NOACTIVATE | SWP_NOZORDER)
        return self.focused()


def _exe_of(pid: int) -> str:
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(len(buf))
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(h)


def windows(hint: str = TITLE_HINT) -> list[MinecraftWindow]:
    """Все видимые окна, в заголовке которых есть hint."""
    found: list[MinecraftWindow] = []

    @WNDENUMPROC
    def _cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, len(buf))
        title = buf.value
        if title and hint.lower() in title.lower():
            pid = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            found.append(MinecraftWindow(hwnd=hwnd, title=title, pid=pid.value))
        return True

    user32.EnumWindows(_cb, 0)
    return found


def find(hint: str = TITLE_HINT) -> MinecraftWindow | None:
    """Первое найденное окно Minecraft или None."""
    ws = windows(hint)
    if not ws:
        return None
    w = ws[0]
    return MinecraftWindow(w.hwnd, w.title, w.pid, _exe_of(w.pid))


def is_running(hint: str = TITLE_HINT) -> bool:
    return find(hint) is not None


def wait(timeout: float | None = None, poll: float = 0.5,
         hint: str = TITLE_HINT) -> MinecraftWindow | None:
    """Ждём появления окна Minecraft. timeout=None ждёт бесконечно."""
    started = time.time()
    while True:
        w = find(hint)
        if w is not None:
            return w
        if timeout is not None and time.time() - started > timeout:
            return None
        time.sleep(poll)


def wait_world(timeout: float | None = None, poll: float = 0.5,
               hint: str = TITLE_HINT) -> MinecraftWindow | None:
    """Ждём входа в мир (в заголовке появляется ' - <мир>')."""
    started = time.time()
    while True:
        w = find(hint)
        if w is not None and w.is_world:
            return w
        if timeout is not None and time.time() - started > timeout:
            return None
        time.sleep(poll)
