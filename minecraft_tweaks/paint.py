"""Художественная графика поверх Canvas: сглаженные фигуры, градиенты, эффекты.

Всё работает с премультиплицированным BGRA-буфером Canvas, поэтому прозрачность
и наложения выглядят правильно. Координаты задаются в пикселях, цвет в 0xAARRGGBB.
"""

from __future__ import annotations

import math
import random
from typing import Iterable, Sequence

__all__ = [
    "aa_line", "polyline", "bezier", "disk", "ring", "arc", "polygon",
    "rounded_rect", "sdf_rounded_rect",
    "linear_gradient", "radial_gradient", "glow", "shadow",
    "blur", "vignette", "noise", "glass", "blend", "draw_clipped",
    "blit", "blit_rotated", "text_outlined", "text_shadow", "text_gradient",
    "sparkline", "progress_ring",
]


# ---------------------------------------------------------------- служебное

def _put(buf: bytearray, w: int, h: int, x: int, y: int,
         cov: float, r: int, g: int, b: int, a: float) -> None:
    """Наложить цвет с покрытием cov (0..1) и альфой a (0..1)."""
    if cov <= 0.0 or x < 0 or y < 0 or x >= w or y >= h:
        return
    sa = cov * a
    if sa <= 0.0:
        return
    i = (y * w + x) * 4
    if sa >= 0.998:
        buf[i] = b
        buf[i + 1] = g
        buf[i + 2] = r
        buf[i + 3] = 255
        return
    inv = 1.0 - sa
    buf[i] = min(255, int(buf[i] * inv + b * sa))
    buf[i + 1] = min(255, int(buf[i + 1] * inv + g * sa))
    buf[i + 2] = min(255, int(buf[i + 2] * inv + r * sa))
    buf[i + 3] = min(255, int(buf[i + 3] * inv + 255 * sa))


def _rgba(argb: int) -> tuple[int, int, int, float]:
    return ((argb >> 16) & 0xFF, (argb >> 8) & 0xFF, argb & 0xFF,
            ((argb >> 24) & 0xFF) / 255.0)


def _seg_dist(px: float, py: float, x0: float, y0: float,
              x1: float, y1: float) -> float:
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy
    if length2 <= 1e-9:
        return math.hypot(px - x0, py - y0)
    t = ((px - x0) * dx + (py - y0) * dy) / length2
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return math.hypot(px - (x0 + dx * t), py - (y0 + dy * t))


def sdf_rounded_rect(px: float, py: float, x: float, y: float,
                     w: float, h: float, radius: float) -> float:
    """Расстояние до скруглённого прямоугольника (отрицательное внутри)."""
    cx, cy = x + w / 2.0, y + h / 2.0
    hw, hh = max(0.0, w / 2.0 - radius), max(0.0, h / 2.0 - radius)
    qx = abs(px - cx) - hw
    qy = abs(py - cy) - hh
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    inside = min(max(qx, qy), 0.0)
    return outside + inside - radius


# ---------------------------------------------------------------- фигуры

def aa_line(c, x0: float, y0: float, x1: float, y1: float,
            argb: int, width: float = 1.0) -> None:
    """Сглаженная линия любой толщины."""
    r, g, b, a = _rgba(argb)
    half = max(0.5, width / 2.0)
    x_lo = max(0, int(min(x0, x1) - half - 1))
    x_hi = min(c.width - 1, int(max(x0, x1) + half + 1))
    y_lo = max(0, int(min(y0, y1) - half - 1))
    y_hi = min(c.height - 1, int(max(y0, y1) + half + 1))
    for py in range(y_lo, y_hi + 1):
        for px in range(x_lo, x_hi + 1):
            d = _seg_dist(px + 0.5, py + 0.5, x0, y0, x1, y1)
            cov = half + 0.5 - d
            if cov > 0.0:
                _put(c.buf, c.width, c.height, px, py, min(1.0, cov), r, g, b, a)


def polyline(c, points: Sequence[tuple[float, float]], argb: int,
             width: float = 1.0, closed: bool = False) -> None:
    pts = list(points)
    for i in range(len(pts) - 1):
        aa_line(c, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], argb, width)
    if closed and len(pts) > 2:
        aa_line(c, pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], argb, width)


