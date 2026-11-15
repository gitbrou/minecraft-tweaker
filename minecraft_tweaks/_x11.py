"""X11 backend for Linux: overlay window and input state via libX11.

Everything goes through ctypes, so no extra packages are needed. The overlay
uses an ARGB visual and XPutImage, which needs a running compositor for
transparency (GNOME, KDE, Xfce with compositing, picom, and so on).
"""

from __future__ import annotations

import ctypes
import ctypes.util

Display = ctypes.c_void_p
Window = ctypes.c_ulong
Visual = ctypes.c_void_p
Colormap = ctypes.c_ulong
KeySym = ctypes.c_ulong


def _load(name: str, *fallbacks: str) -> ctypes.CDLL:
    path = ctypes.util.find_library(name)
    for candidate in (path, *fallbacks):
        if not candidate:
            continue
        try:
            return ctypes.CDLL(candidate)
        except OSError:
            continue
    raise OSError(f"cannot load {name}")


class _MissingLib:
    """Stand-in for libX11 on systems that do not have it (Windows, macOS).

    Attribute access keeps working so the module-level prototypes can be
    declared, and any real call raises a clear error instead of failing at
    import time.
    """

    def __getattr__(self, name: str) -> "_MissingLib":
        return _MissingLib()

    def __setattr__(self, name: str, value: object) -> None:
        pass

    def __call__(self, *args: object, **kwargs: object) -> object:
        raise OSError("X11 is not available on this system")


try:
    x11 = _load("X11", "libX11.so.6", "libX11.so")
    X11_AVAILABLE = True
except OSError:
    x11 = _MissingLib()
    X11_AVAILABLE = False

x11.XOpenDisplay.restype = Display
x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
x11.XCloseDisplay.argtypes = [Display]
x11.XFlush.argtypes = [Display]
x11.XDefaultRootWindow.restype = Window
x11.XDefaultRootWindow.argtypes = [Display]
x11.XDefaultScreen.argtypes = [Display]
x11.XDisplayWidth.argtypes = [Display, ctypes.c_int]
x11.XDisplayHeight.argtypes = [Display, ctypes.c_int]
x11.XKeysymToKeycode.restype = ctypes.c_ubyte
x11.XKeysymToKeycode.argtypes = [Display, KeySym]
x11.XStringToKeysym.restype = KeySym
x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
x11.XQueryKeymap.argtypes = [Display, ctypes.POINTER(ctypes.c_char)]
x11.XQueryPointer.restype = ctypes.c_int
x11.XQueryPointer.argtypes = [
    Display, Window,
    ctypes.POINTER(Window), ctypes.POINTER(Window),
    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_uint),
]
x11.XCreateWindow.restype = Window
x11.XCreateWindow.argtypes = [
    Display, Window, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
    ctypes.c_uint, ctypes.c_int, ctypes.c_uint, Visual,
    ctypes.c_ulong, ctypes.c_void_p,
]
x11.XDestroyWindow.argtypes = [Display, Window]
x11.XMapRaised.argtypes = [Display, Window]
x11.XUnmapWindow.argtypes = [Display, Window]
x11.XMoveResizeWindow.argtypes = [Display, Window, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_uint, ctypes.c_uint]
x11.XCreateColormap.restype = Colormap
x11.XCreateColormap.argtypes = [Display, Window, Visual, ctypes.c_int]
x11.XCreateGC.restype = ctypes.c_void_p
x11.XCreateGC.argtypes = [Display, Window, ctypes.c_ulong, ctypes.c_void_p]
x11.XFreeGC.argtypes = [Display, ctypes.c_void_p]
x11.XCreateImage.restype = ctypes.c_void_p
x11.XCreateImage.argtypes = [
    Display, Visual, ctypes.c_uint, ctypes.c_int, ctypes.c_int,
    ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_int, ctypes.c_int,
]
x11.XPutImage.argtypes = [
    Display, Window, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_uint, ctypes.c_uint,
]
x11.XGetWindowAttributes.restype = ctypes.c_int
x11.XGetWindowAttributes.argtypes = [Display, Window, ctypes.c_void_p]
x11.XTranslateCoordinates.restype = ctypes.c_int
x11.XTranslateCoordinates.argtypes = [
    Display, Window, Window,
    ctypes.c_int, ctypes.c_int,
    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(Window),
]
x11.XInternAtom.restype = ctypes.c_ulong
x11.XInternAtom.argtypes = [Display, ctypes.c_char_p, ctypes.c_int]
x11.XGetWindowProperty.restype = ctypes.c_int
x11.XGetWindowProperty.argtypes = [
    Display, Window, ctypes.c_ulong, ctypes.c_long, ctypes.c_long,
    ctypes.c_int, ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
    ctypes.POINTER(ctypes.c_void_p),
]
x11.XFree.argtypes = [ctypes.c_void_p]
x11.XQueryTree.restype = ctypes.c_int
x11.XQueryTree.argtypes = [
    Display, Window,
    ctypes.POINTER(Window), ctypes.POINTER(Window),
    ctypes.POINTER(ctypes.POINTER(Window)), ctypes.POINTER(ctypes.c_uint),
]

