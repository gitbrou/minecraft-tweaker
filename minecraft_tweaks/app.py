"""App собирает оверлей, ESP, GUI и ваши расширения.

Один объект, один вызов ``run()``::

    import minecraft_tweaks as mt

    @mt.esp_block("diamond_ore")
    def diamonds():
        return [(10, 5, 3)]

    app = mt.App(fps=144)
    app.run()
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from . import process
from .draw import Canvas
from .esp import Camera, ESPRenderer, EspSettings
from .extensions import REGISTRY, Registry
from .gui import ClickGui, Module
from .keys import VK_LBUTTON, Combo, Keys
from .overlay import Overlay

TEXT = 0xFFF2F2F5
TEXT_DIM = 0xFFA8A8B3
ACCENT = 0xFF7C5CFF


class App:
    """Приложение-оверлей: держит окно, рисует ESP/GUI и зовёт ваши функции."""

    def __init__(self, *, fps: int = 144, esp: EspSettings | None = None,
                 registry: Registry | None = None, gui: bool = True,
                 overlay: Overlay | None = None, require_arm: bool = False,
                 show_hud: bool = True) -> None:
        self.registry = registry or REGISTRY
        self.overlay = overlay or Overlay(fps=fps)
        self.esp = ESPRenderer(esp or EspSettings())
        self.gui: ClickGui | None = ClickGui({}, on_toggle=self._on_toggle) if gui else None
        self.gui_open = False
        self.require_arm = require_arm
        self.show_hud = show_hud

        self.camera = Camera(0, 0, 0, 0, 0, fov=70)
        self.keys = Keys()
        self.arming = Combo(["S", "R", "R"], modifier="ALT")
        self.armed = False
        self._last_lmb = False
        self._last_time = time.perf_counter()
        self.last_frame_ms = 0.0

    # -- служебное ---------------------------------------------------------
    def _on_toggle(self, module: Module) -> None:
        self.registry.toggle(module.name, module.enabled)

    def _sync_categories(self) -> None:
        if self.gui is None:
            return
        cats: dict[str, list[Module]] = {}
        for mod in self.registry.modules:
            cats.setdefault(mod.category or "Custom", []).append(mod)
        for name, mods in self.gui.categories.items():
            bucket = cats.setdefault(name, [])
            for m in mods:
                if m not in bucket:
                    bucket.append(m)
        self.gui.categories = cats

    def _camera(self) -> Camera:
        return self.camera

    # -- кадр --------------------------------------------------------------
    def draw(self, canvas: Canvas, mc: process.MinecraftWindow | None = None) -> None:
        now = time.perf_counter()
        dt = now - self._last_time
        self._last_time = now
        t0 = now

        # арм-комбо и GUI-хоткей
        if self.arming.update():
            self.armed = True
        if self.keys.pressed("RSHIFT") and (self.armed or not self.require_arm):
            self.gui_open = not self.gui_open

        self._sync_categories()
        cam = self._camera()
        entities = self.registry.entities(cam)

        if not self.require_arm or self.armed:
            self.esp.draw(canvas, cam, entities, glow_phase=now * 3.0)

        self.registry.draw_extras(canvas, cam, self)
        self.registry.frame(dt, self)
        self.registry.draw_modules(canvas, self)

        if self.gui is not None and self.gui_open:
            lmb = self.keys.mouse_down(VK_LBUTTON)
            self.gui.draw(canvas, self.keys.cursor(), focused=True)
            hit = self.gui.click(self.keys.cursor(), lmb and not self._last_lmb)
            self._last_lmb = lmb
            del hit

        if self.show_hud:
            self._draw_hud(canvas, len(entities))

        self.last_frame_ms = (time.perf_counter() - t0) * 1000.0

    def _draw_hud(self, canvas: Canvas, entity_count: int) -> None:
        canvas.text("MT", 6, 6, ACCENT, 2)
        y = 22
        canvas.text(f"{self.overlay.stats.fps:4.0f} FPS", 6, y, TEXT, 1)
        y += 9
        canvas.text(f"{entity_count} targets", 6, y, TEXT_DIM, 1)
        y += 9
        canvas.text("armed" if self.armed else "disarmed", 6, y,
                    ACCENT if self.armed else TEXT_DIM, 1)
        if self.registry.errors:
            canvas.text(f"errors {len(self.registry.errors)}", 6, canvas.height - 14, 0xFFE05555, 1)

    # -- цикл --------------------------------------------------------------
    def run(self, *, follow: bool = True, hide_unfocused: bool = True,
            stop: Optional[Callable[[], bool]] = None) -> None:
        def render(canvas: Canvas, overlay: Overlay) -> None:
            self.draw(canvas)

        def should_stop() -> bool:
            if stop is not None and stop():
                return True
            return self.keys.down("SHIFT") and self.keys.down("ESC")

        self.overlay.loop(render, follow=follow, hide_unfocused=hide_unfocused,
                          should_stop=should_stop)

    def snapshot(self, path: str = "frame.bmp") -> None:
        """Сохранить кадр в BMP (удобно для тестов и отладки)."""
        import struct

        canvas = self.overlay.canvas
        w, h = canvas.width, canvas.height
        row = w * 4
        pixels = bytearray()
        for y in range(h - 1, -1, -1):
            row_data = bytearray(canvas.buf[y * row:(y + 1) * row])
            # BGRA -> BGRA (bmp 32bpp ждёт BGRA), альфу оставляем
            pixels += row_data
        header = struct.pack("<2sIHHI", b"BM", 14 + 40 + len(pixels), 0, 0, 14 + 40)
        info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 32, 0, len(pixels), 2835, 2835, 0, 0)
        with open(path, "wb") as f:
            f.write(header + info + pixels)
