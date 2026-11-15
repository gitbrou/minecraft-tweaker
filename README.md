# minecraft-tweaks

simple minecraft injector

Overlay library for Minecraft on Windows and Linux. Pure Python, no
dependencies: a transparent window sits on top of the game, draws boxes,
labels, a ClickGUI and whatever else you add, and the game itself is left
untouched.

## Install

```bash
pip install minecraft-tweaks
```

Python 3.10 or newer. Windows needs nothing extra. Linux needs X11 and a
running compositor (GNOME, KDE, Xfce with compositing, picom).

## Quick start

```python
import minecraft_tweaks as mt

def render(canvas, overlay):
    canvas.text("hello", 20, 20, 0xFFFFFFFF)

mt.Overlay(fps=144).loop(render)
```

The window follows the game window, stays above it, ignores the mouse and
never takes focus. It hides when the game loses focus, so alt-tabbing leaves
nothing on screen.

## Or run the whole client

```bash
python -m minecraft_tweaks
```

It waits for Minecraft, shows the ESP and the ClickGUI, and returns to
waiting when the game closes. Flags: `--fps`, `--no-esp`, `--no-gui`,
`--no-arm`, `--world`, `--once`, `-q`.

Arm the macros with Alt+S, R, R. Right Shift opens the ClickGUI.

## What is inside

| Module | Purpose |
| --- | --- |
| `overlay` | transparent click-through window, follows the game |
| `draw` | canvas: rectangles, lines, gradients, rounded shapes, pixel text |
| `paint` | antialiased lines, bezier, glow, blur, shadow, glass, sprites, text effects |
| `esp` | projection, boxes, corners, icons, health bars, distance, tracers |
| `gui` | ClickGUI with categories, toggles and search |
| `keys` | key state, combo arming, hotkeys |
| `process` | finds the game window on both platforms |
| `extensions` | registry of your own entities, blocks, modules and draw hooks |
| `watchdog` | waits for the game, runs the client, reconnects |
| `anim` | easing, tweens, timelines |
| `png` | load and save PNG without Pillow |

## ESP

```python
import minecraft_tweaks as mt

cam = mt.Camera(x=0, y=70, z=0, yaw=45, pitch=10, fov=70, aspect=16 / 9)
ent = mt.Entity(x=6, y=70, z=8, height=1.8, kind="player", health=0.8, label="Alex")
mt.ESPRenderer().draw(canvas, cam, [ent], partial_tick=0.5)
```

Positions are interpolated with the partial tick, so boxes move smoothly
instead of stepping 20 times per second. `mt.esp_block("diamond_ore")` draws
blocks you collect yourself, `mt.esp_entity` adds a source of entities.

## Your own stuff

```python
import minecraft_tweaks as mt

@mt.esp_block("ancient_debris", color=0xFFFF8844, max_distance=64, label="debris")
def debris():
    return [(120, 14, -330)]

@mt.esp_draw
def watermark(canvas, cam, app):
    canvas.text("my pack", 12, 12, 0xFF7C5CFF)

@mt.module("AutoSprint", category="Movement", enabled=True)
class AutoSprint:
    def on_tick(self, app):
        pass
```

`mt.load_scripts("scripts")` imports every `*.py` in that folder, so other
people can extend the client without touching the library.

## Platforms

Windows uses a layered window with `UpdateLayeredWindow`. Linux uses an X11
ARGB window with `XPutImage` and reads keys from the X11 keymap. Wayland is
not supported, use the X11 session.

## Limitations

The library draws from outside the game process. It cannot change game
mechanics: no packet tricks, no inventory moves. For that there is an
optional Java agent, see below.

---

# minecraft-tweaks (по-русски)

simple minecraft injector

Библиотека оверлеев для Minecraft на Windows и Linux. Чистый Python без
зависимостей: прозрачное окно поверх игры рисует рамки, подписи, ClickGUI и
всё, что вы добавите. Сама игра не трогается.

## Установка

```bash
pip install minecraft-tweaks
```

Нужен Python 3.10 или новее. На Windows больше ничего не требуется. На
Linux нужны X11 и работающий композитор (GNOME, KDE, Xfce с композитингом,
picom).

## Быстрый старт

```python
import minecraft_tweaks as mt

def render(canvas, overlay):
    canvas.text("привет", 20, 20, 0xFFFFFFFF)

mt.Overlay(fps=144).loop(render)
```

Окно следует за окном игры, держится сверху, не ловит мышь и не забирает
фокус. Когда игра теряет фокус, окно прячется.

## Или сразу весь клиент

```bash
python -m minecraft_tweaks
```

Ждёт Minecraft, показывает ESP и ClickGUI, после закрытия игры снова ждёт.
Флаги: `--fps`, `--no-esp`, `--no-gui`, `--no-arm`, `--world`, `--once`, `-q`.

Взвод макросов: Alt+S, R, R. Right Shift открывает ClickGUI.

## Что внутри

| Модуль | Назначение |
| --- | --- |
| `overlay` | прозрачное окно поверх игры, клики проходят насквозь |
| `draw` | холст: прямоугольники, линии, градиенты, скругления, пиксельный текст |
| `paint` | сглаженные линии, безье, свечение, размытие, тени, стекло, спрайты, эффекты текста |
| `esp` | проекция, рамки, уголки, иконки, полосы здоровья, дистанция, трассеры |
| `gui` | ClickGUI с категориями, тумблерами и поиском |
| `keys` | состояние клавиш, комбо, хоткеи |
| `process` | поиск окна игры на обеих платформах |
| `extensions` | реестр своих сущностей, блоков, модулей и хуков отрисовки |
| `watchdog` | ждёт игру, запускает клиент, переподключается |
| `anim` | кривые, твины, таймлайны |
| `png` | чтение и запись PNG без Pillow |

## ESP

```python
import minecraft_tweaks as mt

cam = mt.Camera(x=0, y=70, z=0, yaw=45, pitch=10, fov=70, aspect=16 / 9)
ent = mt.Entity(x=6, y=70, z=8, height=1.8, kind="player", health=0.8, label="Alex")
mt.ESPRenderer().draw(canvas, cam, [ent], partial_tick=0.5)
```

Позиции интерполируются по partial tick, поэтому рамки двигаются плавно, а
не шагами по 20 раз в секунду. `mt.esp_block("diamond_ore")` рисует блоки,
которые вы отдаёте сами, `mt.esp_entity` добавляет источник сущностей.

## Свои методы

```python
import minecraft_tweaks as mt

@mt.esp_block("ancient_debris", color=0xFFFF8844, max_distance=64, label="debris")
def debris():
    return [(120, 14, -330)]

@mt.esp_draw
def watermark(canvas, cam, app):
    canvas.text("my pack", 12, 12, 0xFF7C5CFF)

@mt.module("AutoSprint", category="Movement", enabled=True)
class AutoSprint:
    def on_tick(self, app):
        pass
```

`mt.load_scripts("scripts")` подключает все `*.py` из папки, так что другие
люди расширяют клиент не залезая в библиотеку.

## Платформы

На Windows это layered-окно с `UpdateLayeredWindow`. На Linux окно X11 с
ARGB визуалом и `XPutImage`, клавиши читаются из маски X11. Wayland не
поддерживается, нужна X11-сессия.

## Ограничения

Библиотека рисует снаружи игрового процесса. Она не меняет механику игры:
никаких пакетов и перекладывания предметов. Для этого есть отдельный
Java-агент, он подключается по желанию.

## License

MIT
