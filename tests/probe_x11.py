import ctypes
from minecraft_tweaks import _x11 as x

client = x.default_client()
vis = x.ARGBVisual(client)
print("visual depth", vis.depth, "id", vis.visual)

lib = x.x11
lib.XSetErrorHandler(None)


def try_create(label, depth, visual, colormap, mask):
    attrs = (ctypes.c_ulong * 16)()
    ctypes.memset(attrs, 0, ctypes.sizeof(attrs))
    attrs[12] = 1
    attrs[13] = colormap
    w = lib.XCreateWindow(client.display, client.root, 0, 0, 200, 100, 0,
                          depth, x.InputOutput, visual, ctypes.c_ulong(mask), ctypes.byref(attrs))
    print(label, "-> window", w)
    return w


cm = ctypes.c_ulong(lib.XCreateColormap(client.display, client.root, vis.visual, x.AllocNone)).value
print("colormap", cm)

try_create("A depth32+cm+override", 32, vis.visual, cm, x.CWColormap | x.CWOverrideRedirect)
try_create("B depth32+cm", 32, vis.visual, cm, x.CWColormap)
try_create("C default depth", 0, None, 0, 0)
