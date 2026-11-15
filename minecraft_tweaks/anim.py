"""Анимации: кривые ускорения, твины и таймлайны.

Всё считается по времени в секундах, без потоков и сна.
"""

from __future__ import annotations

import math
import time
from typing import Callable, Iterable

Ease = Callable[[float], float]


def _clamp01(t: float) -> float:
    return 0.0 if t < 0 else (1.0 if t > 1 else t)


def linear(t: float) -> float:
    return _clamp01(t)


def quad_in(t: float) -> float:
    t = _clamp01(t)
    return t * t


def quad_out(t: float) -> float:
    t = _clamp01(t)
    return 1 - (1 - t) ** 2


def quad_inout(t: float) -> float:
    t = _clamp01(t)
    return 2 * t * t if t < 0.5 else 1 - 2 * (1 - t) ** 2


def cubic_in(t: float) -> float:
    t = _clamp01(t)
    return t ** 3


def cubic_out(t: float) -> float:
    t = _clamp01(t)
    return 1 - (1 - t) ** 3


def cubic_inout(t: float) -> float:
    t = _clamp01(t)
    return 4 * t ** 3 if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2


def expo_out(t: float) -> float:
    t = _clamp01(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def back_out(t: float) -> float:
    t = _clamp01(t)
    c = 1.70158
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def elastic_out(t: float) -> float:
    t = _clamp01(t)
    if t in (0.0, 1.0):
        return t
    c = (2 * math.pi) / 3
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * c) + 1


def bounce_out(t: float) -> float:
    t = _clamp01(t)
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


def sine_inout(t: float) -> float:
    t = _clamp01(t)
    return -(math.cos(math.pi * t) - 1) / 2


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1: int, c2: int, t: float) -> int:
    t = _clamp01(t)
    out = 0
    for shift in (24, 16, 8, 0):
        a = (c1 >> shift) & 0xFF
        b = (c2 >> shift) & 0xFF
        out |= int(a + (b - a) * t) << shift
    return out


def spring(t: float, damping: float = 6.0, frequency: float = 12.0) -> float:
    """Затухающая пружина 0→1 (для «живых» ховеров и открытий)."""
    if t <= 0:
        return 0.0
    return 1 - math.exp(-damping * t) * math.cos(frequency * t)


class Tween:
    """Одно значение, плавно идущее из from в to за duration секунд."""

    __slots__ = ("start", "end", "duration", "ease", "_t0", "loop", "pingpong")

    def __init__(self, start: float, end: float, duration: float = 0.3,
                 ease: Ease = cubic_out, loop: bool = False, pingpong: bool = False) -> None:
        self.start = start
        self.end = end
        self.duration = max(1e-6, duration)
        self.ease = ease
        self.loop = loop
        self.pingpong = pingpong
        self._t0 = time.perf_counter()

    def reset(self) -> None:
        self._t0 = time.perf_counter()

    def raw(self) -> float:
        return (time.perf_counter() - self._t0) / self.duration

    def value(self, now: float | None = None) -> float:
        t = self.raw() if now is None else now
        if self.loop:
            t = t % 1.0
            if self.pingpong and int(self.raw()) % 2 == 1:
                t = 1.0 - t
        return lerp(self.start, self.end, self.ease(t))

    def done(self) -> bool:
        return not self.loop and self.raw() >= 1.0


class Timeline:
    """Набор твинов, привязанных к общему времени старта."""

    def __init__(self) -> None:
        self._t0 = time.perf_counter()
        self._items: list[tuple[float, float, Tween]] = []

    def add(self, tween: Tween, at: float = 0.0, delay: float = 0.0) -> Tween:
        self._items.append((at + delay, (at + delay) + tween.duration, tween))
        return tween

    def reset(self) -> None:
        self._t0 = time.perf_counter()

    def elapsed(self) -> float:
        return time.perf_counter() - self._t0

    def value(self, tween: Tween) -> float:
        return tween.value(self.elapsed())


def stagger(items: Iterable[float], step: float = 0.04) -> list[float]:
    """Задержки для каскадного появления списка элементов."""
    return [i * step for i, _ in enumerate(items)]
