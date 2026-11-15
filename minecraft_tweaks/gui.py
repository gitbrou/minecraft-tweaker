"""ClickGUI: панели категорий, тумблеры, кнопки профилей.

Всё рисуется на том же ``Canvas``, что и ESP, поэтому GUI и оверлеи
выглядят одинаково и не требуют ни одной картинки.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .draw import Canvas

ACCENT = 0xFF7C5CFF
PANEL = 0xF50C0C11
TEXT = 0xFFF2F2F5
TEXT_DIM = 0xFFA8A8B3
HOVER = 0x14FFFFFF
PILL_OFF = 0xFF26262E
KNOB = 0xFFEDEDF2


@dataclass
class Module:
    name: str
    enabled: bool = False
    description: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    category: str = ""


@dataclass
class _RowHit:
    x: int
    y: int
    w: int
    h: int
    module: Module


class ClickGui:
    """Простое, но аккуратное меню в стиле «тёмное стекло».

    Использование::

        gui = ClickGui({"Combat": [Module("KillAura")], "Render": [Module("PlayerESP")]})
        gui.draw(canvas, cursor, focused=True)
        hit = gui.click(cursor, lmb_pressed=True)
    """

    def __init__(self, categories: dict[str, Iterable[Module]] | None = None, *,
                 margin: int = 8, gap: int = 8, row_h: int = 17,
                 max_columns: int = 4, title: str = "minecraft-tweaks",
                 on_toggle: Callable[[Module], None] | None = None) -> None:
        self.categories: dict[str, list[Module]] = {
            k: list(v) for k, v in (categories or {}).items()
        }
        self.on_toggle = on_toggle
        self.margin = margin
        self.gap = gap
        self.row_h = row_h
        self.max_columns = max_columns
        self.title = title
        self.search = ""
        self._rows: list[_RowHit] = []
        self._hovered: Module | None = None

    # -- поиск -------------------------------------------------------------
    def find(self, name: str) -> Module | None:
        for mods in self.categories.values():
            for m in mods:
                if m.name == name:
                    return m
        return None

    def toggle(self, name: str) -> Module | None:
        m = self.find(name)
        if m is not None:
            m.enabled = not m.enabled
        return m

    def enabled(self) -> list[Module]:
        return [m for mods in self.categories.values() for m in mods if m.enabled]

    # -- отрисовка ---------------------------------------------------------
    def draw(self, canvas: Canvas, cursor: tuple[int, int] = (0, 0),
             focused: bool = True) -> None:
        self._rows.clear()
        self._hovered = None

        cats = list(self.categories.items())
        if not cats:
            return
        cols = max(1, min(self.max_columns, len(cats)))
        usable = canvas.width - 2 * self.margin - (cols - 1) * self.gap
        col_w = max(120, usable // cols)
        total_h = canvas.height - 2 * self.margin - 24
        x0 = (canvas.width - (cols * col_w + (cols - 1) * self.gap)) // 2

        # заголовок
        title = f"{self.title.upper()}"
        canvas.text(title, x0 + 1, self.margin, TEXT, 2)
        hint = "RMB - settings   X - close"
        canvas.text(hint, canvas.width - self.margin - canvas.text_width(hint), self.margin + 4,
                    TEXT_DIM, 1)

        for i, (cat_name, mods) in enumerate(cats[:cols]):
            cx = x0 + i * (col_w + self.gap)
            cy = self.margin + 26
            filtered = [m for m in mods
                        if not self.search or self.search.lower() in m.name.lower()]
            rows = max(1, len(filtered))
            ch = min(total_h, 26 + rows * self.row_h + 8)

            canvas.rounded(cx, cy, col_w, ch, 8, PANEL)
            canvas.hgradient(cx + 8, cy + 1, col_w - 16, 1, ACCENT, 0x003C2A8F)
            canvas.text(cat_name.upper(), cx + 8, cy + 8, ACCENT, 1)
            canvas.text(str(len(filtered)), cx + col_w - 14, cy + 8, TEXT_DIM, 1)

            ry = cy + 24
            for m in filtered:
                hovered = focused and (cx + 2 <= cursor[0] <= cx + col_w - 2
                                       and ry <= cursor[1] <= ry + self.row_h - 1)
                if hovered:
                    canvas.fill_rect(cx + 2, ry, col_w - 4, self.row_h - 1, HOVER)
                    self._hovered = m
                canvas.text(m.name, cx + 8, ry + 5,
                            TEXT if m.enabled else TEXT_DIM, 1)
                self._pill(canvas, cx + col_w - 26, ry + 5, m.enabled)
                self._rows.append(_RowHit(cx + 2, ry, col_w - 4, self.row_h - 1, m))
                ry += self.row_h

    def _pill(self, canvas: Canvas, x: int, y: int, on: bool) -> None:
        w, h = 20, 9
        canvas.rounded(x, y, w, h, 4, ACCENT if on else PILL_OFF)
        kx = x + (w - 9) if on else x + 1
        canvas.rounded(kx, y + 1, 7, h - 2, 3, KNOB)

    # -- ввод --------------------------------------------------------------
    def click(self, cursor: tuple[int, int], lmb_pressed: bool) -> Module | None:
        """Возвращает модуль, у которого переключили тумблер."""
        if not lmb_pressed:
            return None
        for r in self._rows:
            if r.x <= cursor[0] <= r.x + r.w and r.y <= cursor[1] <= r.y + r.h:
                r.module.enabled = not r.module.enabled
                if self.on_toggle is not None:
                    self.on_toggle(r.module)
                return r.module
        return None

    @property
    def hovered(self) -> Module | None:
        return self._hovered
