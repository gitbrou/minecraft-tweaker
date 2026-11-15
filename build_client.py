"""Сборка клиента одной командой.

    python build_client.py --compile            собрать Java-клиент и Python-клиент
    python build_client.py --compile --autostart on
    python build_client.py --autostart off
    python build_client.py --status

Java-часть собирается через ../mc-inject/build-all.ps1: он сам находит библиотеки,
выбирает случайные имена и кладёт в dist единый jar, маскированный exe и .bat.
Python-часть собирается в один .pyz через build-all.py из этой же папки.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JAVA_ROOT = ROOT.parent / "mc-inject"
RUN_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"


def run(cmd: list[str], cwd: Path) -> int:
    print("$ " + " ".join(str(c) for c in cmd))
    return subprocess.call([str(c) for c in cmd], cwd=str(cwd))


def build_java() -> Path | None:
    script = JAVA_ROOT / "build-all.ps1"
    if not script.is_file():
        print(f"[java] нет {script}")
        return None
    rc = run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)], JAVA_ROOT)
    if rc != 0:
        print(f"[java] сборка упала, код {rc}")
        return None
    jars = sorted((JAVA_ROOT / "dist").glob("*.jar"), key=lambda p: p.stat().st_mtime)
    if not jars:
        print("[java] dist пуст")
        return None
    jar = jars[-1]
    print(f"[java] готово: {jar}")
    return jar


def build_python() -> Path | None:
    script = ROOT / "build-all.py"
    if not script.is_file():
        print(f"[python] нет {script}")
        return None
    rc = run([sys.executable, str(script)], ROOT)
    if rc != 0:
        print(f"[python] сборка упала, код {rc}")
        return None
    pyz = sorted((ROOT / "dist").glob("*.pyz"), key=lambda p: p.stat().st_mtime)
    if not pyz:
        print("[python] dist пуст")
        return None
    print(f"[python] готово: {pyz[-1]}")
    return pyz[-1]


def java_autostart_command(jar: Path) -> str:
    """Команда автозапуска: маскированный exe из dist/runtime, иначе javaw."""
    base = jar.stem
    runtime = jar.parent / "runtime"
    exe = runtime / f"{base}.exe"
    if not exe.is_file():
        cand = sorted(runtime.glob("*.exe")) if runtime.is_dir() else []
        exe = cand[-1] if cand else None
    if exe is not None and exe.is_file():
        return f'"{exe}" -jar "{jar}"'
    javaw = Path(sys.executable).with_name("javaw.exe")
    launcher = str(javaw) if javaw.is_file() else "javaw"
    return f'"{launcher}" -jar "{jar}"'


def autostart_set(jar: Path, on: bool) -> int:
    if sys.platform != "win32":
        print("[autostart] этот сценарий только для Windows")
        return 1
    import winreg

    name = jar.stem
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_PATH, 0,
                                 winreg.KEY_SET_VALUE | winreg.KEY_READ)
    except OSError as exc:
        print(f"[autostart] нет доступа к реестру: {exc}")
        return 1
    try:
        if on:
            cmd = java_autostart_command(jar)
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, cmd)
            print(f"[autostart] включена под именем {name}: {cmd}")
        else:
            try:
                winreg.DeleteValue(key, name)
                print(f"[autostart] выключена: {name}")
            except FileNotFoundError:
                print(f"[autostart] записи {name} нет")
    except OSError as exc:
        print(f"[autostart] не вышло: {exc}")
        return 1
    finally:
        winreg.CloseKey(key)
    return 0


def autostart_status() -> None:
    if sys.platform != "win32":
        print("[autostart] статус доступен только на Windows")
        return
    import winreg

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_PATH, 0, winreg.KEY_READ)
    except OSError:
        print("[autostart] пусто")
        return
    try:
        count = winreg.QueryInfoKey(key)[1]
        rows = []
        for i in range(count):
            try:
                name, value, _ = winreg.EnumValue(key, i)
            except OSError:
                break
            if name.startswith("SearchHost") or name.startswith("RuntimeBroker") \
                    or "mc-inject" in value.replace("/", "\\"):
                rows.append(f"{name} = {value}")
        print("\n".join(rows) if rows else "[autostart] записей клиента нет")
    finally:
        winreg.CloseKey(key)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="build_client", description="Сборка SS-клиента")
    ap.add_argument("--compile", action="store_true", help="собрать оба клиента")
    ap.add_argument("--java", action="store_true", help="только Java-клиент")
    ap.add_argument("--python", action="store_true", help="только Python-клиент")
    ap.add_argument("--autostart", choices=("on", "off", "status"))
    args = ap.parse_args(argv)

    built_java: Path | None = None
    if args.compile or args.java or (not args.python and not args.autostart):
        built_java = build_java()
    if args.compile or args.python:
        build_python()

    if args.autostart == "status":
        autostart_status()
        return 0

    if args.autostart in ("on", "off"):
        if built_java is None:
            jars = sorted((JAVA_ROOT / "dist").glob("*.jar"), key=lambda p: p.stat().st_mtime)
            built_java = jars[-1] if jars else None
        if built_java is None:
            print("[autostart] нечего прописывать: сначала соберите --compile")
            return 1
        return autostart_set(built_java, args.autostart == "on")

    if built_java is not None:
        print()
        print("дальше:")
        print(f'  "{built_java}"            запуск вахтёра (ловит старт Minecraft и внедряет агент)')
        print(f'  "{built_java}" install    автозагрузка + вахтёр')
        print(f'  "{built_java}" autostart status')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
