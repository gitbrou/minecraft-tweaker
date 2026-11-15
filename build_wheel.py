"""Сборка pure-python wheel без зависимостей (без пакета wheel/build).

Создаёт dist_pypi/minecraft_tweaks-<ver>-py3-none-any.whl по спецификации
PEP 427: пакет + .dist-info с METADATA/WHEEL/RECORD.
"""
from __future__ import annotations

import base64
import hashlib
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "minecraft_tweaks"
DIST = ROOT / "dist_pypi"


def meta() -> dict:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    def grab(key: str, default: str = "") -> str:
        m = re.search(rf'^{key}\s*=\s*"([^"]*)"', text, re.M)
        return m.group(1) if m else default
    return {
        "version": grab("version", "0.0.0"),
        "description": grab("description"),
        "requires_python": grab("requires-python", ">=3.10"),
    }


def readme() -> str:
    p = ROOT / "README.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def metadata_file(m: dict) -> str:
    lines = [
        "Metadata-Version: 2.1",
        f"Name: {NAME.replace('_', '-')}",
        f"Version: {m['version']}",
        f"Summary: {m['description']}",
        "Author: newlevel",
        "License: MIT",
        f"Requires-Python: {m['requires_python']}",
        "Description-Content-Type: text/markdown",
        "",
        readme(),
    ]
    return "\n".join(lines)


def wheel_file() -> str:
    return "\n".join([
        "Wheel-Version: 1.0",
        "Generator: mt-wheel 1.0",
        "Root-Is-Purelib: true",
        "Tag: py3-none-any",
        "",
    ])


def add(zf: zipfile.ZipFile, arc: str, data: bytes, record: list[tuple[str, str, int]]) -> None:
    zf.writestr(arc, data)
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
    record.append((arc, f"sha256={digest}", len(data)))


def main() -> int:
    m = meta()
    DIST.mkdir(exist_ok=True)
    wheel_name = f"{NAME}-{m['version']}-py3-none-any.whl"
    out = DIST / wheel_name
    dist_info = f"{NAME}-{m['version']}.dist-info"

    record: list[tuple[str, str, int]] = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted((ROOT / NAME).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            arc = path.relative_to(ROOT).as_posix()
            add(zf, arc, path.read_bytes(), record)
        add(zf, f"{dist_info}/METADATA", metadata_file(m).encode("utf-8"), record)
        add(zf, f"{dist_info}/WHEEL", wheel_file().encode("utf-8"), record)
        add(zf, f"{dist_info}/top_level.txt", (NAME + "\n").encode("utf-8"), record)
        rec_lines = [f"{p},{h},{s}" for p, h, s in record]
        rec_lines.append(f"{dist_info}/RECORD,,")
        zf.writestr(f"{dist_info}/RECORD", "\n".join(rec_lines) + "\n")

    size = out.stat().st_size
    digest = hashlib.sha256(out.read_bytes()).hexdigest()[:16].upper()
    print(f"wheel: {out.name}  {size:,} bytes  sha256:{digest}")
    print(f"files: {len(record) + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