CWColormap = 1 << 13
CWOverrideRedirect = 1 << 9
CWBorderPixel = 1 << 3
InputOutput = 1
ZPixmap = 2
AllocNone = 0
AnyPropertyType = 0
IsViewable = 2

# X keysyms we need. Letters and digits map by code point.
XK_SHIFT_L = 0xFFE1
XK_SHIFT_R = 0xFFE2
XK_CONTROL_L = 0xFFE3
XK_CONTROL_R = 0xFFE4
XK_ALT_L = 0xFFE9
XK_ALT_R = 0xFFEA
XK_ESCAPE = 0xFF1B
XK_RETURN = 0xFF0D
XK_SPACE = 0x20
XK_TAB = 0xFF09

VK_TO_KEYSYM = {
    0x08: 0xFF08,          # backspace
    0x09: XK_TAB,
    0x0D: XK_RETURN,
    0x10: XK_SHIFT_L,
    0x11: XK_CONTROL_L,
    0x12: XK_ALT_L,
    0x1B: XK_ESCAPE,
    0x20: XK_SPACE,
    0xA0: XK_SHIFT_L,
    0xA1: XK_SHIFT_R,
    0xA2: XK_CONTROL_L,
    0xA3: XK_CONTROL_R,
    0xA4: XK_ALT_L,
    0xA5: XK_ALT_R,
}
for _code in range(0x30, 0x3A):            # 0..9
    VK_TO_KEYSYM[_code] = _code
for _code in range(0x41, 0x5B):            # A..Z
    VK_TO_KEYSYM[_code] = _code + 0x20

BUTTON_MASKS = {0x01: 1 << 8, 0x02: 1 << 10, 0x04: 1 << 9}


def keysym_for_vk(code: int) -> int | None:
    """Windows virtual-key code to X keysym."""
    return VK_TO_KEYSYM.get(code)


def is_pressed(keymap: bytes, keycode: int) -> bool:
    """Check one keycode in the 32-byte mask returned by XQueryKeymap."""
    index = keycode >> 3
    if index < 0 or index >= len(keymap):
        return False
    return bool(keymap[index] & (1 << (keycode & 7)))


class XClient:
    """A single X display connection shared by the whole library."""

    def __init__(self, name: str | None = None) -> None:
        self.display = x11.XOpenDisplay(name.encode() if name else None)
        if not self.display:
            raise RuntimeError("cannot open X display (is DISPLAY set?)")
        self.screen = x11.XDefaultScreen(self.display)
        self.root = Window(x11.XDefaultRootWindow(self.display))

    def screen_size(self) -> tuple[int, int]:
        return (int(x11.XDisplayWidth(self.display, self.screen)),
                int(x11.XDisplayHeight(self.display, self.screen)))

    def keycode(self, keysym: int) -> int:
        return int(x11.XKeysymToKeycode(self.display, KeySym(keysym)))

    def keymap(self) -> bytes:
        buf = (ctypes.c_char * 32)()
        x11.XQueryKeymap(self.display, buf)
        return bytes(buf)

    def key_down(self, vk_code: int) -> bool:
        if vk_code in BUTTON_MASKS:
            return bool(self.pointer()[2] & BUTTON_MASKS[vk_code])
        keysym = keysym_for_vk(vk_code)
        if keysym is None:
            return False
        code = self.keycode(keysym)
        if code == 0:
            return False
        return is_pressed(self.keymap(), code)

    def pointer(self) -> tuple[int, int, int]:
        root_ret = Window()
        child = Window()
        rx = ctypes.c_int()
        ry = ctypes.c_int()
        wx = ctypes.c_int()
        wy = ctypes.c_int()
        mask = ctypes.c_uint()
        ok = x11.XQueryPointer(self.display, self.root,
                               ctypes.byref(root_ret), ctypes.byref(child),
                               ctypes.byref(rx), ctypes.byref(ry),
                               ctypes.byref(wx), ctypes.byref(wy),
                               ctypes.byref(mask))
        if not ok:
            return 0, 0, 0
        return int(rx.value), int(ry.value), int(mask.value)

    def close(self) -> None:
        if self.display:
            x11.XCloseDisplay(self.display)
            self.display = None


