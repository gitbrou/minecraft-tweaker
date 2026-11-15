"""Демо: ClickGUI + HUD, мышь читается глобально (клики проходят в игру).

Запуск:  python examples/gui_demo.py
Управление: ПКМ по строке — переключить модуль; Shift+Esc — выход.
"""

from __future__ import annotations

import time

import minecraft_tweaks as mt

CATEGORIES = {
    "Combat": [mt.Module("KillAura"), mt.Module("AimAssist"), mt.Module("TriggerBot"),
               mt.Module("Criticals"), mt.Module("Velocity")],
    "Movement": [mt.Module("Fly"), mt.Module("Speed"), mt.Module("NoFall"),
                 mt.Module("Step"), mt.Module("Scaffold")],
    "Render": [mt.Module("PlayerESP"), mt.Module("StorageESP"), mt.Module("Tracers"),
               mt.Module("Chams"), mt.Module("FullBright")],
    "Client": [mt.Module("Config"), mt.Module("Scripts"), mt.Module("Plugins"),
               mt.Module("Profiles")],
}


def main() -> None:
    keys = mt.Keys()
    gui = mt.ClickGui(CATEGORIES, title="minecraft-tweaks")
    for name in ("PlayerESP", "Tracers", "NoFall"):
        m = gui.find(name)
        if m:
            m.enabled = True

    ov = mt.Overlay(fps=120, click_through=True)
    last_lmb = False
    started = time.perf_counter()

    def render(canvas, overlay, _mc):
        nonlocal last_lmb
        lmb = keys.mouse_down(mt.VK_LBUTTON)
        gui.draw(canvas, keys.cursor(), focused=True)
        hit = gui.click(keys.cursor(), lmb and not last_lmb)
        last_lmb = lmb
        if hit is not None:
            print(f"{hit.name}: {'вкл' if hit.enabled else 'выкл'}")

        # нижняя плашка со списком включённого
        on = gui.enabled()
        canvas.text(f"active {len(on)}", 10, canvas.height - 18, 0xFF7C5CFF, 1)
        for i, m in enumerate(on[:8]):
            canvas.text(m.name, 10, canvas.height - 30 - i * 9, 0xFFA8A8B3, 1)

    try:
        ov.loop(render, follow=True, hide_unfocused=True,
                should_stop=lambda: keys.down("SHIFT") and keys.down("ESC"))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
