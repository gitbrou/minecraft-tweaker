"""Загрузка пакета на PyPI/TestPyPI без twine (только стандартная библиотека).

Токен берётся из переменной окружения TWINE_PASSWORD или из ~/.pypirc:

    [pypi]
    username = __token__
    password = pypi-...

Использование:
    python upload.py --dry-run            # показать, что будет загружено
    python upload.py                      # на PyPI
    python upload.py --index testpypi     # на TestPyPI
"""
from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import sys
import urllib.request
import hashlib
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist_pypi"

INDEXES = {
    "pypi": "https://upload.pypi.org/legacy/",
    "testpypi": "https://test.pypi.org/legacy/",
}

NAME = "minecraft-tweaks"
VERSION = "0.3.0"


def read_pypirc(index: str) -> tuple[str, str]:
    env_user = os.environ.get("TWINE_USERNAME")
    env_pass = os.environ.get("TWINE_PASSWORD")
    if env_pass:
        return (env_user or "__token__", env_pass)

    rc = Path(os.environ.get("USERPROFILE", Path.home())) / ".pypirc"
    if rc.exists():
        section = None
        user = passwd = None
        for raw in rc.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip()
                continue
            if section != index or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip().lower()
            if key == "username":
                user = value.strip()
            elif key == "password":
                passwd = value.strip()
        if passwd:
            return (user or "__token__", passwd)
    return ("", "")


def files() -> list[Path]:
    out = sorted(DIST.glob(f"*{VERSION}*"))
    return [p for p in out if p.suffix in {".whl", ".gz"}]


def filetype(p: Path) -> tuple[str, str]:
    if p.suffix == ".whl":
        return ("bdist_wheel", "py3")
    return ("sdist", "source")


def build_body(p: Path) -> tuple[bytes, str]:
    boundary = "----mt" + uuid.uuid4().hex
    ft, pyver = filetype(p)
    readme = (ROOT / "README.md")
    description = readme.read_text(encoding="utf-8") if readme.exists() else ""
    # legacy upload принимает метаданные отдельными полями формы, JSON-поле сервер не читает
    pairs: list[tuple[str, str]] = [
        (":action", "file_upload"),
        ("protocol_version", "1"),
        ("metadata_version", "2.1"),
        ("name", NAME),
        ("version", VERSION),
        ("filetype", ft),
        ("pyversion", pyver),
        ("summary", "simple minecraft injector"),
        ("description", description),
        ("description_content_type", "text/markdown"),
        ("author", "gitbrou"),
        ("license", "MIT"),
        ("requires_python", ">=3.10"),
        ("keywords", "minecraft,overlay,esp,gui,win32"),
        ("home_page", "https://pypi.org/project/minecraft-tweaks/"),
    ]
    data = p.read_bytes()
    pairs.append(("md5_digest", hashlib.md5(data).hexdigest()))
    pairs.append(("sha256_digest", hashlib.sha256(data).hexdigest()))
    pairs.append(("size", str(len(data))))
    for cls in (
        "Programming Language :: Python :: 3",
        "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: MIT License",
    ):
        pairs.append(("classifiers", cls))
    chunks: list[bytes] = []
    for k, v in pairs:
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
        )
    chunks.append(
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"content\"; "
            f"filename=\"{p.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
        ).encode()
    )
    chunks.append(p.read_bytes())
    chunks.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="upload.py")
    ap.add_argument("--index", choices=sorted(INDEXES), default="pypi")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    targets = files()
    if not targets:
        print(f"нет файлов в {DIST}")
        return 2

    user, passwd = read_pypirc(args.index)
    print(f"index: {INDEXES[args.index]}")
    print(f"user:  {user or '<не задан>'}")
    print(f"token: {'задан, длина ' + str(len(passwd)) if passwd else 'НЕ НАЙДЕН'}")
    for p in targets:
        print(f"file:  {p.name} ({p.stat().st_size:,} bytes, {filetype(p)[0]})")

    if args.dry_run:
        body, ctype = build_body(targets[0])
        print(f"dry-run: сформировано тело {len(body):,} bytes, {ctype.split('boundary=')[0]}...")
        return 0

    if not passwd:
        print("\nТокен не найден. Положив его в %USERPROFILE%\\.pypirc:\n"
              "  [pypi]\n  username = __token__\n  password = pypi-...\n"
              "или задав переменную TWINE_PASSWORD, повтори запуск.")
        return 3

    auth = base64.b64encode(f"{user}:{passwd}".encode()).decode()
    rc = 0
    for p in targets:
        body, ctype = build_body(p)
        req = urllib.request.Request(
            INDEXES[args.index], data=body, method="POST",
            headers={"Authorization": f"Basic {auth}", "Content-Type": ctype},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                print(f"{p.name}: HTTP {resp.status} OK")
        except Exception as exc:  # noqa: BLE001 - показываем текст ответа PyPI
            detail = getattr(exc, "read", lambda: b"")()
            print(f"{p.name}: ОШИБКА {exc} {detail[:400]!r}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