class XVisualInfo(ctypes.Structure):
    _fields_ = [("visual", Visual), ("visualid", ctypes.c_ulong),
                ("screen", ctypes.c_int), ("depth", ctypes.c_int),
                ("c_class", ctypes.c_int), ("red_mask", ctypes.c_ulong),
                ("green_mask", ctypes.c_ulong), ("blue_mask", ctypes.c_ulong),
                ("colormap_size", ctypes.c_int), ("bits_per_rgb", ctypes.c_int)]


x11.XMatchVisualInfo.restype = ctypes.c_int
x11.XMatchVisualInfo.argtypes = [Display, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_int, ctypes.POINTER(XVisualInfo)]


class ARGBVisual:
    """32-bit TrueColor visual, the one compositors blend with."""

    def __init__(self, client: XClient) -> None:
        info = XVisualInfo()
        ok = x11.XMatchVisualInfo(client.display, client.screen, 32, 4,
                                  ctypes.byref(info))
        if not ok:
            raise RuntimeError("no 32-bit ARGB visual on this display")
        self.info = info
        self.depth = 32
        self.visual = info.visual


class XSetWindowAttributes(ctypes.Structure):
    """Real layout of XSetWindowAttributes.

    Setting fields by raw offsets fails, because several members are 32-bit
    ints with padding; colormap ends up in the wrong slot and XCreateWindow
    answers BadMatch.
    """

    _fields_ = [
        ("background_pixmap", ctypes.c_ulong),
        ("background_pixel", ctypes.c_ulong),
        ("border_pixmap", ctypes.c_ulong),
        ("border_pixel", ctypes.c_ulong),
        ("bit_gravity", ctypes.c_int),
        ("win_gravity", ctypes.c_int),
        ("backing_store", ctypes.c_int),
        ("backing_planes", ctypes.c_ulong),
        ("backing_pixel", ctypes.c_ulong),
        ("save_under", ctypes.c_int),
        ("event_mask", ctypes.c_long),
        ("do_not_propagate_mask", ctypes.c_long),
        ("override_redirect", ctypes.c_int),
        ("colormap", ctypes.c_ulong),
        ("cursor", ctypes.c_ulong),
    ]


def create_overlay_window(client: XClient, visual: ARGBVisual,
                          x: int, y: int, width: int, height: int) -> Window:
    # XCreateColormap already returns a plain int because restype is set.
    # int() on a ctypes wrapper is not reliable on every Python version
    # (3.14 returns bytes), so use .value where a wrapper appears.
    colormap = ctypes.c_ulong(x11.XCreateColormap(client.display, client.root,
                                                  visual.visual, AllocNone)).value
    attrs = XSetWindowAttributes()
    attrs.override_redirect = 1
    # a depth 32 window inheriting the parent border pixmap is a BadMatch,
    # so give it its own border pixel
    attrs.border_pixel = 0
    attrs.colormap = colormap
    raw = x11.XCreateWindow(
        client.display, client.root, x, y, width, height, 0, visual.depth,
        InputOutput, visual.visual, ctypes.c_ulong(CWColormap | CWOverrideRedirect | CWBorderPixel),
        ctypes.cast(ctypes.byref(attrs), ctypes.c_void_p))
    # restype comes back as int on some builds and as a wrapper on others
    win = Window(raw.value if hasattr(raw, "value") else int(raw))
    if not win:
        raise RuntimeError("XCreateWindow failed")
    return win


def put_buffer(client: XClient, visual: ARGBVisual, win: Window, gc,
               buf: bytearray, width: int, height: int) -> bool:
    """Blit a BGRA buffer into the window with XPutImage."""
    stride = width * 4
    data = (ctypes.c_char * len(buf)).from_buffer(buf)
    image = x11.XCreateImage(client.display, visual.visual, visual.depth,
                             ZPixmap, 0, data, width, height, 32, stride)
    if not image:
        return False
    try:
        x11.XPutImage(client.display, win, gc, image, 0, 0, 0, 0, width, height)
    finally:
        x11.XFree(image)
    x11.XFlush(client.display)
    return True


