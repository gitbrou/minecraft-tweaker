"""Рисование в ARGB-буфер.

Все примитивы пишут напрямую в ``bytearray`` (BGRA, как ждёт DIB),
поэтому кадр стоит дёшево и не зависит от GDI.
"""

from __future__ import annotations

import math
from typing import Sequence

# 5x7 пиксельный шрифт: 1 означает пиксель. Нижний регистр отображается заглавными.
_F: dict[str, tuple[str, ...]] = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    " ": ("00000",) * 7,
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
}

GLYPH_W, GLYPH_H, TRACKING = 5, 7, 1


def _premul(argb: int) -> bytes:
    a = (argb >> 24) & 0xFF
    r = (argb >> 16) & 0xFF
    g = (argb >> 8) & 0xFF
    b = argb & 0xFF
    if a != 255:
        r = r * a // 255
        g = g * a // 255
        b = b * a // 255
    return bytes((b, g, r, a))


class Canvas:
    """Пиксельный холст размером WxH (BGRA, top-down)."""

    __slots__ = ("width", "height", "buf", "_patterns")

    def __init__(self, width: int, height: int) -> None:
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.buf = bytearray(self.width * self.height * 4)
        self._patterns: dict[int, bytes] = {}

    # -- служебное ---------------------------------------------------------
    def _pat(self, argb: int) -> bytes:
        p = self._patterns.get(argb)
        if p is None:
            p = _premul(argb)
            self._patterns[argb] = p
        return p

    def resize(self, width: int, height: int) -> bool:
        if width == self.width and height == self.height:
            return False
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.buf = bytearray(self.width * self.height * 4)
        self._patterns.clear()
        return True

    def clear(self, argb: int = 0) -> None:
        if argb == 0:
            self.buf[:] = b"\x00" * len(self.buf)
        else:
            self.buf[:] = self._pat(argb) * (self.width * self.height)

    # -- примитивы ---------------------------------------------------------
    def fill_rect(self, x: int, y: int, w: int, h: int, argb: int) -> None:
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(self.width, int(x + w)), min(self.height, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        pat = self._pat(argb)
        row = pat * (x1 - x0)
        stride = self.width * 4
        buf = self.buf
        for yy in range(y0, y1):
            o = yy * stride + x0 * 4
            buf[o:o + len(row)] = row

    def frame(self, x: int, y: int, w: int, h: int, argb: int, thickness: int = 1) -> None:
        t = max(1, thickness)
        self.fill_rect(x, y, w, t, argb)
        self.fill_rect(x, y + h - t, w, t, argb)
        self.fill_rect(x, y, t, h, argb)
        self.fill_rect(x + w - t, y, t, h, argb)

    def corners(self, x: int, y: int, w: int, h: int, argb: int,
                thickness: int = 2, arm: int | None = None) -> None:
        """Рамка из четырёх уголков выглядит аккуратнее полной."""
        t = max(1, thickness)
        a = max(3, arm if arm is not None else min(w, h) // 3)
        for (cx, cy, dx, dy) in (
            (x, y, 1, 1),
            (x + w - 1, y, -1, 1),
            (x, y + h - 1, 1, -1),
            (x + w - 1, y + h - 1, -1, -1),
        ):
            sx = cx if dx > 0 else cx - a + 1
            sy = cy if dy > 0 else cy - t + 1
            self.fill_rect(sx, sy, a, t, argb)
            sx2 = cx if dx > 0 else cx - t + 1
            sy2 = cy if dy > 0 else cy - a + 1
            self.fill_rect(sx2, sy2, t, a, argb)

    def line(self, x0: float, y0: float, x1: float, y1: float, argb: int,
             thickness: int = 1, dash: int | None = None) -> None:
        steps = int(max(abs(x1 - x0), abs(y1 - y0)))
        if steps <= 0:
            self.fill_rect(int(x0), int(y0), thickness, thickness, argb)
            return
        t = max(1, thickness)
        for i in range(steps + 1):
            if dash and (i // dash) % 2 == 1:
                continue
            px = int(x0 + (x1 - x0) * i / steps)
            py = int(y0 + (y1 - y0) * i / steps)
            self.fill_rect(px, py, t, t, argb)

    def gradient_line(self, x0: float, y0: float, x1: float, y1: float,
                      argb: int, thickness: int = 1, fade_from: float = 0.15) -> None:
        """Линия с затуханием к началу (трассеры)."""
        steps = int(max(abs(x1 - x0), abs(y1 - y0)))
        if steps <= 0:
            return
        base_a = (argb >> 24) & 0xFF
        base = argb & 0x00FFFFFF
        for i in range(steps + 1):
            k = fade_from + (1.0 - fade_from) * i / steps
            a = int(base_a * k)
            px = int(x0 + (x1 - x0) * i / steps)
            py = int(y0 + (y1 - y0) * i / steps)
            self.fill_rect(px, py, thickness, thickness, (a << 24) | base)

    def rounded(self, x: int, y: int, w: int, h: int, radius: int, argb: int) -> None:
        r = max(0, min(radius, w // 2, h // 2))
        if r == 0:
            self.fill_rect(x, y, w, h, argb)
            return
        self.fill_rect(x + r, y, w - 2 * r, h, argb)
        self.fill_rect(x, y + r, r, h - 2 * r, argb)
        self.fill_rect(x + w - r, y + r, r, h - 2 * r, argb)
        for i in range(r):
            dx = r - int(math.sqrt(max(0, r * r - (r - i - 1) ** 2)))
            self.fill_rect(x + dx, y + i, w - 2 * dx, 1, argb)
            self.fill_rect(x + dx, y + h - 1 - i, w - 2 * dx, 1, argb)

    def hgradient(self, x: int, y: int, w: int, h: int, left: int, right: int) -> None:
        la, lr, lg, lb = (left >> 24) & 0xFF, (left >> 16) & 0xFF, (left >> 8) & 0xFF, left & 0xFF
        ra, rr, rg, rb = (right >> 24) & 0xFF, (right >> 16) & 0xFF, (right >> 8) & 0xFF, right & 0xFF
        for i in range(max(1, w)):
            k = i / max(1, w - 1)
            c = (
                (int(la + (ra - la) * k) << 24)
                | (int(lr + (rr - lr) * k) << 16)
                | (int(lg + (rg - lg) * k) << 8)
                | int(lb + (rb - lb) * k)
            )
            self.fill_rect(x + i, y, 1, h, c)

    def bar(self, x: int, y: int, w: int, h: int, fraction: float,
            fg: int, bg: int) -> None:
        self.fill_rect(x, y, w, h, bg)
        fill = int(max(0.0, min(1.0, fraction)) * w)
        if fill > 0:
            self.fill_rect(x, y, fill, h, fg)

    # -- текст -------------------------------------------------------------
    def text_width(self, s: str, scale: int = 1) -> int:
        if not s:
            return 0
        return (len(s) * (GLYPH_W + TRACKING) - TRACKING) * scale

    def text(self, s: str, x: int, y: int, argb: int, scale: int = 1,
             shadow: bool = True) -> None:
        if shadow:
            self._glyphs(s, x + scale, y + scale, (0xC0000000 | (argb & 0x00FFFFFF)), scale)
        self._glyphs(s, x, y, argb, scale)

    def _glyphs(self, s: str, x: int, y: int, argb: int, scale: int) -> None:
        cx = int(x)
        for ch in s:
            glyph = _F.get(ch.upper(), _F["?"])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        self.fill_rect(cx + gx * scale, y + gy * scale,
                                       scale, scale, argb)
            cx += (GLYPH_W + TRACKING) * scale

    def text_center(self, s: str, cx: int, y: int, argb: int, scale: int = 1,
                    shadow: bool = True) -> None:
        self.text(s, int(cx - self.text_width(s, scale) / 2), y, argb, scale, shadow)

    # -- картинки ----------------------------------------------------------
    def pixel_art(self, rows: Sequence[str], x: int, y: int, argb: int,
                  scale: int = 1, palette: dict[str, int] | None = None) -> None:
        for ry, row in enumerate(rows):
            for rx, ch in enumerate(row):
                if ch in (" ", ".", "0"):
                    continue
                col = palette[ch] if palette and ch in palette else argb
                self.fill_rect(x + rx * scale, y + ry * scale, scale, scale, col)
