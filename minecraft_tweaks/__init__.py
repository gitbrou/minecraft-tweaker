"""minecraft-tweaks: оверлей, ESP и GUI для Minecraft на чистом Python.

Быстрый старт::

    import minecraft_tweaks as mt

    @mt.on_start
    def started(mc):
        print("Minecraft:", mc.title)

    ov = mt.Overlay(fps=144)
    esp = mt.ESPRenderer()

    def render(canvas, overlay, mc):
        cam = mt.Camera(0, 0, 0, 0, 0, fov=70)
        ents = [mt.Entity(5, 0, 10, kind="player", health=0.8)]
        esp.draw(canvas, cam, ents)
        canvas.text(f"FPS {overlay.stats.fps:.0f}", 10, 10, 0xFFFFFFFF)

    mt.run_forever(render, overlay=ov)
"""

from __future__ import annotations

from . import agent, process
from .app import App
from .draw import Canvas
from .esp import KIND_COLOR, Camera, Entity, ESPRenderer, EspSettings
from .extensions import (
    BlockEsp,
    Registry,
    esp_block,
    esp_draw,
    esp_entity,
    load_scripts,
    module,
    on_frame,
    registry,
)
from .gui import ClickGui, Module
from .hooks import on_exit, on_start, on_world, run_forever
from .keys import (
    Combo,
    Hotkey,
    Keys,
    VK_ALT,
    VK_CONTROL,
    VK_ESCAPE,
    VK_LBUTTON,
    VK_RBUTTON,
    VK_RSHIFT,
    VK_SHIFT,
    VK_SPACE,
    vk,
)
from .overlay import Overlay, OverlayStats
from .process import MinecraftWindow

__version__ = "0.3.0"

__all__ = [
    "agent",
    "process",
    "App",
    "Canvas",
    "Overlay",
    "OverlayStats",
    "MinecraftWindow",
    "Camera",
    "Entity",
    "ESPRenderer",
    "EspSettings",
    "KIND_COLOR",
    "ClickGui",
    "Module",
    "Registry",
    "BlockEsp",
    "esp_entity",
    "esp_block",
    "esp_draw",
    "on_frame",
    "module",
    "load_scripts",
    "registry",
    "Keys",
    "Combo",
    "Hotkey",
    "vk",
    "on_start",
    "on_world",
    "on_exit",
    "run_forever",
    "VK_ALT",
    "VK_CONTROL",
    "VK_ESCAPE",
    "VK_LBUTTON",
    "VK_RBUTTON",
    "VK_RSHIFT",
    "VK_SHIFT",
    "VK_SPACE",
]


def find() -> MinecraftWindow | None:
    """Найти окно Minecraft прямо сейчас."""
    return process.find()


def is_running() -> bool:
    """Запущен ли Minecraft (проверка по окну, без перебора процессов)."""
    return process.is_running()


def wait(timeout: float | None = None) -> MinecraftWindow | None:
    """Дождаться запуска Minecraft."""
    return process.wait(timeout)


def wait_world(timeout: float | None = None) -> MinecraftWindow | None:
    """Дождаться входа в мир."""
    return process.wait_world(timeout)
