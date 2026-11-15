"""Точка входа: python -m minecraft_tweaks [--version|--fps N|...]."""

from .watchdog import main

if __name__ == "__main__":
    raise SystemExit(main())
