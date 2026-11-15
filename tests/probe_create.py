import traceback

from minecraft_tweaks import _x11 as x

client = x.default_client()
vis = x.ARGBVisual(client)
print("visual depth", vis.depth)
try:
    w, h = client.screen_size(); print("screen", w, h); win = x.create_overlay_window(client, vis, 0, 0, w, h); gc = x.x11.XCreateGC(client.display, win, 0, None); print("gc", gc)
    print("created", win)
except Exception:
    traceback.print_exc()
