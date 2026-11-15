"""Статический разбор пакета: ищем ошибки, а не стиль.

Проверяет: неиспользуемые импорты, голые except, проглатывание ошибок,
изменяемые значения по умолчанию, тень встроенных имён, print в библиотеке,
маркеры TODO/FIXME в комментариях, длинные строки, табы, перевод строки в конце.
"""
from __future__ import annotations

import ast
import builtins
import pathlib
import sys

PKG = pathlib.Path("minecraft_tweaks")
BUILTINS = set(dir(builtins))
CLI = {"watchdog.py", "__main__.py"}
findings: list[str] = []


def report(path: pathlib.Path, node: ast.AST | int, msg: str) -> None:
    line = node if isinstance(node, int) else getattr(node, "lineno", 0)
    findings.append(f"{path.name}:{line}: {msg}")


def check_imports(path: pathlib.Path, tree: ast.Module) -> None:
    imported: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported[alias.asname or alias.name.split(".")[0]] = node
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in {"*", "annotations"}:
                    continue
                imported[alias.asname or alias.name] = node

    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            base: ast.AST = node
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                used.add(base.id)

    source = path.read_text(encoding="utf-8")
    for name, node in imported.items():
        if name not in used and f'"{name}"' not in source and f"'{name}'" not in source:
            report(path, node, f"неиспользуемый импорт: {name}")


def check_excepts(path: pathlib.Path, tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            report(path, node, "голый except:")
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            if all(isinstance(n, ast.Pass) for n in node.body):
                report(path, node, "except Exception: pass без следа в логе")


def check_defaults(path: pathlib.Path, tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for default in list(node.args.defaults) + [d for d in node.args.kw_defaults if d]:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                report(path, default, f"изменяемое значение по умолчанию в {node.name}()")


def check_shadow(path: pathlib.Path, tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args + node.args.kwonlyargs:
                if arg.arg in BUILTINS and arg.arg not in {"id", "type", "format", "input"}:
                    report(path, arg, f"аргумент {arg.arg} перекрывает встроенное имя")


def check_prints(path: pathlib.Path, tree: ast.Module) -> None:
    if path.name in CLI:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            report(path, node, "print() в библиотечном коде")


def check_text(path: pathlib.Path) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        report(path, 0, "нет перевода строки в конце файла")
    for i, line in enumerate(text.splitlines(), 1):
        if len(line) > 120:
            report(path, i, f"строка {len(line)} символов (>120)")
        if "\t" in line:
            report(path, i, "символ табуляции")
        stripped = line.strip()
        if stripped.startswith("#"):
            for marker in ("TODO", "FIXME", "XXX", "HACK"):
                if marker in stripped.upper():
                    report(path, i, f"маркер {marker} в комментарии")


def main() -> int:
    files = sorted(PKG.glob("*.py"))
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        check_imports(path, tree)
        check_excepts(path, tree)
        check_defaults(path, tree)
        check_shadow(path, tree)
        check_prints(path, tree)
        check_text(path)
    for item in findings:
        print(item)
    print(f"\nmodules={len(files)} findings={len(findings)}")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
