"""Хуки жизненного цикла: «майнкрафт запустился», «вошёл в мир», «вышел».

Главная точка входа библиотеки::

    import minecraft_tweaks as mt

    @mt.on_start
    def started(mc):
        print("Minecraft найден:", mc.title)

    @mt.on_world
    def world(mc):
        print("вошли в мир:", mc.world)

    mt.run_forever(fps=144)
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from . import process
from .draw import Canvas
from .overlay import Overlay
from .process import MinecraftWindow

_start: list[Callable[[MinecraftWindow], None]] = []
_world: list[Callable[[MinecraftWindow], None]] = []
_exit: list[Callable[[MinecraftWindow], None]] = []


def on_start(fn: Callable[[MinecraftWindow], None] | None = None):
    """Вызывается, когда окно Minecraft появилось (один раз на запуск)."""
    def deco(f: Callable[[MinecraftWindow], None]):
        _start.append(f)
        return f
    return deco(fn) if fn is not None else deco


def on_world(fn: Callable[[MinecraftWindow], None] | None = None):
    """Вызывается при входе в мир (и при смене мира)."""
    def deco(f: Callable[[MinecraftWindow], None]):
        _world.append(f)
        return f
    return deco(fn) if fn is not None else deco


def on_exit(fn: Callable[[MinecraftWindow], None] | None = None):
    """Вызывается, когда окно Minecraft исчезло."""
    def deco(f: Callable[[MinecraftWindow], None]):
        _exit.append(f)
        return f
    return deco(fn) if fn is not None else deco


def run_forever(render: Optional[Callable[[Canvas, Overlay, MinecraftWindow], None]] = None,
                *, fps: int = 144, hide_unfocused: bool = True,
                stop: Optional[Callable[[], bool]] = None,
                overlay: Overlay | None = None) -> None:
    """Главный цикл: следит за окном игры и рисует кадры.

    render(canvas, overlay, mc) вызывается каждый кадр, когда игра активна.
    """
    ov = overlay or Overlay(fps=fps)
    ov.open()
    last_title: Optional[str] = None
    running: MinecraftWindow | None = None
    created: set[str] = set()

    try:
        while not (stop and stop()):
            mc = process.find()
            if mc is None:
                if running is not None:
                    for fn in _exit:
                        fn(running)
                    running = None
                    last_title = None
                    created.clear()
                ov.hide()
                time.sleep(0.25)
                continue

            if running is None or running.pid != mc.pid:
                running = mc
                if mc.pid not in created:
                    created.add(mc.pid)
                    for fn in _start:
                        fn(mc)

            if mc.is_world and mc.title != last_title:
                last_title = mc.title
                for fn in _world:
                    fn(mc)
            elif not mc.is_world:
                last_title = mc.title

            if hide_unfocused and not mc.focused():
                ov.hide()
                time.sleep(0.05)
                continue

            ov.follow(mc)
            if render is not None:
                ov.canvas.clear()
                render(ov.canvas, ov, mc)
                ov.present()
            time.sleep(1.0 / max(1, fps))
    finally:
        for fn in _exit:
            if running is not None:
                fn(running)
        ov.close()
