"""Export the web port's assets from the ROM.

    python tools/export_assets.py [outdir]        (default: web/assets)

Emits:
  gfx.png       all nine graphics blocks, RLE-decoded and concatenated
  data.png      32 KB address-identity image holding only the *data* bytes
                (Z80 code and the now-redundant compressed graphics are
                zeroed), so JS can keep using the KB's absolute addresses
  manifest.json offsets, extents and provenance for both files

The payloads ride inside PNGs in a private `zaNc` chunk (a zlib stream the
loader inflates with DecompressionStream in the browser / node:zlib headless -
no canvas involved, so no premultiplication hazard). The visible pixels are
purely for humans: gfx.png shows the actual decoded tilesheet (charset, logo,
bg tiles, sprites) and data.png a byte map (one pixel per ROM byte, 256 per
row, code bytes black).

The data mask comes from tools/coverage_audit.py, which classifies every ROM
byte against source/zanac.asm + the KB (currently 100% known, 0 unknown).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coverage_audit import parse_asm, parse_kb
from pngwrite import write_rgb
from zanac_assets import (
    GFX_BLOCKS,
    PALETTE,
    ROM_BASE,
    ROM_SHA1,
    Rom,
    decompress,
    load_rom,
)

ROM_END = 0xC000
# The compressed graphics live here; the port ships gfx.bin instead.
GFX_REGION = (0x5D2C, 0x70B9)

# Tables the disassembler mis-decoded as instructions, so coverage_audit
# classifies them as code and they would otherwise be zeroed out of data.bin
# even though the running game reads them as data.
KEEP_RANGES = (
    # Type-35 death-explosion animation table, loaded at 0x84B3 as
    # `LD DE,0x84D1` and read by entity_update's animate step: 6 frames of
    # (sat_name, sat_colour). It starts inside the `JP 0x48D0` at 0x84D0 and
    # runs on through bytes shown as INC E / ADC A,D / ... in zanac.asm.
    (0x84D1, 0x84DD, "type-35 explosion anim table (6 x 2 bytes)"),
    # Player-death animation, loaded at 0x86D3 (`LD DE,0x86F3`); swallowed
    # by the RET at 0x86F4 and shown as INC E / ADD A,(HL) / ... in the asm.
    (0x86F3, 0x8709, "type-60 player death anim table (11 x 2 bytes)"),
    # large_descender_color_table (0x8EAF, 8 bytes) - labelled in the asm but
    # its bytes are still shown as ADD A,r instructions, so the audit counts
    # them as code. Read by the type-61 walker (0x8338) and the black shadow
    # (0x8E55) as a rotating colour palette.
    (0x8EAF, 0x8EB7, "large_descender_color_table (8 colours)"),
    # Crater strips read by the stamper 0x88ED: word table at 0x88AB
    # (subtypes 84-86 -> 0x88B1/0x88B8/0x88C2) then the strips themselves,
    # format [rowCount] then per row [width][tiles...]; they overlap to save
    # bytes and end right at the stamper's first instruction (0x88ED). The
    # asm shows them as CP/JR mnemonics, so the audit counts them as code.
    (0x88AB, 0x88ED, "crater tile strips + pointer table (0x88ED stamper)"),
    # Base-segment tables the disassembler renders as instructions. All four
    # are reached through `dispatch_inline_table` (0x5C2E) or `LD DE,nn`, so
    # the asm shows their bytes as code:
    #   0x8C1D  base_segment_draw jump table, 7 words (types 73-79)
    #   0x8CDA  wreck / core tile blocks, [rows]([len]tiles) each
    #   0x8D1C  base_segment_spawn_debris jump table, 7 words
    #   0x8DB3  the core's aimed-fan direction deltas (0, -1, +1, -2, +2)
    (0x8C1D, 0x8C2B, "base_segment_draw jump table (7 words)"),
    (0x8CDA, 0x8D14, "base segment wreck + core tile blocks"),
    (0x8D1C, 0x8D2A, "base_segment_spawn_debris jump table (7 words)"),
    (0x8DB3, 0x8DB8, "base core aimed-fan deltas (5 bytes)"),
    # entity_jump_table (0x70B7-0x716A, one word per entity type). The asm
    # emits the first 26 words as DB and then slips into instructions at
    # 0x70EB, so every handler pointer from type 26 up was being zeroed.
    (0x70EB, 0x716B, "entity_jump_table tail (types 26-89)"),
    # collision_size_table (0x45C9-0x4648), indexed by (sprite name) >> 1 and
    # read as a PAIR: [Y inset, X inset]. `collision_routine` (0x4560) and its
    # IX twin (0x45A0) shrink the nominal 16x16 cell by the inset on each side.
    # The asm renders all 128 bytes as NOP / INC BC / ... so the whole table
    # was being zeroed - every hitbox in the port became a full 16x16 cell.
    (0x45C9, 0x4649, "collision_size_table (128 bytes, 64 x [dy, dx])"),
    # ground_gun_param_table (0x8189): five 4-byte entries shared by entity
    # type PAIRS 46/47 .. 54/55, indexed ((type - 0x2E) & 0xFE) * 2.
    # [flags -> +0x05, colour -> +0x04, fire period -> +0x1E/+0x18,
    #  projectile type -> +0x1F]. Rendered as NOP / ADC A,A / JR NZ / ... in
    # the asm, so the whole table was being zeroed.
    (0x8189, 0x819D, "ground_gun_param_table (5 x 4 bytes, types 46-55)"),
    # Burster tables (types 34/65/66, handler 0x7F99): 4 x [X, dir] entry
    # pairs at 0x807C, two 3-dir lists (player above / below) at 0x8084 /
    # 0x8087, and 5 x [dy, dx] spread offsets at 0x808A.
    (0x807C, 0x8094, "burster entry/dir/offset tables (types 34/65/66)"),
    # The 1-UP's two 32-byte sprite frames (type 62, handler 0x8709): copied
    # by LDIRVM into VRAM 0x1800 (sprite pattern 0) every 16 frames.
    (0x876B, 0x87AB, "type-62 1-UP sprite frames (2 x 32 bytes)"),
)


def build_code_mask() -> bytearray:
    """1 = Z80 instruction byte (excluded from data.bin), 0 = data."""
    mask = bytearray(ROM_END - ROM_BASE)
    items, _ = parse_asm()
    for i, item in enumerate(items):
        start = item["addr"]
        nxt = items[i + 1]["addr"] if i + 1 < len(items) else ROM_END
        if item["kind"] != "code":
            continue
        span = max(1, min(nxt - start, 4))
        for a in range(start, min(start + span, ROM_END)):
            mask[a - ROM_BASE] = 1
    for lo, hi, _why in KEEP_RANGES:
        for a in range(lo, hi):
            mask[a - ROM_BASE] = 0
    return mask


# ---------------------------------------------------------------------------
# Visual sheets. The exact payload bytes ride in the PNG's private `zaNc`
# chunk (see pngwrite.write_rgb); the visible pixels are only for humans, so
# they can show the actual game graphics instead of packed-byte noise.
# ---------------------------------------------------------------------------

SHEET_BG = (24, 24, 28)
SHEET_W = 256  # 32 tiles, pre-scale
SCALE = 2


class Canvas:
    """Grow-down RGB canvas of fixed width."""

    def __init__(self, width: int):
        self.w = width
        self.buf = bytearray()

    @property
    def h(self) -> int:
        return len(self.buf) // (self.w * 3)

    def ensure(self, height: int) -> None:
        while self.h < height:
            row = bytearray()
            for _ in range(self.w):
                row += bytes(SHEET_BG)
            self.buf += row

    def put(self, x: int, y: int, rgb: tuple[int, int, int]) -> None:
        i = (y * self.w + x) * 3
        self.buf[i : i + 3] = bytes(rgb)

    def scaled(self, s: int) -> tuple[int, int, bytes]:
        w, h = self.w, self.h
        out = bytearray(w * s * h * s * 3)
        for y in range(h * s):
            src_row = (y // s) * w * 3
            for x in range(w * s):
                src = src_row + (x // s) * 3
                dst = (y * w * s + x) * 3
                out[dst : dst + 3] = self.buf[src : src + 3]
        return w * s, h * s, bytes(out)


def _draw_tile(cv: Canvas, x: int, y: int, pat: bytes, col: bytes | None,
               fg_def: int = 15, bg_def: int = 1) -> None:
    cv.ensure(y + 8)
    for r in range(8):
        bits = pat[r] if r < len(pat) else 0
        if col is not None and r < len(col):
            fg, bg = col[r] >> 4, col[r] & 0x0F
        else:
            fg, bg = fg_def, bg_def
        for c in range(8):
            idx = fg if bits & (0x80 >> c) else bg
            cv.put(x + c, y + r, PALETTE[idx] if idx else (0, 0, 0))


def _draw_label(cv: Canvas, x: int, y: int, text: str, charset: bytes) -> None:
    """Section captions, typeset with the game's own ASCII charset tiles."""
    cv.ensure(y + 8)
    for i, ch in enumerate(text.upper()):
        pat = charset[ord(ch) * 8 : ord(ch) * 8 + 8]
        for r in range(8):
            bits = pat[r] if r < len(pat) else 0
            for c in range(8):
                if bits & (0x80 >> c):
                    cv.put(x + i * 8 + c, y + r, (200, 200, 200))