def window_geometry(client: XClient, win: Window) -> tuple[int, int, int, int]:
    class Attrs(ctypes.Structure):
        _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int),
                    ("width", ctypes.c_int), ("height", ctypes.c_int),
                    ("border_width", ctypes.c_int), ("depth", ctypes.c_int),
                    ("visual", Visual), ("root", Window), ("c_class", ctypes.c_int),
                    ("bit_gravity", ctypes.c_int), ("win_gravity", ctypes.c_int),
                    ("backing_store", ctypes.c_int),
                    ("backing_planes", ctypes.c_ulong),
                    ("backing_pixel", ctypes.c_ulong),
                    ("save_under", ctypes.c_int), ("colormap", Colormap),
                    ("map_installed", ctypes.c_int), ("map_state", ctypes.c_int),
                    ("all_event_masks", ctypes.c_long),
                    ("your_event_mask", ctypes.c_long),
                    ("do_not_propagate_mask", ctypes.c_long),
                    ("override_redirect", ctypes.c_int), ("screen", ctypes.c_void_p)]

    attrs = Attrs()
    if not x11.XGetWindowAttributes(client.display, win, ctypes.byref(attrs)):
        return 0, 0, 0, 0
    rx = ctypes.c_int()
    ry = ctypes.c_int()
    child = Window()
    x11.XTranslateCoordinates(client.display, win, client.root, 0, 0,
                              ctypes.byref(rx), ctypes.byref(ry),
                              ctypes.byref(child))
    return int(rx.value), int(ry.value), int(attrs.width), int(attrs.height)


def window_pid(client: XClient, win: Window) -> int | None:
    atom = x11.XInternAtom(client.display, b"_NET_WM_PID", 1)
    actual_type = ctypes.c_ulong()
    actual_format = ctypes.c_int()
    nitems = ctypes.c_ulong()
    bytes_after = ctypes.c_ulong()
    prop = ctypes.c_void_p()
    status = x11.XGetWindowProperty(client.display, win, atom, 0, 1, 0,
                                    AnyPropertyType, ctypes.byref(actual_type),
                                    ctypes.byref(actual_format),
                                    ctypes.byref(nitems),
                                    ctypes.byref(bytes_after),
                                    ctypes.byref(prop))
    if status != 0 or not prop.value:
        return None
    try:
        value = ctypes.cast(prop, ctypes.POINTER(ctypes.c_ulong))[0]
        return int(value)
    finally:
        x11.XFree(prop)


def window_title(client: XClient, win: Window) -> str:
    for name in (b"_NET_WM_NAME", b"WM_NAME"):
        atom = x11.XInternAtom(client.display, name, 1)
        actual_type = ctypes.c_ulong()
        actual_format = ctypes.c_int()
        nitems = ctypes.c_ulong()
        bytes_after = ctypes.c_ulong()
        prop = ctypes.c_void_p()
        status = x11.XGetWindowProperty(client.display, win, atom, 0, 1024, 0,
                                        AnyPropertyType, ctypes.byref(actual_type),
                                        ctypes.byref(actual_format),
                                        ctypes.byref(nitems),
                                        ctypes.byref(bytes_after),
                                        ctypes.byref(prop))
        if status == 0 and prop.value and nitems.value:
            try:
                if actual_format.value == 8:
                    raw = ctypes.string_at(prop, nitems.value)
                else:
                    raw = ctypes.string_at(prop, nitems.value * 4)
                text = raw.decode("utf-8", "replace").strip("\x00").strip()
                if text:
                    return text
            finally:
                x11.XFree(prop)
    return ""


def child_windows(client: XClient, parent: Window) -> list[Window]:
    root_ret = Window()
    parent_ret = Window()
    children = ctypes.POINTER(Window)()
    count = ctypes.c_uint()
    ok = x11.XQueryTree(client.display, parent, ctypes.byref(root_ret),
                        ctypes.byref(parent_ret), ctypes.byref(children),
                        ctypes.byref(count))
    if not ok or not children:
        return []
    try:
        return [Window(children[i]) for i in range(count.value)]
    finally:
        x11.XFree(children)


def active_window(client: XClient) -> Window:
    atom = x11.XInternAtom(client.display, b"_NET_ACTIVE_WINDOW", 1)
    actual_type = ctypes.c_ulong()
    actual_format = ctypes.c_int()
    nitems = ctypes.c_ulong()
    bytes_after = ctypes.c_ulong()
    prop = ctypes.c_void_p()
    status = x11.XGetWindowProperty(client.display, client.root, atom, 0, 1, 0,
                                    AnyPropertyType, ctypes.byref(actual_type),
                                    ctypes.byref(actual_format),
                                    ctypes.byref(nitems), ctypes.byref(bytes_after),
                                    ctypes.byref(prop))
    if status != 0 or not prop.value:
        return Window(0)
    try:
        return Window(ctypes.cast(prop, ctypes.POINTER(ctypes.c_ulong))[0])
    finally:
        x11.XFree(prop)


_default: XClient | None = None


def default_client() -> XClient:
    global _default
    if _default is None:
        _default = XClient()
    return _default