def bezier(c, p0, p1, p2, p3=None, argb: int = 0xFFFFFFFF,
           width: float = 1.0, steps: int = 24) -> None:
    """Кубическая (4 точки) или квадратичная (3 точки) кривая Безье."""
    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        if p3 is None:
            x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
            y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
        else:
            x = (u ** 3) * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + (t ** 3) * p3[0]
            y = (u ** 3) * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + (t ** 3) * p3[1]
        pts.append((x, y))
    polyline(c, pts, argb, width)


def disk(c, cx: float, cy: float, radius: float, argb: int) -> None:
    r, g, b, a = _rgba(argb)
    x_lo = max(0, int(cx - radius - 1))
    x_hi = min(c.width - 1, int(cx + radius + 1))
    y_lo = max(0, int(cy - radius - 1))
    y_hi = min(c.height - 1, int(cy + radius + 1))
    for py in range(y_lo, y_hi + 1):
        dy = py + 0.5 - cy
        for px in range(x_lo, x_hi + 1):
            dx = px + 0.5 - cx
            cov = radius + 0.5 - math.hypot(dx, dy)
            if cov > 0.0:
                _put(c.buf, c.width, c.height, px, py, min(1.0, cov), r, g, b, a)


def ring(c, cx: float, cy: float, radius: float, thickness: float,
         argb: int, start: float = 0.0, end: float = 360.0) -> None:
    """Кольцо или дуга (углы в градусах, 0 означает вправо, дальше по часовой)."""
    r, g, b, a = _rgba(argb)
    half = max(0.5, thickness / 2.0)
    outer = radius + half + 1
    x_lo = max(0, int(cx - outer))
    x_hi = min(c.width - 1, int(cx + outer))
    y_lo = max(0, int(cy - outer))
    y_hi = min(c.height - 1, int(cy + outer))
    full = end - start >= 359.9
    for py in range(y_lo, y_hi + 1):
        dy = py + 0.5 - cy
        for px in range(x_lo, x_hi + 1):
            dx = px + 0.5 - cx
            dist = math.hypot(dx, dy)
            cov = half + 0.5 - abs(dist - radius)
            if cov <= 0.0:
                continue
            if not full:
                ang = math.degrees(math.atan2(dy, dx)) % 360.0
                inside = (start % 360.0) <= ang <= (end % 360.0) if end > start \
                    else (ang >= start % 360.0 or ang <= end % 360.0)
                if not inside:
                    continue
            _put(c.buf, c.width, c.height, px, py, min(1.0, cov), r, g, b, a)


def arc(c, cx: float, cy: float, radius: float, thickness: float,
        start: float, end: float, argb: int) -> None:
    ring(c, cx, cy, radius, thickness, argb, start, end)


def polygon(c, points: Sequence[tuple[float, float]], argb: int,
            samples: int = 3) -> None:
    """Заливка произвольного многоугольника со сглаживанием (суперсэмплинг)."""
    r, g, b, a = _rgba(argb)
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 3:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x_lo = max(0, int(min(xs)))
    x_hi = min(c.width - 1, int(max(xs)))
    y_lo = max(0, int(min(ys)))
    y_hi = min(c.height - 1, int(max(ys)))
    step = 1.0 / samples
    offsets = [(i + 0.5) * step for i in range(samples)]
    total = float(samples * samples)
    for py in range(y_lo, y_hi + 1):
        for px in range(x_lo, x_hi + 1):
            hits = 0
            for oy in offsets:
                sy = py + oy
                for ox in offsets:
                    sx = px + ox
                    inside = False
                    j = len(pts) - 1
                    for i in range(len(pts)):
                        xi, yi = pts[i]
                        xj, yj = pts[j]
                        if (yi > sy) != (yj > sy):
                            xcross = xi + (sy - yi) * (xj - xi) / (yj - yi)
                            if sx < xcross:
                                inside = not inside
                        j = i
                    if inside:
                        hits += 1
            if hits:
                _put(c.buf, c.width, c.height, px, py, hits / total, r, g, b, a)


def rounded_rect(c, x: float, y: float, w: float, h: float, radius: float,
                 argb: int) -> None:
    """Сглаженный скруглённый прямоугольник (аналитическое покрытие)."""
    r, g, b, a = _rgba(argb)
    radius = max(0.0, min(radius, min(w, h) / 2.0))
    x_lo = max(0, int(x - 1))
    x_hi = min(c.width - 1, int(x + w + 1))
    y_lo = max(0, int(y - 1))
    y_hi = min(c.height - 1, int(y + h + 1))
    for py in range(y_lo, y_hi + 1):
        for px in range(x_lo, x_hi + 1):
            d = sdf_rounded_rect(px + 0.5, py + 0.5, x, y, w, h, radius)
            cov = 0.5 - d
            if cov > 0.0:
                _put(c.buf, c.width, c.height, px, py, min(1.0, cov), r, g, b, a)


