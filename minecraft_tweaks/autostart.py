"""Автозагрузка клиента: HKCU Run на Windows, ~/.config/autostart на Linux.

Прав администратора не нужно, запись живёт только у текущего пользователя.
На Windows пишем через winreg: reg.exe спотыкается на кавычках в пути.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "MinecraftTweaks"
RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
DESKTOP_FILE = "minecraft-tweaks.desktop"


def launch_command() -> str:
    """Команда, которая поднимает клиент в фоне."""
    exe = sys.executable
    entry = Path(sys.argv[0]).resolve()
    if sys.platform == "win32":
        pyw = Path(exe).with_name("pythonw.exe")
        if pyw.is_file():
            exe = str(pyw)
    return f'"{exe}" "{entry}"'


def enable(command: str | None = None) -> bool:
    cmd = command or launch_command()
    if sys.platform == "win32":
        import winreg

        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_PATH, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            finally:
                winreg.CloseKey(key)
            return True
        except OSError:
            return False

    try:
        target = _desktop_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP_NAME}\n"
            f"Exec={cmd}\n"
            "X-GNOME-Autostart-enabled=true\n"
            "Terminal=false\n",
            encoding="utf-8")
        return True
    except OSError:
        return False


def disable() -> bool:
    if sys.platform == "win32":
        import winreg

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_PATH, 0, winreg.KEY_SET_VALUE)
        except OSError:
            return False
        try:
            winreg.DeleteValue(key, APP_NAME)
            return True
        except OSError:
            return False
        finally:
            winreg.CloseKey(key)

    try:
        _desktop_path().unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def status() -> str:
    """Строка для человека: включена, выключена или нет доступа."""
    if sys.platform == "win32":
        import winreg

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_PATH, 0, winreg.KEY_READ)
        except OSError:
            return "выключена"
        try:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return f"включена: {value}"
        except OSError:
            return "выключена"
        finally:
            winreg.CloseKey(key)

    return "включена" if _desktop_path().is_file() else "выключена"


def _desktop_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "autostart" / DESKTOP_FILE
