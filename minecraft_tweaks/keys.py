"""Глобальные клавиши и мышь без хуков: опрос состояния клавиш.

Хуки не ставим специально: античиты и игры их не любят, а опрос
100 раз в секунду стоит копейки и работает даже когда окно не в фокусе.
На Windows источник GetAsyncKeyState, на Linux маска клавиш X11.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from . import _input

# --- виртуальные коды ------------------------------------------------------
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_ALT = 0x12
VK_SPACE = 0x20
VK_ESCAPE = 0x1B
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LALT = 0xA4
VK_RALT = 0xA5

NAMED = {
    "ALT": (VK_ALT, VK_LALT, VK_RALT),
    "CTRL": (VK_CONTROL, VK_LCONTROL, VK_RCONTROL),
    "SHIFT": (VK_SHIFT, VK_LSHIFT),
    "RSHIFT": (VK_RSHIFT,),
    "SPACE": (VK_SPACE,),
    "ESC": (VK_ESCAPE,),
}


def vk(key: int | str) -> int:
    """'R' -> 0x52, 'A' -> 0x41, 'ALT' -> 0x12."""
    if isinstance(key, int):
        return key
    k = key.upper()
    if k in NAMED:
        return NAMED[k][0]
    if len(k) == 1:
        return ord(k)
    if k.startswith("F") and k[1:].isdigit():
        return 0x6F + int(k[1:])
    raise ValueError(f"неизвестная клавиша: {key}")


def _down(vk_code: int) -> bool:
    return _input.down(vk_code)


class Keys:
    """Состояние клавиш + фронты (нажатие/отпускание)."""

    def __init__(self) -> None:
        self._prev: dict[int, bool] = {}

    def down(self, key: int | str) -> bool:
        if isinstance(key, str) and key.upper() in NAMED:
            return any(_down(c) for c in NAMED[key.upper()])
        return _down(vk(key))

    def pressed(self, key: int | str) -> bool:
        """True ровно в тот кадр, когда клавиша нажата."""
        code = vk(key)
        now = self.down(key)
        was = self._prev.get(code, False)
        self._prev[code] = now
        return now and not was

    def released(self, key: int | str) -> bool:
        code = vk(key)
        now = self.down(key)
        was = self._prev.get(code, True)
        self._prev[code] = now
        return (not now) and was

    # -- мышь --------------------------------------------------------------
    @staticmethod
    def mouse_down(button: int = VK_LBUTTON) -> bool:
        return _down(button)

    @staticmethod
    def cursor() -> tuple[int, int]:
        return _input.cursor()

    def modifiers(self) -> dict[str, bool]:
        return {name: any(_down(c) for c in codes)
                for name, codes in NAMED.items() if name in ("ALT", "CTRL", "SHIFT")}


@dataclass
class Combo:
    """Комбо вида «держим модификатор, нажимаем S, R, R», как в читах.

    Используется так: комбо == «взвести» макрос/оверлей.
    """

    sequence: Sequence[str] = ("S", "R", "R")
    modifier: str = "ALT"
    keys: Keys = field(default_factory=Keys)
    _step: int = 0
    _armed: bool = False

    def update(self) -> bool:
        """Возвращает True в момент, когда комбо целиком введено."""
        mod_down = self.keys.down(self.modifier)
        finished = False
        if not mod_down:
            self._step = 0
            return False
        # проверяем именно текущий шаг, чтобы порядок нельзя было перепутать
        want = self.sequence[self._step]
        if self.keys.pressed(want):
            self._step += 1
            if self._step >= len(self.sequence):
                self._step = 0
                finished = True
        # любые чужие нажатия сбрасывают последовательность
        for key in self.sequence:
            if key != want and self.keys.pressed(key):
                self._step = 0
        return finished

    def reset(self) -> None:
        self._step = 0


class Hotkey:
    """Простой хоткей с колбэком и фронтом."""

    def __init__(self, key: int | str, callback: Callable[[], None],
                 modifier: str | None = None) -> None:
        self.key = key
        self.callback = callback
        self.modifier = modifier
        self.keys = Keys()

    def poll(self) -> None:
        if self.modifier and not self.keys.down(self.modifier):
            return
        if self.keys.pressed(self.key):
            self.callback()
