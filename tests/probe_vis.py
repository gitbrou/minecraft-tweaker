import ctypes

from minecraft_tweaks import _x11 as x

c = x.default_client()
lib = x.x11
vis = x.ARGBVisual(c)
print("visual", vis.visual, "info size", ctypes.sizeof(x.XVisualInfo))
info = vis.info
print("visualid", getattr(info, "visualid", "?"), "depth field", getattr(info, "depth", "?"),
      "class field", getattr(info, "c_class", "?"))

cm = lib.XCreateColormap(c.display, c.root, vis.visual, x.AllocNone)
lib.XSync(c.display, 0)
print("colormap ok", cm)
cm2 = lib.XCreateColormap(c.display, c.root, vis.visual, x.AllocNone)
lib.XSync(c.display, 0)
print("colormap ok2", cm2)
