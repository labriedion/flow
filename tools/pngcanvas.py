"""A tiny dependency-free PNG writer (8-bit truecolor RGB).

Used by the artifact-generation scripts in this folder to render example images
for the projects' READMEs without pulling in Pillow/numpy. Just zlib + struct
from the standard library.
"""

from __future__ import annotations

import struct
import zlib


def write_rgb_png(path: str, width: int, height: int, buf: bytes | bytearray) -> None:
    """Write `buf` (length width*height*3, row-major RGB) to a PNG file."""
    if len(buf) != width * height * 3:
        raise ValueError("buffer size does not match width*height*3")

    def chunk(typ: bytes, data: bytes) -> bytes:
        out = struct.pack(">I", len(data)) + typ + data
        crc = zlib.crc32(typ + data) & 0xFFFFFFFF
        return out + struct.pack(">I", crc)

    # Prepend a filter byte (0 = none) to each scanline.
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw.extend(buf[y * stride:(y + 1) * stride])

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit, color type 2 (RGB)
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))
