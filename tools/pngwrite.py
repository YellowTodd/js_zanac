"""Dependency-free PNG writer (8-bit truecolour, no interlace)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def write_rgb(
    path: Path, width: int, height: int, pixels: bytes, payload: bytes | None = None
) -> None:
    """`pixels` is width*height*3 bytes of RGB, row-major, top-down.

    If `payload` is given it rides in a private ancillary chunk `zaNc`
    (zlib-compressed), so the visible image can be a human-readable sheet
    while the game's loader still gets the exact bytes. Image viewers ignore
    the chunk; web/src/assets.js prefers it over decoding IDAT.
    """
    if len(pixels) != width * height * 3:
        raise ValueError("pixel buffer size mismatch")
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None)
        raw += pixels[y * stride : (y + 1) * stride]
    out = b"\x89PNG\r\n\x1a\n" + _chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    )
    if payload is not None:
        out += _chunk(b"zaNc", zlib.compress(payload, 9))
    out += _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b"")
    path.write_bytes(out)