# ---------------------------------------------------------------- градиенты

def linear_gradient(c, x: float, y: float, w: float, h: float,
                    c1: int, c2: int, angle: float = 0.0,
                    radius: float = 0.0) -> None:
    """Линейный градиент под углом (0 слева направо, 90 сверху вниз)."""
    r1, g1, b1, a1 = _rgba(c1)
    r2, g2, b2, a2 = _rgba(c2)
    rad = math.radians(angle)
    dx, dy = math.cos(rad), math.sin(rad)
    span = abs(dx) * w + abs(dy) * h
    if span <= 0:
        return
    x_lo = max(0, int(x - 1))
    x_hi = min(c.width - 1, int(x + w + 1))
    y_lo = max(0, int(y - 1))
    y_hi = min(c.height - 1, int(y + h + 1))
    for py in range(y_lo, y_hi + 1):
        for px in range(x_lo, x_hi + 1):
            cov = 1.0
            if radius > 0:
                d = sdf_rounded_rect(px + 0.5, py + 0.5, x, y, w, h, radius)
                cov = min(1.0, max(0.0, 0.5 - d))
                if cov <= 0.0:
                    continue
            proj = ((px + 0.5 - x) * dx + (py + 0.5 - y) * dy) / span
            t = 0.0 if proj < 0 else (1.0 if proj > 1 else proj)
            _put(c.buf, c.width, c.height, px, py, cov,
                 int(r1 + (r2 - r1) * t),
                 int(g1 + (g2 - g1) * t),
                 int(b1 + (b2 - b1) * t),
                 a1 + (a2 - a1) * t)


def radial_gradient(c, cx: float, cy: float, radius: float,
                    inner: int, outer: int) -> None:
    r1, g1, b1, a1 = _rgba(inner)
    r2, g2, b2, a2 = _rgba(outer)
    x_lo = max(0, int(cx - radius - 1))
    x_hi = min(c.width - 1, int(cx + radius + 1))
    y_lo = max(0, int(cy - radius - 1))
    y_hi = min(c.height - 1, int(cy + radius + 1))
    for py in range(y_lo, y_hi + 1):
        dy = py + 0.5 - cy
        for px in range(x_lo, x_hi + 1):
            dx = px + 0.5 - cx
            t = math.hypot(dx, dy) / radius
            if t > 1.0:
                continue
            _put(c.buf, c.width, c.height, px, py, 1.0,
                 int(r1 + (r2 - r1) * t),
                 int(g1 + (g2 - g1) * t),
                 int(b1 + (b2 - b1) * t),
                 a1 + (a2 - a1) * t)


def glow(c, cx: float, cy: float, radius: float, argb: int,
         falloff: float = 2.2) -> None:
    """Мягкое свечение: ярче в центре, плавно гаснет к краю."""
    r, g, b, a = _rgba(argb)
    x_lo = max(0, int(cx - radius - 1))
    x_hi = min(c.width - 1, int(cx + radius + 1))
    y_lo = max(0, int(cy - radius - 1))
    y_hi = min(c.height - 1, int(cy + radius + 1))
    for py in range(y_lo, y_hi + 1):
        dy = py + 0.5 - cy
        for px in range(x_lo, x_hi + 1):
            dx = px + 0.5 - cx
            d = math.hypot(dx, dy) / radius
            if d >= 1.0:
                continue
            cov = (1.0 - d) ** falloff
            _put(c.buf, c.width, c.height, px, py, cov, r, g, b, a)


# ---------------------------------------------------------------- эффекты

def _mask_rounded(w: int, h: int, x: float, y: float, rw: float, rh: float,
                  radius: float) -> bytearray:
    mask = bytearray(w * h)
    for py in range(h):
        row = py * w
        for px in range(w):
            d = sdf_rounded_rect(px + 0.5 - x, py + 0.5 - y, 0, 0, rw, rh, radius)
            cov = 0.5 - d
            if cov > 0:
                mask[row + px] = 255 if cov >= 1 else int(cov * 255)
    return mask


