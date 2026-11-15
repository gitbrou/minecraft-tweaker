"""Свои методы: ESP для любых блоков, свои сущности, свой модуль и отрисовка.

Этот файл — пример того, как «дописать своё» в три строки. Каждый блок
ниже независим: удалите ненужное, остальное продолжит работать.

Запуск:  python examples/custom.py
"""

from __future__ import annotations

import math
import time

import minecraft_tweaks as mt

# 1) Свои сущности. Функция вызывается каждый кадр, возвращает Entity.
@mt.esp_entity
def my_entities():
    t = time.perf_counter()
    return [
        mt.Entity(math.cos(t) * 6, 0, math.sin(t) * 6, kind="player", health=0.9),
        mt.Entity(math.cos(t + 2) * 9, 0, math.sin(t + 2) * 9, kind="mob"),
    ]


# 2) Свой ESP для ЛЮБОГО блока: возвращаем координаты углов блоков.
#    Цвет, подпись и дальность настраиваются прямо в декораторе.
@mt.esp_block("diamond_ore", color=0xFF00E5FF, label=True, max_distance=96)
def diamond_ores():
    return [(12, 5, -3), (14, 6, -1), (18, 4, 2)]


@mt.esp_block("ancient_debris", color=0xFFFF8A00, max_distance=64)
def debris():
    return [(-9, 12, 7)]


# 3) Своя отрисовка поверх всего кадра: (canvas, camera, app).
@mt.esp_draw
def watermark(canvas, camera, app):
    canvas.rounded(6, canvas.height - 40, 150, 32, 6, 0xF50C0C11)
    canvas.text("MY CLIENT 1.0", 12, canvas.height - 34, 0xFF7C5CFF, 1)
    canvas.text(f"{app.overlay.stats.fps:4.0f} FPS  {len(app.registry.entities(camera))} ENT",
                12, canvas.height - 22, 0xFFA8A8B3, 1)


# 4) Свой модуль: он появится в GUI и получит колбэки.
@mt.module("MyTracer", category="Render", enabled=True)
class MyTracer:
    pass


@MyTracer.on_draw
def _draw_tracer(canvas, app):
    canvas.text("my tracer", canvas.width - 80, 10, 0xFF7C5CFF, 1)


@MyTracer.on_toggle
def _on_toggle(enabled: bool):
    print("[custom] MyTracer:", "on" if enabled else "off")


# 5) Логика раз в кадр (dt в секундах).
@mt.on_frame
def spin_camera(dt: float, app):
    app.camera.yaw = (app.camera.yaw + 12.0 * dt) % 360.0


def main() -> None:
    print("свои скрипты из папки scripts:", mt.load_scripts("scripts"))
    app = mt.App(fps=144, require_arm=False)
    app.camera.y = 1.62
    print("ESC+SHIFT — выход; RShift — GUI (когда вооружено)")
    app.run()


if __name__ == "__main__":
    main()
