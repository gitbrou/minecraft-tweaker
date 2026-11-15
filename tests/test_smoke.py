"""Смоук-тест без игры: окно создаётся за экраном, кадры считаются.

Запуск:  python tests/test_smoke.py
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import minecraft_tweaks as mt


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"{'OK ' if ok else 'FAIL'} {name}{(' :: ' + detail) if detail else ''}")
    return ok


def main() -> int:
    ok = True

    # 1. детект
    mc = mt.find()
    ok &= check("process.find()", True, mc.title if mc else "Minecraft не запущен (это не ошибка)")

    # 2. canvas: примитивы и текст
    c = mt.Canvas(200, 100)
    c.clear()
    c.rounded(5, 5, 60, 20, 4, 0xFF7C5CFF)
    c.frame(70, 5, 40, 20, 0xFFE05A5A, 2)
    c.corners(5, 40, 40, 30, 0xFFEBC83C, 2)
    c.line(60, 40, 190, 90, 0xFFFFFFFF, 1, dash=3)
    c.text("SS 1.20.4 144FPS", 5, 80, 0xFFF2F2F5, 1)
    lit = sum(1 for i in range(0, len(c.buf), 4) if c.buf[i + 3] != 0)
    ok &= check("canvas primitives", lit > 1500, f"{lit} непрозрачных пикселей")

    # 3. ESP-проекция: цель прямо перед камерой должна быть в центре
    cam = mt.Camera(0, 0, 0, 0, 0, fov=70)
    proj = mt.ESPRenderer()
    p = proj.project(cam, 1920, 1080, (0, 0, 10))
    ok &= check("projection center", p is not None and abs(p[0] - 960) < 2 and abs(p[1] - 540) < 2,
                f"{p}")
    fired = proj.draw(c, cam, [mt.Entity(0, 0, 10, kind="player", health=0.7)])
    ok &= check("esp draw", fired == 1)

    # 4. GUI: клик по строке переключает модуль
    gui = mt.ClickGui({"Combat": [mt.Module("KillAura"), mt.Module("Velocity")]})
    gui.draw(c, (0, 0))
    hit = gui.click((gui._rows[0].x + 3, gui._rows[0].y + 3), True)
    ok &= check("gui toggle", hit is not None and hit.enabled, hit.name if hit else "промах")

    # 5. оверлей: окно создаётся за пределами экрана, кадры реально отправляются
    ov = mt.Overlay(fps=144, name="minecraft-tweaks smoke")
    ov.open()
    ov._ensure_surface(640, 360)
    ov._pos.x, ov._pos.y = -20000, -20000  # чтобы окно не мелькало
    t0 = time.perf_counter()
    frames = 0
    for i in range(120):
        ov.canvas.clear()
        ov.canvas.text(f"frame {i}", 10, 10, 0xFFFFFFFF, 1)
        proj.draw(ov.canvas, cam, [mt.Entity(math.sin(i / 10) * 2, 0, 8, kind="mob")])
        if ov.present():
            frames += 1
    dt = time.perf_counter() - t0
    ok &= check("overlay present", frames == 120, f"{frames}/120 кадров, {frames / dt:.0f} fps, "
                                                 f"ошибок {ov.stats.present_errors}")
    ov.close()

    # 6. хоткей-хелпер
    ok &= check("vk()", mt.vk("R") == 0x52 and mt.vk("ALT") == 0x12)

    # 7. расширения: свои сущности, свои блоки, свои модули и отрисовка
    reg = mt.Registry()

    @mt.esp_entity(reg=reg)
    def _ents():
        return [mt.Entity(0, 0, 5, kind="player", health=0.5)]

    @mt.esp_block("diamond_ore", color=0xFF00E5FF, reg=reg)
    def _ores():
        return [(1, 2, 3), (4, 5, 6)]

    @mt.esp_draw(reg=reg)
    def _extra(canvas, camera, app):
        canvas.text("extra", 0, 0, 0xFFFFFFFF)

    @mt.module("MyMod", category="Custom", reg=reg)
    class _MyMod:
        pass

    ticks: list[float] = []

    @_MyMod.on_tick
    def _tick(dt):
        ticks.append(dt)

    _MyMod.enable()

    ents = reg.entities(mt.Camera(0, 0, 0, 0, 0))
    kinds = sorted({e.kind for e in ents})
    ok &= check("custom entity provider", any(e.kind == "player" for e in ents))
    ok &= check("custom block esp", sum(1 for e in ents if e.kind == "block") == 2, str(kinds))
    ok &= check("custom module registered", reg.modules[0].name == "MyMod"
                and reg.modules[0].category == "Custom")

    c2 = mt.Canvas(320, 180)
    app = mt.App(fps=60, registry=reg, show_hud=True)
    app.camera = cam
    app.draw(c2)
    ok &= check("App.draw", (not reg.errors) and bool(ticks), f"errors={reg.errors[:1]} ticks={len(ticks)}")

    print("\nRESULT", "ok" if ok else "fail")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