def _blur_mask(mask: bytearray, w: int, h: int, radius: int) -> bytearray:
    if radius <= 0:
        return mask
    tmp = bytearray(w * h)
    win = radius * 2 + 1
    for y in range(h):
        row = y * w
        acc = 0
        for i in range(-radius, radius + 1):
            xi = min(w - 1, max(0, i))
            acc += mask[row + xi]
        for x in range(w):
            tmp[row + x] = acc // win
            add = mask[row + min(w - 1, x + radius + 1)]
            sub = mask[row + max(0, x - radius)]
            acc += add - sub
    out = bytearray(w * h)
    for x in range(w):
        acc = 0
        for i in range(-radius, radius + 1):
            yi = min(h - 1, max(0, i))
            acc += tmp[yi * w + x]
        for y in range(h):
            out[y * w + x] = acc // win
            acc += tmp[min(h - 1, y + radius + 1) * w + x] - tmp[max(0, y - radius) * w + x]
    return out


def shadow(c, x: float, y: float, w: float, h: float, radius: float = 8.0,
           spread: int = 10, argb: int = 0x66000000) -> None:
    """Мягкая тень под панелью (настоящее размытие маски)."""
    pad = spread * 2
    mw, mh = int(w) + pad * 2, int(h) + pad * 2
    if mw <= 0 or mh <= 0:
        return
    mask = _mask_rounded(mw, mh, pad, pad, w, h, radius)
    mask = _blur_mask(mask, mw, mh, max(1, spread))
    r, g, b, a = _rgba(argb)
    base_x = int(x) - pad
    base_y = int(y) - pad
    for py in range(mh):
        for px in range(mw):
            m = mask[py * mw + px]
            if not m:
                continue
            _put(c.buf, c.width, c.height, base_x + px, base_y + py,
                 m / 255.0, r, g, b, a)


def blur(c, radius: int = 2) -> None:
    """Размытие всего холста (по премультиплицированным каналам)."""
    if radius <= 0:
        return
    w, h, buf = c.width, c.height, c.buf
    win = radius * 2 + 1
    tmp = bytearray(len(buf))
    for ch in range(4):
        for y in range(h):
            row = y * w * 4 + ch
            acc = 0
            for i in range(-radius, radius + 1):
                acc += buf[row + min(w - 1, max(0, i)) * 4]
            for x in range(w):
                tmp[row + x * 4] = acc // win
                acc += buf[row + min(w - 1, x + radius + 1) * 4]
                acc -= buf[row + max(0, x - radius) * 4]
    for ch in range(4):
        for x in range(w):
            acc = 0
            for i in range(-radius, radius + 1):
                acc += tmp[min(h - 1, max(0, i)) * w * 4 + x * 4 + ch]
            for y in range(h):
                buf[y * w * 4 + x * 4 + ch] = acc // win
                acc += tmp[min(h - 1, y + radius + 1) * w * 4 + x * 4 + ch]
                acc -= tmp[max(0, y - radius) * w * 4 + x * 4 + ch]


def vignette(c, strength: float = 0.55) -> None:
    """Затемнение по краям кадра, «кинематографичный» акцент."""
    w, h, buf = c.width, c.height, c.buf
    cx, cy = w / 2.0, h / 2.0
    maxd = math.hypot(cx, cy)
    for y in range(h):
        dy = y + 0.5 - cy
        row = y * w * 4
        for x in range(w):
            dx = x + 0.5 - cx
            t = math.hypot(dx, dy) / maxd
            factor = 1.0 - strength * (t ** 2.2)
            i = row + x * 4
            buf[i] = int(buf[i] * factor)
            buf[i + 1] = int(buf[i + 1] * factor)
            buf[i + 2] = int(buf[i + 2] * factor)


def noise(c, amount: float = 0.06, seed: int = 0) -> None:
    """Лёгкое зерно поверх кадра (убирает «пластиковость» градиентов)."""
    rnd = random.Random(seed)
    w, h, buf = c.width, c.height, c.buf
    amp = max(0.0, min(1.0, amount)) * 255.0
    for i in range(0, len(buf), 4):
        d = int((rnd.random() - 0.5) * amp)
        buf[i] = min(255, max(0, buf[i] + d))
        buf[i + 1] = min(255, max(0, buf[i + 1] + d))
        buf[i + 2] = min(255, max(0, buf[i + 2] + d))


