"""ESP: проекция мира в экран и отрисовка рамок/иконок/дистанции.

Модуль ничего не знает про то, откуда берутся сущности: ему дают список
``Entity`` и ``Camera``. Это позволяет кормить его данными из любого
источника (мод, агент, пакеты, отладка) и тестировать без игры.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from .draw import Canvas

# --- цвета (ARGB) ----------------------------------------------------------
COL_PLAYER = 0xFF7C5CFF
COL_MOB = 0xFFE05A5A
COL_STORAGE = 0xFFEBC83C
COL_TEXT = 0xFFF2F2F5
COL_BG = 0x66000000
COL_HP_HIGH = 0xFF54E08A
COL_HP_MID = 0xFFE0C64A
COL_HP_LOW = 0xFFE05555

KIND_COLOR = {"player": COL_PLAYER, "mob": COL_MOB, "storage": COL_STORAGE}

_ICON_PLAYER = (
    "..XXX..",
    ".XXXXX.",
    ".X.X.X.",
    ".XXXXX.",
    "..XXX..",
    ".XXXXX.",
    "X.XXX.X",
)
_ICON_MOB = (
    "...X...",
    "..XXX..",
    ".XXXXX.",
    "XXXXXXX",
    ".XXXXX.",
    "..XXX..",
)
_ICON_STORAGE = (
    "XXXXXXXXX",
    "XXXXXXXXX",
    "X..X..X..",
    "XXXXXXXXX",
    "X..X..X..",
    "X..X..X..",
)


@dataclass
class Camera:
    x: float
    y: float
    z: float
    yaw: float      # градусы, как в Minecraft
    pitch: float    # градусы
    fov: float = 70.0
    aspect: float = 16 / 9

    def basis(self):
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        forward = (-sy * cp, -sp, cy * cp)
        right = (-cy, 0.0, -sy)
        up = (-sy * sp, cp, cy * sp)
        return forward, right, up


@dataclass
class Entity:
    x: float
    y: float
    z: float
    height: float = 1.8
    kind: str = "player"
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    health: float | None = None
    name: str | None = None
    color: int | None = None
    label: str | None = None

    def position(self, partial_tick: float = 1.0) -> tuple[float, float, float]:
        """Интерполяция как в ванилле: pos - delta * (1 - partialTick).

        Именно это убирает «ступеньки» 20 тиков/с: сервер двигает сущность
        20 раз в секунду, а рисуем мы 144 раза. Без интерполяции рамка
        дёргается.
        """
        if partial_tick >= 1.0:
            return self.x, self.y, self.z
        k = 1.0 - max(0.0, partial_tick)
        return self.x - self.vx * k, self.y - self.vy * k, self.z - self.vz * k


@dataclass
class EspSettings:
    boxes: bool = True
    corners: bool = True
    icons: bool = True
    distance: bool = True
    names: bool = False
    health: bool = True
    tracers: bool = False
    glow: bool = True
    max_distance: float = 128.0
    min_box_px: float = 6.0


class ESPRenderer:
    """Рисует ESP в ``Canvas`` по камере и списку сущностей."""

    def __init__(self, settings: EspSettings | None = None) -> None:
        self.settings = settings or EspSettings()

    def project(self, cam: Camera, w: int, h: int, point: tuple[float, float, float]):
        """Возвращает (sx, sy, depth) или None, если точка за спиной/вне экрана."""
        fwd, right, up = cam.basis()
        vx, vy, vz = point[0] - cam.x, point[1] - cam.y, point[2] - cam.z
        zc = vx * fwd[0] + vy * fwd[1] + vz * fwd[2]
        if zc <= 0.15:
            return None
        xc = vx * right[0] + vy * right[1] + vz * right[2]
        yc = vx * up[0] + vy * up[1] + vz * up[2]
        tan_y = math.tan(math.radians(cam.fov) / 2.0)
        tan_x = tan_y * (w / max(1, h))
        sx = w / 2.0 + (xc / (zc * tan_x)) * (w / 2.0)
        sy = h / 2.0 - (yc / (zc * tan_y)) * (h / 2.0)
        return sx, sy, zc

    def draw(self, canvas: Canvas, cam: Camera, entities: Iterable[Entity],
             partial_tick: float = 1.0, glow_phase: float = 0.0) -> int:
        s = self.settings
        w, h = canvas.width, canvas.height
        tan_y = math.tan(math.radians(cam.fov) / 2.0)
        drawn = 0

        for ent in entities:
            px, py, pz = ent.position(partial_tick)
            dist = math.dist((px, py, pz), (cam.x, cam.y, cam.z))
            if dist > s.max_distance:
                continue

            feet = self.project(cam, w, h, (px, py, pz))
            head = self.project(cam, w, h, (px, py + ent.height, pz))
            if feet is None or head is None:
                continue

            height_px = abs(feet[1] - head[1])
            if height_px < s.min_box_px:
                continue
            width_px = height_px * 0.42
            cx = (feet[0] + head[0]) / 2.0
            left = int(cx - width_px / 2)
            right = int(cx + width_px / 2)
            top = int(min(feet[1], head[1]))
            bottom = int(max(feet[1], head[1]))

            color = ent.color if ent.color is not None else KIND_COLOR.get(ent.kind, COL_PLAYER)
            alpha = 255 - int(110 * min(1.0, dist / max(1.0, s.max_distance)))

            if s.glow:
                pulse = 55 + int(65 * (0.5 + 0.5 * math.sin(glow_phase)))
                glow_col = ((pulse << 24) | (color & 0x00FFFFFF))
                canvas.frame(left - 2, top - 2, right - left + 5, bottom - top + 5, glow_col, 1)

            box_col = ((alpha << 24) | (color & 0x00FFFFFF))
            if s.corners:
                canvas.corners(left, top, right - left, bottom - top, box_col, 2)
            elif s.boxes:
                canvas.frame(left, top, right - left, bottom - top, box_col, 1)

            if s.icons:
                self._icon(canvas, ent.kind, int(cx), top - 12, box_col)

            if s.health and ent.health is not None:
                frac = max(0.0, min(1.0, ent.health))
                hp_col = COL_HP_HIGH if frac > 0.6 else (COL_HP_MID if frac > 0.3 else COL_HP_LOW)
                canvas.bar(left, bottom + 3, max(10, right - left), 2, frac, hp_col, COL_BG)

            if s.distance:
                canvas.text(f"{int(dist)}M", right + 4, top, box_col, 1)

            if ent.label:
                canvas.text(ent.label, left, top - 10, box_col, 1)

            if s.names and ent.name:
                canvas.text_center(ent.name, int(cx), top - 11, COL_TEXT, 1)

            if s.tracers:
                canvas.gradient_line(w / 2, h - 2, cx, bottom, box_col, 1)

            drawn += 1

        return drawn

    @staticmethod
    def _icon(canvas: Canvas, kind: str, cx: int, y: int, color: int) -> None:
        art = _ICON_STORAGE if kind in ("storage", "block") else (_ICON_MOB if kind == "mob" else _ICON_PLAYER)
        width = max(len(r) for r in art)
        y = max(1, y)
        canvas.pixel_art(art, int(cx - width / 2), y, color)
