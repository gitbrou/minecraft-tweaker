"""Watchdog: ждём Minecraft, цепляемся оверлеем, переподключаемся после рестарта.

Python-аналог ``mcinject.Watchdog`` из Java-клиента: пока игра не запущена,
тихо спим, как только окно появилось, стартуем оверлей/ESP/GUI, после закрытия
игры возвращаемся в ожидание.
"""

from __future__ import annotations

import time
from typing import Optional

from . import process


def wait_for_minecraft(timeout: Optional[float] = None, poll: float = 1.0,
                       world: bool = False, verbose: bool = False) -> Optional[process.MinecraftWindow]:
    """Ждать окно Minecraft. ``timeout=None`` означает ждать бесконечно."""
    deadline = None if timeout is None else time.monotonic() + timeout
    announced = False
    while True:
        mc = process.find()
        if mc is not None and (not world or mc.is_world):
            return mc
        if verbose and not announced:
            print("[watchdog] ждём Minecraft…", flush=True)
            announced = True
        if deadline is not None and time.monotonic() >= deadline:
            return None
        time.sleep(poll)


def run_client(*, fps: int = 144, esp: bool = True, gui: bool = True,
               require_arm: bool = True, world: bool = False,
               verbose: bool = True, poll: float = 1.0) -> None:
    """Крутить клиент, пока не остановят (Ctrl+C), и переподключается к игре."""
    from .app import App
    from .esp import EspSettings

    while True:
        mc = wait_for_minecraft(world=world, poll=poll, verbose=verbose)
        if verbose:
            print(f"[watchdog] minecraft: {mc.title!r} pid={mc.pid}", flush=True)
        app = App(fps=fps, esp=EspSettings() if esp else None,
                  gui=gui, require_arm=require_arm, show_hud=gui)
        try:
            app.run(stop=lambda: process.find() is None)
        except KeyboardInterrupt:
            return
        if verbose:
            print("[watchdog] игра закрыта, ждём снова", flush=True)
        time.sleep(0.5)


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="minecraft-tweaks",
                                 description="Клиент поверх окна Minecraft: ESP, ClickGUI, HUD")
    ap.add_argument("--version", action="store_true", help="показать версию и выйти")
    ap.add_argument("--fps", type=int, default=144, help="целевой FPS оверлея")
    ap.add_argument("--no-esp", action="store_true", help="не рисовать ESP")
    ap.add_argument("--no-gui", action="store_true", help="без ClickGUI и HUD")
    ap.add_argument("--no-arm", action="store_true", help="не требовать комбо ALT+S,R,R")
    ap.add_argument("--world", action="store_true", help="ждать именно загрузки мира")
    ap.add_argument("--once", action="store_true", help="выйти после закрытия игры")
    ap.add_argument("-q", "--quiet", action="store_true", help="без сообщений")
    ap.add_argument("--autostart", choices=("on", "off", "status"),
                    help="добавить клиент в автозагрузку или показать статус")
    args = ap.parse_args(argv)

    if args.autostart:
        from . import autostart
        if args.autostart == "on":
            ok = autostart.enable()
            print(f"[autostart] {'включена' if ok else 'не вышло'}: {autostart.launch_command()}")
            return 0 if ok else 1
        if args.autostart == "off":
            ok = autostart.disable()
            print(f"[autostart] {'выключена' if ok else 'не найдена'}")
            return 0 if ok else 1
        print(f"[autostart] {autostart.status()}")
        return 0

    if args.version:
        from . import __version__
        print(f"minecraft-tweaks {__version__}")
        return 0

    if args.once:
        mc = wait_for_minecraft(world=args.world, verbose=not args.quiet)
        if mc is None:
            return 1
        from .app import App
        from .esp import EspSettings
        App(fps=args.fps, esp=None if args.no_esp else EspSettings(),
            gui=not args.no_gui, require_arm=not args.no_arm,
            show_hud=not args.no_gui).run(stop=lambda: process.find() is None)
        return 0

    try:
        run_client(fps=args.fps, esp=not args.no_esp, gui=not args.no_gui,
                   require_arm=not args.no_arm, world=args.world,
                   verbose=not args.quiet)
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