def glass(c, x: float, y: float, w: float, h: float, radius: float = 10.0,
          tint: int = 0x882A2A38, blur_px: int = 6,
          border: int = 0x33FFFFFF) -> None:
    """Стеклянная панель: размывает то, что под ней, и накрывает тоном."""
    xi, yi, wi, hi = int(x), int(y), int(w), int(h)
    if wi <= 0 or hi <= 0:
        return
    region_canvas = _sub(c, xi, yi, wi, hi)
    if region_canvas is not None:
        blur(region_canvas, blur_px)
        _paste(c, region_canvas, xi, yi, 1.0)
    rounded_rect(c, x, y, w, h, radius, tint)
    ring_rect(c, x + 0.5, y + 0.5, w - 1, h - 1, radius, border)


def ring_rect(c, x: float, y: float, w: float, h: float, radius: float,
              argb: int, thickness: float = 1.0) -> None:
    """Рамка скруглённого прямоугольника (обводка в 1 px по умолчанию)."""
    r, g, b, a = _rgba(argb)
    x_lo = max(0, int(x - 1))
    x_hi = min(c.width - 1, int(x + w + 1))
    y_lo = max(0, int(y - 1))
    y_hi = min(c.height - 1, int(y + h + 1))
    for py in range(y_lo, y_hi + 1):
        for px in range(x_lo, x_hi + 1):
            d = abs(sdf_rounded_rect(px + 0.5, py + 0.5, x, y, w, h, radius))
            cov = thickness / 2.0 + 0.5 - d
            if cov > 0:
                _put(c.buf, c.width, c.height, px, py, min(1.0, cov), r, g, b, a)


# ---------------------------------------------------------------- слои

def _sub(c, x: int, y: int, w: int, h: int):
    from .draw import Canvas
    out = Canvas(w, h)
    for row in range(h):
        sy = y + row
        if sy < 0 or sy >= c.height:
            continue
        sx = max(0, x)
        ex = min(c.width, x + w)
        if ex <= sx:
            continue
        src = (sy * c.width + sx) * 4
        dst = (row * w + (sx - x)) * 4
        out.buf[dst:dst + (ex - sx) * 4] = c.buf[src:src + (ex - sx) * 4]
    return out


def _paste(c, src, x: int, y: int, alpha: float) -> None:
    for row in range(src.height):
        for col in range(src.width):
            i = (row * src.width + col) * 4
            b, g, r, a = src.buf[i:i + 4]
            if a == 0:
                continue
            cov = a / 255.0
            _put(c.buf, c.width, c.height, x + col, y + row, cov,
                 r, g, b, (a / 255.0) * alpha)


def blend(c, src, x: int = 0, y: int = 0, alpha: float = 1.0) -> None:
    """Наложить другой холст (dither-free, с альфой слоя)."""
    _paste(c, src, x, y, alpha)


def draw_clipped(c, x: int, y: int, w: int, h: int, fn) -> None:
    """Рисует fn(temp) в область x,y,w,h; всё за границей обрезается."""
    from .draw import Canvas
    tmp = Canvas(w, h)
    fn(tmp)
    _paste(c, tmp, x, y, 1.0)


def blit(c, sprite_w: int, sprite_h: int, bgra: Sequence[int] | bytes | bytearray,
         x: int, y: int, alpha: float = 1.0, scale: float = 1.0) -> None:
    """Рисует спрайт (BGRA без премультипликации); scale может быть целым или дробным."""
    if scale <= 0:
        return
    dw = max(1, int(sprite_w * scale))
    dh = max(1, int(sprite_h * scale))
    for dy in range(dh):
        sy = min(sprite_h - 1, int(dy / scale))
        for dx in range(dw):
            sx = min(sprite_w - 1, int(dx / scale))
            i = (sy * sprite_w + sx) * 4
            b, g, r, a = bgra[i:i + 4]
            if a == 0:
                continue
            _put(c.buf, c.width, c.height, x + dx, y + dy,
                 a / 255.0, r, g, b, (a / 255.0) * alpha)


