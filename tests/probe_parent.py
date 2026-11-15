import ctypes

from minecraft_tweaks import _x11 as x

c = x.default_client()
lib = x.x11
lib.XDefaultVisual.restype = ctypes.c_void_p
lib.XDefaultVisual.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.XDefaultDepth.restype = ctypes.c_int
lib.XDefaultDepth.argtypes = [ctypes.c_void_p, ctypes.c_int]

d_def = lib.XDefaultDepth(c.display, c.screen)
v_def = lib.XDefaultVisual(c.display, c.screen)
print("default depth", d_def, "default visual", v_def)
vis = x.ARGBVisual(c)
print("argb visual", vis.visual, "depth", vis.depth)


def show(label, depth, visual, mask=0, attrs=None):
    raw = lib.XCreateWindow(c.display, c.root, 0, 0, 64, 64, 0, depth,
                            x.InputOutput, visual, ctypes.c_ulong(mask),
                            ctypes.cast(ctypes.byref(attrs), ctypes.c_void_p) if attrs else None)
    lib.XSync(c.display, 0)
    print(label, "->", raw)


show("copy-from-parent", 0, None)
show("default visual", d_def, v_def)
show("argb 32", 32, vis.visual)
