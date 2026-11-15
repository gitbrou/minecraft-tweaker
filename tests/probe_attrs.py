import ctypes

from minecraft_tweaks import _x11 as x

c = x.default_client()
vis = x.ARGBVisual(c)
lib = x.x11
print("sizeof attrs", ctypes.sizeof(x.XSetWindowAttributes))
print("visual ptr", vis.visual, "depth", vis.depth)

cm = ctypes.c_ulong(lib.XCreateColormap(c.display, c.root, vis.visual, x.AllocNone)).value
print("colormap", cm)


def build(colormap, override):
    a = x.XSetWindowAttributes()
    a.override_redirect = override
    a.colormap = colormap
    return a


def show(mask, attrs, label):
    raw = lib.XCreateWindow(c.display, c.root, 0, 0, 64, 64, 0, vis.depth,
                            x.InputOutput, vis.visual, ctypes.c_ulong(mask),
                            ctypes.cast(ctypes.byref(attrs), ctypes.c_void_p) if attrs else None)
    lib.XSync(c.display, 0)
    print(label, "->", raw)


show(0, None, "mask0")
show(x.CWOverrideRedirect, build(0, 1), "override only")
show(x.CWColormap, build(cm, 0), "colormap only")
show(x.CWColormap | x.CWOverrideRedirect, build(cm, 1), "both")
