# Instructions (English)

## Install

```
pip install minecraft-tweaks
```

Python 3.10 or newer, no dependencies.

## Run

```
python -m minecraft_tweaks
```

The process waits for the Minecraft window, shows the ESP overlay and the
ClickGUI, and waits again when the game closes. `Right Shift` toggles the GUI,
`Shift + Esc` quits, `Alt + S, R, R` arms the client.

Flags: `--fps`, `--no-esp`, `--no-gui`, `--no-arm`, `--world`, `--once`, `-q`.

## Build a single file

```
python build-all.py
```

Produces `dist\<name>.pyz` and `dist\<name>.bat` with a randomized process
name. Options: `--name`, `--exe`, `--keep-old`.

## Autostart

```
python -m minecraft_tweaks --autostart on|off|status
```

## Extensions

```
import minecraft_tweaks as mt

@mt.esp_block("diamond_ore", color=0xFF4ADEDE, max_distance=48)
def ores(): ...
```

Decorators: `esp_block`, `esp_entity`, `esp_draw`, `on_frame`, `module`.
Scripts in `scripts/` load through `mt.load_scripts("scripts")`.

## Java agent

```
mt.agent.attach()
mt.agent.read_state()
```

Needs the `mc-inject` folder next to the package.

## Limits

Windows and Linux with X11. Wayland is not supported. Transparency on Linux
needs a running compositor.

# Инструкция

## Установка

```
pip install minecraft-tweaks
```

Python 3.10 или новее. Зависимостей нет, всё через ctypes и Win32 или libX11.

## Быстрый старт

```
python -m minecraft_tweaks
```

Утилита ждёт окно Minecraft, поднимает оверлей с ESP и ClickGUI, а когда игра
закрывается, снова ждёт. Клавиши: `Right Shift` открывает и закрывает GUI,
`Shift + Esc` завершает процесс, `Alt + S, R, R` взводит клиент.

Флаги: `--fps 144`, `--no-esp`, `--no-gui`, `--no-arm`, `--world`, `--once`,
`-q`. Полный набор: `python -m minecraft_tweaks --help`.

## Сборка в один файл

```
python build-all.py
```

На выходе `dist\<имя>.pyz` и `dist\<имя>.bat`. Скрипт сам выбирает случайное
системное имя, копирует `pythonw.exe` под этим именем и генерирует bat.
Переопределить: `--name`, `--exe`, `--keep-old`.

## Автозапуск

```
python -m minecraft_tweaks --autostart on
python -m minecraft_tweaks --autostart status
python -m minecraft_tweaks --autostart off
```

Windows: ключ `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
Linux: `~/.config/autostart/minecraft-tweaks.desktop`.

## Свои расширения

```
import minecraft_tweaks as mt

@mt.esp_block("diamond_ore", color=0xFF4ADEDE, max_distance=48)
def ores(): ...

@mt.module("AutoTool", category="Player")
class AutoTool:
    def on_tick(self, app): ...
```

Свои скрипты кладутся в `scripts/` и подхватываются вызовом
`mt.load_scripts("scripts")`. Доступны `@mt.esp_entity`, `@mt.esp_draw`,
`@mt.on_frame`, а также `mt.registry` для регистрации источников сущностей.

## Связка с Java-клиентом

Пакет умеет звать агент из соседней папки `mc-inject`:

```
mt.agent.attach()
mt.agent.read_state()
```

Это нужно для модулей, которым мало внешнего оверлея: пакеты, инвентарь,
логика на тиках игры.

## Ограничения

Windows и Linux через X11. Wayland не поддерживается. Для прозрачности на
Linux нужен композитор. После установки из pip исходники Java не нужны,
кроме случая с `mt.agent`.

---
