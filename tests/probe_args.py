from minecraft_tweaks import _x11 as x

at = x.x11.XCreateWindow.argtypes
print("count", len(at))
for i, t in enumerate(at):
    print(i, t)
