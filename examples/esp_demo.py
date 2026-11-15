"""Демо: плавный ESP с интерполяцией на «живых» мишенях.

Данные здесь синтетические — цель показать, что рендер сам по себе
гладкий (144 кадра/с, интерполяция по partial_tick). Как только у вас
появятся настоящие сущности, замените ``demo_entities()`` своим источником.

Запуск:  python examples/esp_demo.py
"""

from __future__ import annotations

import math
import time

import minecraft_tweaks as mt

FPS = 144
TICK = 1 / 20  # один тик Minecraft


def demo_entities(t: float) -> list[mt.Entity]:
    """Три мишени, которые двигаются тиками, как настоящие мобы."""
    tick_no = int(t / TICK)
    server_t = tick_no * TICK  # «серверное» время: 20 Гц
    partial = (t - server_t) / TICK  # аналог partialTick

    ents = []
    for i, kind in enumerate(("player", "mob", "storage")):
        angle = server_t * (0.6 + 0.25 * i) + i * 2.1
        radius = 6 + i * 2
        x = math.cos(angle) * radius
        z = math.sin(angle) * radius
        nxt = server_t + TICK
        nx = math.cos(nxt * (0.6 + 0.25 * i) + i * 2.1) * radius
        nz = math.sin(nxt * (0.6 + 0.25 * i) + i * 2.1) * radius
        ents.append(mt.Entity(
            x=x, y=0.0, z=z,
            height=1.8 if kind == "player" else (1.0 if kind == "storage" else 1.4),
            kind=kind,
            vx=(nx - x) / TICK, vy=0.0, vz=(nz - z) / TICK,
            health=0.85 if kind == "player" else None,
            name=f"bot{i}" if kind == "player" else None,
        ))
    return ents, partial


def main() -> None:
    mc = mt.find()
    if mc is None:
        print("Minecraft не запущен — ESP покажу поверх рабочего стола через 5 секунд")
    else:
        print("Minecraft найден:", mc.title)

    ov = mt.Overlay(fps=FPS)
    esp = mt.ESPRenderer(mt.EspSettings(tracers=True, names=True))
    cam = mt.Camera(0, 1.62, 0, 0, 0, fov=70)
    started = time.perf_counter()

    def render(canvas, overlay, _mc):
        t = time.perf_counter() - started
        # камера медленно вращается, чтобы видеть плавность и рамок, и трейсеров
        cam.yaw = (t * 22.0) % 360.0
        ents, partial = demo_entities(t)
        esp.draw(canvas, cam, ents, partial_tick=partial, glow_phase=t * 3.0)
        canvas.text(f"{overlay.stats.fps:5.0f} FPS", 10, 10, 0xFFF2F2F5, 1)
        canvas.text("minecraft-tweaks / esp demo", 10, 22, 0xFFA8A8B3, 1)

    try:
        ov.loop(render, follow=mc is not None, hide_unfocused=mc is not None)
    except KeyboardInterrupt:
        print("остановлено")


if __name__ == "__main__":
    main()
