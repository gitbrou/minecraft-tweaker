"""Расширения: свои источники сущностей, свои блоки, свои модули и отрисовка.

Идея: декораторы в одну строку. Пользователь пишет обычную функцию и вешает
на неё декоратор, библиотека сама вызывает её каждый кадр.

    import minecraft_tweaks as mt

    @mt.esp_entity                      # свои сущности
    def mobs():
        return [mt.Entity(10, 0, 5, kind="mob")]

    @mt.esp_block("diamond_ore")        # свой ESP для любого блока
    def diamonds():
        return [(12, 5, -3), (14, 6, -1)]

    @mt.esp_draw                        # своя отрисовка поверх всего
    def watermark(canvas, cam, app):
        canvas.text("my client", 10, 10, 0xFFFFFFFF)
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from .draw import Canvas
from .esp import Camera, Entity
from .gui import Module

__all__ = [
    "Registry",
    "BlockEsp",
    "registry",
    "esp_entity",
    "esp_block",
    "esp_draw",
    "on_frame",
    "module",
    "load_scripts",
    "REGISTRY",
]

EntitySource = Callable[[], Iterable[Entity]]
BlockSource = Callable[[], Iterable[Sequence[float] | tuple[float, float, float]]]
DrawHook = Callable[[Canvas, Camera, Any], None]
FrameHook = Callable[[float, Any], None]


@dataclass
class BlockEsp:
    """Свой ESP для блоков: имя, цвет, подпись, дальность."""

    block: str
    color: int = 0xFF00E5FF
    box: bool = True
    label: bool = True
    max_distance: float = 64.0
    source: BlockSource | None = None
    height: float = 1.0


@dataclass
class ModuleHooks:
    tick: Callable[[float], None] | None = None
    draw: Callable[[Canvas, Any], None] | None = None
    toggle: Callable[[bool], None] | None = None


@dataclass
class Registry:
    """Всё, что пользователь зарегистрировал."""

    entity_sources: list[EntitySource] = field(default_factory=list)
    block_sources: list[BlockEsp] = field(default_factory=list)
    draw_hooks: list[DrawHook] = field(default_factory=list)
    frame_hooks: list[FrameHook] = field(default_factory=list)
    modules: list[Module] = field(default_factory=list)
    hooks: dict[str, ModuleHooks] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    # -- регистрация -------------------------------------------------------
    def add_entity_source(self, fn: EntitySource) -> EntitySource:
        self.entity_sources.append(fn)
        return fn

    def add_block_source(self, spec: BlockEsp) -> BlockEsp:
        if spec.source is None:
            raise ValueError("block spec без source")
        self.block_sources.append(spec)
        return spec

    def add_draw_hook(self, fn: DrawHook) -> DrawHook:
        self.draw_hooks.append(fn)
        return fn

    def add_frame_hook(self, fn: FrameHook) -> FrameHook:
        self.frame_hooks.append(fn)
        return fn

    def add_module(self, module: Module) -> Module:
        self.modules.append(module)
        self.hooks.setdefault(module.name, ModuleHooks())
        return module

    def module_hooks(self, name: str) -> ModuleHooks:
        return self.hooks.setdefault(name, ModuleHooks())

    # -- сбор данных -------------------------------------------------------
    @staticmethod
    def _safe(label: str, fn: Callable[[], Any], default: Any, errors: list[str]) -> Any:
        try:
            return fn()
        except Exception:
            errors.append(f"{label}: {traceback.format_exc(limit=2)}")
            return default

    def entities(self, camera: Camera | None = None) -> list[Entity]:
        out: list[Entity] = []
        for src in self.entity_sources:
            res = self._safe(getattr(src, "__name__", "entity_source"), src, (), self.errors)
            for e in res or ():
                if isinstance(e, Entity):
                    out.append(e)
                elif isinstance(e, (tuple, list)) and len(e) >= 3:
                    out.append(Entity(float(e[0]), float(e[1]), float(e[2])))
        for spec in self.block_sources:
            res = self._safe(f"block:{spec.block}", spec.source, (), self.errors)
            for pos in res or ():
                if len(pos) < 3:
                    continue
                x, y, z = float(pos[0]), float(pos[1]), float(pos[2])
                if camera is not None:
                    d = ((x - camera.x) ** 2 + (y - camera.y) ** 2 + (z - camera.z) ** 2) ** 0.5
                    if d > spec.max_distance:
                        continue
                out.append(Entity(
                    x=x + 0.5, y=y, z=z + 0.5,
                    height=spec.height, kind="block",
                    color=spec.color,
                    label=spec.block if spec.label else None,
                ))
        return out

    def draw_extras(self, canvas: Canvas, camera: Camera, app: Any) -> None:
        for hook in self.draw_hooks:
            self._safe(getattr(hook, "__name__", "draw_hook"),
                       lambda h=hook: h(canvas, camera, app), None, self.errors)

    def frame(self, dt: float, app: Any) -> None:
        for hook in self.frame_hooks:
            self._safe(getattr(hook, "__name__", "frame_hook"),
                       lambda h=hook: h(dt, app), None, self.errors)
        for mod in self.modules:
            h = self.hooks.get(mod.name)
            if h and h.tick and mod.enabled:
                self._safe(f"tick:{mod.name}", lambda h=h: h.tick(dt), None, self.errors)

    def draw_modules(self, canvas: Canvas, app: Any) -> None:
        for mod in self.modules:
            h = self.hooks.get(mod.name)
            if h and h.draw and mod.enabled:
                self._safe(f"draw:{mod.name}",
                           lambda h=h: h.draw(canvas, app), None, self.errors)

    def toggle(self, name: str, enabled: bool) -> None:
        h = self.hooks.get(name)
        if h and h.toggle:
            self._safe(f"toggle:{name}", lambda: h.toggle(enabled), None, self.errors)


REGISTRY = Registry()
registry = REGISTRY


# --- декораторы ------------------------------------------------------------
def esp_entity(fn: EntitySource | None = None, *, reg: Registry | None = None):
    """@mt.esp_entity: источник сущностей (вызывается каждый кадр)."""
    def deco(f: EntitySource):
        (reg or REGISTRY).add_entity_source(f)
        return f
    return deco(fn) if fn is not None else deco


def esp_block(block: str, *, color: int = 0xFF00E5FF, box: bool = True,
              label: bool = True, max_distance: float = 64.0, height: float = 1.0,
              reg: Registry | None = None):
    """@mt.esp_block("diamond_ore"): ESP для своих блоков.

    Функция возвращает список координат углов блоков: [(x, y, z), ...].
    """
    def deco(fn: BlockSource):
        (reg or REGISTRY).add_block_source(BlockEsp(
            block=block, color=color, box=box, label=label,
            max_distance=max_distance, source=fn, height=height,
        ))
        return fn
    return deco


def esp_draw(fn: DrawHook | None = None, *, reg: Registry | None = None):
    """@mt.esp_draw: своя отрисовка: (canvas, camera, app) -> None."""
    def deco(f: DrawHook):
        (reg or REGISTRY).add_draw_hook(f)
        return f
    return deco(fn) if fn is not None else deco


def on_frame(fn: FrameHook | None = None, *, reg: Registry | None = None):
    """@mt.on_frame: логика каждый кадр: (dt, app) -> None."""
    def deco(f: FrameHook):
        (reg or REGISTRY).add_frame_hook(f)
        return f
    return deco(fn) if fn is not None else deco


class ModuleBuilder:
    """То, что возвращает @mt.module: цепочка настройки своего модуля."""

    def __init__(self, module: Module, reg: Registry) -> None:
        self.module = module
        self._reg = reg
        self._hooks = reg.module_hooks(module.name)

    def on_tick(self, fn: Callable[[float], None]) -> Callable[[float], None]:
        self._hooks.tick = fn
        return fn

    def on_draw(self, fn: Callable[[Canvas, Any], None]) -> Callable[[Canvas, Any], None]:
        self._hooks.draw = fn
        return fn

    def on_toggle(self, fn: Callable[[bool], None]) -> Callable[[bool], None]:
        self._hooks.toggle = fn
        return fn

    def enable(self) -> Module:
        self.module.enabled = True
        return self.module

    def __call__(self, cls):
        """Позволяет писать @mt.module(...) прямо над классом.

        Методы класса on_tick/on_draw/on_toggle становятся колбэками модуля.
        Возвращается ModuleBuilder, чтобы можно было добавить колбэки
        декораторами: @MyMod.on_draw.
        """
        for attr in ("on_tick", "on_draw", "on_toggle"):
            fn = getattr(cls, attr, None)
            if callable(fn):
                setattr(self._hooks, attr, fn)
        if getattr(cls, "enabled", False):
            self.module.enabled = True
        return self


def module(name: str, *, category: str = "Custom", enabled: bool = False,
           description: str = "", reg: Registry | None = None):
    """@mt.module("Мой модуль", category="Render"): модуль в ClickGUI.

    Возвращает ModuleBuilder: .on_tick, .on_draw, .on_toggle.
    """
    r = reg or REGISTRY
    mod = Module(name=name, enabled=enabled, description=description, category=category)
    r.add_module(mod)
    return ModuleBuilder(mod, r)


# --- свои скрипты ---------------------------------------------------------
def load_scripts(directory: str = "scripts", *, reg: Registry | None = None) -> list[str]:
    """Загрузить все *.py из папки: там можно просто писать декораторы.

    Файл скрипта выглядит как обычный код:

        import minecraft_tweaks as mt
        @mt.esp_block("gold_ore", color=0xFFFFC107)
        def gold():
            return [(0, 60, 0)]
    """
    import importlib.util
    from pathlib import Path

    found: list[str] = []
    base = Path(directory)
    if not base.exists():
        return found
    for path in sorted(base.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"mt_script_{path.stem}", path)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            found.append(path.name)
        except Exception:
            (reg or REGISTRY).errors.append(f"script {path.name}: {traceback.format_exc(limit=3)}")
    return found
