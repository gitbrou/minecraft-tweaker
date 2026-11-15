import traceback

from minecraft_tweaks import process, _x11 as x

print("step1: default_client")
c = x.default_client()
print("screen", c.screen_size())
print("step2: keymap/pointer")
print(len(c.keymap()), c.pointer())
print("step3: process.find")
w = process.find()
print("window", w)

print("step4: Overlay.open")
from minecraft_tweaks._overlay_x11 import Overlay

try:
    ov = Overlay(fps=30).open()
    print("opened", ov.hwnd)
    ov.present()
    print("present ok", ov.stats.frames, ov.stats.present_errors)
    ov.close()
except Exception:
    traceback.print_exc()