def blit_rotated(c, sprite_w: int, sprite_h: int,
                 bgra: Sequence[int] | bytes | bytearray,
                 cx: float, cy: float, angle_deg: float,
                 scale: float = 1.0, alpha: float = 1.0) -> None:
    """Спрайт с поворотом вокруг центра (обратная выборка, сглаженно)."""
    if scale <= 0:
        return
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    half_w, half_h = sprite_w * scale / 2.0, sprite_h * scale / 2.0
    reach = math.hypot(half_w, half_h) + 1
    x_lo = max(0, int(cx - reach))
    x_hi = min(c.width - 1, int(cx + reach))
    y_lo = max(0, int(cy - reach))
    y_hi = min(c.height - 1, int(cy + reach))
    for py in range(y_lo, y_hi + 1):
        dy = py + 0.5 - cy
        for px in range(x_lo, x_hi + 1):
            dx = px + 0.5 - cx
            u = (dx * cos_a + dy * sin_a) / scale + sprite_w / 2.0
            v = (-dx * sin_a + dy * cos_a) / scale + sprite_h / 2.0
            if u < 0 or v < 0 or u >= sprite_w or v >= sprite_h:
                continue
            i = (int(v) * sprite_w + int(u)) * 4
            b, g, r, a = bgra[i:i + 4]
            if a == 0:
                continue
            _put(c.buf, c.width, c.height, px, py, 1.0, r, g, b,
                 (a / 255.0) * alpha)


# ---------------------------------------------------------------- текст

def text_outlined(c, s: str, x: int, y: int, argb: int,
                  outline: int = 0xFF000000, scale: int = 1) -> None:
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        c.text(s, x + ox * scale, y + oy * scale, outline, scale)


def text_shadow(c, s: str, x: int, y: int, argb: int,
                shadow: int = 0x99000000, dx: int = 1, dy: int = 2,
                blur_pass: bool = False, scale: int = 1) -> None:
    c.text(s, x + dx, y + dy, shadow, scale)
    if blur_pass:
        c.text(s, x + dx + 1, y + dy, shadow, scale)
    c.text(s, x, y, argb, scale)


def text_gradient(c, s: str, x: int, y: int, c1: int, c2: int,
                  scale: int = 1) -> None:
    """Текст с вертикальным градиентом, рисуется построчно по глифам."""
    total = 7 * scale
    for row in range(total):
        t = row / max(1, total - 1)
        col = 0
        for shift in (24, 16, 8, 0):
            a1 = (c1 >> shift) & 0xFF
            a2 = (c2 >> shift) & 0xFF
            col |= int(a1 + (a2 - a1) * t) << shift
        _text_row(c, s, x, y + row, col, scale, row)


def _text_row(c, s: str, x: int, y: int, argb: int, scale: int, row: int) -> None:
    from .draw import _F, GLYPH_H, GLYPH_W, TRACKING
    cx = x
    for ch in s.upper():
        glyph = _F.get(ch)
        if glyph is None:
            cx += (GLYPH_W + TRACKING) * scale
            continue
        gy = row // scale
        if 0 <= gy < GLYPH_H and glyph[gy][row % scale * 0:]:
            bits = glyph[gy] if scale == 1 else glyph[gy]
            for gx, lit in enumerate(bits):
                if lit == "1":
                    c.fill_rect(cx + gx * scale, y, scale, 1, argb)
        cx += (GLYPH_W + TRACKING) * scale


# ---------------------------------------------------------------- данные

def sparkline(c, x: float, y: float, w: float, h: float,
              values: Iterable[float], argb: int = 0xFF7C5CFF,
              fill: int = 0x337C5CFF, width: float = 1.5) -> None:
    """График-искра по массиву значений (0..1)."""
    vals = [max(0.0, min(1.0, float(v))) for v in values]
    if len(vals) < 2:
        return
    pts = [(x + w * i / (len(vals) - 1), y + h * (1 - v)) for i, v in enumerate(vals)]
    if fill:
        poly = pts + [(x + w, y + h), (x, y + h)]
        polygon(c, poly, fill, samples=1)
    polyline(c, pts, argb, width)


def progress_ring(c, cx: float, cy: float, radius: float, value: float,
                  thickness: float = 4.0, track: int = 0x33FFFFFF,
                  argb: int = 0xFF7C5CFF) -> None:
    """Круговой прогресс с подсветкой для HUD и панелей."""
    ring(c, cx, cy, radius, thickness, track)
    end = -90 + 360 * max(0.0, min(1.0, value))
    ring(c, cx, cy, radius, thickness, argb, -90, end)
    glow(c, cx, cy, radius * 0.9, (argb & 0x00FFFFFF) | 0x22000000, falloff=3.0)
