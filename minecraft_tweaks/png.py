"""Чтение и запись PNG без внешних зависимостей.

Поддержка: 8 бит на канал, типы цвета 2 (RGB) и 6 (RGBA), фильтры 0-4,
без интерлейса. Этого хватает для текстур, спрайтов и скриншотов.
"""

from __future__ import annotations

import struct
import zlib
from typing import Tuple

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read(data_path: str) -> Tuple[int, int, bytearray]:
    """Читает PNG → (width, height, BGRA-буфер без премультипликации)."""
    with open(data_path, "rb") as fh:
        raw = fh.read()
    if not raw.startswith(PNG_SIG):
        raise ValueError("не PNG: " + data_path)

    pos = len(PNG_SIG)
    width = height = depth = color = interlace = 0
    idat = bytearray()
    while pos < len(raw):
        (length,) = struct.unpack(">I", raw[pos:pos + 4])
        ctype = raw[pos + 4:pos + 8]
        body = raw[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, depth, color, _comp, _filt, interlace = struct.unpack(">IIBBBBB", body)
        elif ctype == b"IDAT":
            idat += body
        elif ctype == b"IEND":
            break

    if depth != 8 or color not in (2, 6) or interlace != 0:
        raise ValueError(f"неподдерживаемый PNG: depth={depth} color={color} interlace={interlace}")

    channels = 3 if color == 2 else 4
    stride = width * channels
    data = zlib.decompress(bytes(idat))

    out = bytearray(width * height * 4)
    prev = bytearray(stride)
    src = 0
    for y in range(height):
        ftype = data[src]
        src += 1
        line = bytearray(data[src:src + stride])
        src += stride
        if ftype == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                upleft = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(left, prev[i], upleft)) & 0xFF
        prev = line

        dst = y * width * 4
        if channels == 4:
            for x in range(width):
                r, g, b, a = line[x * 4:x * 4 + 4]
                out[dst:dst + 4] = bytes((b, g, r, a))
                dst += 4
        else:
            for x in range(width):
                r, g, b = line[x * 3:x * 3 + 3]
                out[dst:dst + 4] = bytes((b, g, r, 255))
                dst += 4
    return width, height, out


def write(data_path: str, width: int, height: int, bgra: bytes | bytearray) -> None:
    """Пишет BGRA-буфер (прямой, без премультипликации) в PNG."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # filter: none
        src = y * width * 4
        line = bytearray(width * 4)
        for x in range(width):
            b, g, r, a = bgra[src:src + 4]
            line[x * 4:x * 4 + 4] = bytes((r, g, b, a))
            src += 4
        rows += line

    def chunk(tag: bytes, body: bytes) -> bytes:
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    with open(data_path, "wb") as fh:
        fh.write(PNG_SIG)
        fh.write(chunk(b"IHDR", ihdr))
        fh.write(chunk(b"IDAT", zlib.compress(bytes(rows), 6)))
        fh.write(chunk(b"IEND", b""))