def build_gfx_sheet(blocks: list[dict], gfx: bytes) -> tuple[int, int, bytes]:
    """Tilesheet: every decoded block drawn as the tiles/sprites it holds."""
    by_name = {b["name"]: gfx[b["offset"] : b["offset"] + b["length"]] for b in blocks}
    charset = by_name["charset_bitmap"]
    cv = Canvas(SHEET_W)
    y = 4

    pairs = [
        ("CHARSET", "charset_bitmap", "charset_colors"),
        ("ZANAC LOGO", "logo_bitmap", "logo_colors"),
        ("BG TILES A", "bg_late_bitmap_a", "bg_late_colors_a"),
        ("BG TILES B", "bg_late_bitmap_b", "bg_late_colors_b"),
    ]
    for label, pat_name, col_name in pairs:
        pat, col = by_name[pat_name], by_name[col_name]
        _draw_label(cv, 4, y, label, charset)
        y += 12
        tiles = len(pat) // 8
        for t in range(tiles):
            tx, ty = (t % 32) * 8, y + (t // 32) * 8
            _draw_tile(cv, tx, ty, pat[t * 8 : t * 8 + 8], col[t * 8 : t * 8 + 8])
        y += ((tiles + 31) // 32) * 8 + 8

    sprites = by_name["sprite_patterns"]
    _draw_label(cv, 4, y, "SPRITES", charset)
    y += 12
    count = len(sprites) // 32
    for sp in range(count):
        base = sp * 32
        sx, sy = (sp % 16) * 16, y + (sp // 16) * 16
        cv.ensure(sy + 16)
        for half in range(2):  # 16 bytes left column, 16 bytes right column
            for r in range(16):
                bits = sprites[base + half * 16 + r]
                for c in range(8):
                    if bits & (0x80 >> c):
                        cv.put(sx + half * 8 + c, sy + r, (255, 255, 255))
    y += ((count + 15) // 16) * 16 + 4
    cv.ensure(y)
    return cv.scaled(SCALE)


def build_data_sheet(payload: bytes) -> tuple[int, int, bytes]:
    """Byte map: one pixel per ROM byte, 256 per row (so x+256*y = offset
    from 0x4000). Zeroed (code) bytes are black; data bytes grey by value."""
    width = 256
    height = (len(payload) + width - 1) // width
    out = bytearray(width * height * 3)
    for i, v in enumerate(payload):
        g = 0 if v == 0 else 48 + (v * 207) // 255
        out[i * 3 : i * 3 + 3] = bytes((g, g, g))
    # scale x2 for viewability
    w2, h2 = width * 2, height * 2
    big = bytearray(w2 * h2 * 3)
    for yy in range(h2):
        src_row = (yy // 2) * width * 3
        for xx in range(w2):
            src = src_row + (xx // 2) * 3
            dst = (yy * w2 + xx) * 3
            big[dst : dst + 3] = out[src : src + 3]
    return w2, h2, bytes(big)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "web" / "assets"
    outdir.mkdir(parents=True, exist_ok=True)

    rom = Rom(load_rom())

    # ---- graphics -------------------------------------------------------
    gfx = bytearray()
    blocks = []
    for block in GFX_BLOCKS:
        decoded = decompress(rom, block.src)
        blocks.append(
            {
                "name": block.name,
                "kind": block.kind,
                "tile": block.tile_index,
                "offset": len(gfx),
                "length": len(decoded.data),
                "src": f"0x{block.src:04X}",
                "loader": block.loader,
            }
        )
        gfx += decoded.data
    w, h, pixels = build_gfx_sheet(blocks, bytes(gfx))
    write_rgb(outdir / "gfx.png", w, h, pixels, payload=bytes(gfx))

    # ---- sparse data image ----------------------------------------------
    mask = build_code_mask()
    data = bytearray(rom.data)
    zeroed = 0
    for i, is_code in enumerate(mask):
        if is_code:
            data[i] = 0
            zeroed += 1
    for addr in range(*GFX_REGION):
        if not mask[addr - ROM_BASE]:
            data[addr - ROM_BASE] = 0
            zeroed += 1
    w, h, pixels = build_data_sheet(bytes(data))
    write_rgb(outdir / "data.png", w, h, pixels, payload=bytes(data))

    manifest = {
        "source": {
            "sha1": ROM_SHA1,
            "base": ROM_BASE,
            "size": ROM_END - ROM_BASE,
        },
        "data": {
            "file": "data.png",
            "byteLength": ROM_END - ROM_BASE,
            "base": ROM_BASE,
            "size": ROM_END - ROM_BASE,
            "retainedBytes": (ROM_END - ROM_BASE) - zeroed,
            "note": "payload byte i is ROM address 0x4000+i; code zeroed; exact bytes in the PNG's zaNc chunk",
        },
        "gfx": {"file": "gfx.png", "byteLength": len(gfx), "blocks": blocks},
        "palette": [list(c) for c in PALETTE],
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    total = ROM_END - ROM_BASE
    for name, raw in (("gfx.png", len(gfx)), ("data.png", total)):
        on_disk = (outdir / name).stat().st_size
        print(f"{name:9} payload {raw:6d} B -> {on_disk:5d} B on disk")
    print(f"data retained {total - zeroed} B, zeroed {zeroed} B")
    print(f"-> {outdir}")


if __name__ == "__main__":
    main()
