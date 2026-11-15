"""Подключение к живой игре (Java-агент), опциональная часть.

Библиотека полезна и без инжекта (детект + оверлей + ESP по своим данным).
Но если нужны реальные сущности, здесь лежит обёртка над нашим
Java-агентом из ``mc-inject``: он грузится в процесс игры и умеет
отдавать состояние.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from . import process

ROOT = Path(__file__).resolve().parents[2]  # ...\newlevel
DEFAULT_INJECT_DIR = ROOT / "mc-inject"
DEFAULT_STATE = DEFAULT_INJECT_DIR / "ss-state.json"


def _java(java: str = "java") -> str:
    return os.environ.get("MINECRAFT_TWEAKS_JAVA", java)


def attach(pid: int | None = None, *,
           jar: str | Path | None = None,
           classes: str | Path | None = None,
           options: str = "~",
           timeout: float = 60.0) -> bool:
    """Внедрить Java-агент в процесс игры.

    pid=None: окно Minecraft ищется само.
    Возвращает True, если Attacher отчитался успехом.
    """
    if pid is None:
        mc = process.find()
        if mc is None:
            raise RuntimeError("окно Minecraft не найдено")
        pid = mc.pid

    jar = Path(jar) if jar else _latest_agent_jar()
    classes = Path(classes) if classes else DEFAULT_INJECT_DIR / "out"
    if not jar.exists():
        raise FileNotFoundError(f"агент не найден: {jar}")
    if not classes.exists():
        raise FileNotFoundError(f"классы Attacher не найдены: {classes}")

    proc = subprocess.run(
        [_java(), "-cp", str(classes), "mcinject.Attacher", str(pid), options, str(jar)],
        capture_output=True, text=True, timeout=timeout,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0 and "OK: agent loaded" in out


def detach(pid: int | None = None, *, jar: str | Path | None = None,
           classes: str | Path | None = None) -> bool:
    """Погасить агент (он не выгружается, но перестаёт работать)."""
    jar = Path(jar) if jar else _latest_agent_jar()
    return attach(pid, jar=jar, classes=classes, options="off")


def _latest_agent_jar() -> Path:
    jars = sorted(DEFAULT_INJECT_DIR.glob("agent*.jar"),
                  key=lambda p: int("".join(c for c in p.stem if c.isdigit()) or 0))
    if not jars:
        raise FileNotFoundError("в mc-inject нет ни одного agent*.jar")
    return jars[-1]


def read_state(path: str | Path | None = None) -> dict:
    """Прочитать состояние, которое агент пишет в JSON (если пишет)."""
    p = Path(path) if path else DEFAULT_STATE
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def wait_state(timeout: float = 5.0, path: str | Path | None = None) -> dict:
    """Ждём, пока появится файл состояния (агент мог ещё не успеть)."""
    started = time.time()
    while time.time() - started < timeout:
        st = read_state(path)
        if st:
            return st
        time.sleep(0.1)
    return {}
