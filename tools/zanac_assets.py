"""Zanac ROM asset extraction primitives.

Implements the game's custom RLE codec (`decompress_block` @0x5CCF, verified
against source/zanac.asm lines 2781-2854) plus the ROM/VRAM layout constants
taken from the three loader routines:

    load_logo_tiles      0x5C3C
    load_bg_tiles        0x5C60
    load_charset_sprites 0x5CA5

Used by tools/export_assets.py (web port asset pipeline) and by the PNG
preview dumper.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

ROM_PATH = Path(__file__).resolve().parent.parent / "rom" / "Zanac (Japan).rom"
ROM_SHA1 = "46e9ed7b7f6dfda8eee266476c9ebc4dd9d8fcc2"
ROM_BASE = 0x4000  # cartridge maps at page 1; ROM[0] == address 0x4000


def load_rom(path: Path = ROM_PATH) -> bytes:
    data = path.read_bytes()
    digest = hashlib.sha1(data).hexdigest()
    if digest != ROM_SHA1:
        raise SystemExit(f"ROM sha1 mismatch: {digest} != {ROM_SHA1}")
    if len(data) != 0x8000:
        raise SystemExit(f"unexpected ROM size {len(data)}")
    return data


class Rom:
    """Address-space view of the 32 KB cartridge (0x4000-0xBFFF)."""

    def __init__(self, data: bytes):
        self.data = data

    def __getitem__(self, addr: int) -> int:
        return self.data[addr - ROM_BASE]

    def slice(self, addr: int, length: int) -> bytes:
        off = addr - ROM_BASE
        return self.data[off : off + length]


# --------------------------------------------------------------------------
# RLE codec
# --------------------------------------------------------------------------

# Stream grammar (special byte starts at 0xFF, mode starts at "copy"):
#   <byte != special>            -> emit one unit
#   <special> <byte != special>  -> toggle copy/repeat mode, re-read the byte
#   <special> <special> 0x00     -> STOP
#   <special> <special> 0x01 X   -> set special byte to X
#   <special> <special> 0x02 M N -> re-run the next N units, M times
#
# One "unit" is a single literal byte in copy mode, or a (value, count) pair
# in repeat mode. Z80 DJNZ/DEC-C semantics mean a count of 0 means 256.


@dataclass
class Decoded:
    data: bytearray
    src_start: int
    src_end: int  # first address past the STOP marker

    @property
    def packed_size(self) -> int:
        return self.src_end - self.src_start


def _emit_unit(rom: Rom, hl: int, value: int, mode: int, out: bytearray) -> int:
    if mode & 1:  # repeat
        count = rom[hl]
        hl += 1
        out.extend(bytes([value]) * (count or 256))
    else:  # copy
        out.append(value)
    return hl


def decompress(rom: Rom, src: int, limit: int = 0x4000) -> Decoded:
    """Decode one compressed block starting at ROM address `src`."""
    out = bytearray()
    special = 0xFF
    mode = 0
    hl = src

    while True:
        if len(out) > limit:
            raise ValueError(f"runaway decode at 0x{src:04X} ({len(out)} bytes)")
        value = rom[hl]
        hl += 1

        if value != special:
            hl = _emit_unit(rom, hl, value, mode, out)
            continue

        value = rom[hl]
        hl += 1
        if value != special:
            hl -= 1  # the byte belongs to the stream, not to us
            mode ^= 1
            continue

        cmd = rom[hl]
        hl += 1
        if cmd == 0x00:  # STOP
            return Decoded(out, src, hl)
        if cmd == 0x01:  # SET SPECIAL
            special = rom[hl]
            hl += 1
            continue
        if cmd == 0x02:  # MULTI
            outer = rom[hl] or 256
            hl += 1
            block = hl
            for _ in range(outer):
                hl = block
                inner = rom[hl] or 256
                hl += 1
                for _ in range(inner):
                    value = rom[hl]
                    hl += 1
                    hl = _emit_unit(rom, hl, value, mode, out)
            continue
        raise ValueError(f"unknown RLE command 0x{cmd:02X} at 0x{hl - 1:04X}")


# --------------------------------------------------------------------------
# Asset table
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class GfxBlock:
    """One compressed graphics block and where the loader puts it."""

    name: str
    src: int
    vram: int  # first-bank VRAM destination
    kind: str  # "pattern" | "color" | "sprite"
    loader: str

    @property
    def tile_index(self) -> int:
        """Destination expressed as a tile number within the 256-tile set."""
        return (self.vram & 0x07FF) // 8


# All three loaders write the *same* decoded bytes to all three Screen-2 banks
# (HL += 0x800 between calls), so the pattern/color tables are bank-uniform:
# the port only needs one 256-entry tile set. See load_* routines above.
GFX_BLOCKS: tuple[GfxBlock, ...] = (
    GfxBlock("charset_bitmap", 0x5EFC, 0x0000, "pattern", "load_charset_sprites"),
    GfxBlock("charset_colors", 0x64D3, 0x2000, "color", "load_charset_sprites"),
    GfxBlock("sprite_patterns", 0x6976, 0x1800, "sprite", "load_charset_sprites"),
    GfxBlock("bg_late_bitmap_a", 0x666F, 0x00B8, "pattern", "load_bg_tiles"),
    GfxBlock("bg_late_colors_a", 0x68A9, 0x20B8, "color", "load_bg_tiles"),
    GfxBlock("bg_late_bitmap_b", 0x6705, 0x02D8, "pattern", "load_bg_tiles"),
    GfxBlock("bg_late_colors_b", 0x68DD, 0x22D8, "color", "load_bg_tiles"),
    GfxBlock("logo_bitmap", 0x5D2C, 0x0580, "pattern", "load_logo_tiles"),
    GfxBlock("logo_colors", 0x5EF0, 0x2580, "color", "load_logo_tiles"),
)


# TMS9918A palette. The datasheet values in kb/guides/vdp-tms9918a.md put
# medium green (33,200,66) and dark green (33,176,59) almost on top of each
# other, which flattens Zanac's grass (FG dark on BG medium) into one bright
# tone. This is the measured NTSC set most emulators ship (WebMSX/blueMSX),
# whose green separation matches reference screenshots. Index 0 is
# transparent; the port paints it with the backdrop colour (R7 low nibble = 1).
PALETTE: tuple[tuple[int, int, int], ...] = (
    (0, 0, 0),
    (0, 0, 0),
    (62, 184, 73),
    (116, 208, 125),
    (89, 85, 224),
    (128, 118, 241),
    (185, 94, 81),
    (101, 219, 239),
    (219, 101, 89),
    (255, 137, 125),
    (204, 195, 94),
    (222, 208, 135),
    (58, 162, 65),
    (183, 102, 181),
    (204, 204, 204),
    (255, 255, 255),
)
