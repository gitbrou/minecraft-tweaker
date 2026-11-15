import traceback

from minecraft_tweaks import _x11 as x

client = x.default_client()
print("client", client.display, "root", client.root, "screen", client.screen)
vis = x.ARGBVisual(client)
print("vis", vis.depth, vis.visual)
w, h = client.screen_size()
win = x.create_overlay_window(client, vis, 0, 0, w, h)
print("win1", win)
_x11 = x
print("lib is same:", x.x11.XCreateWindow.argtypes[10])
w2 = x.create_overlay_window(client, vis, 0, 0, 320, 200)
print("win2", w2)

from minecraft_tweaks._overlay_x11 import Overlay

try:
    ov = Overlay(fps=30)
    ov.open()
    print("overlay opened", ov.hwnd)
    ov.close()
except Exception:
    traceback.print_exc()
