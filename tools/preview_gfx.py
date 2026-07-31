"""Render the decoded ROM graphics to PNG sheets for visual verification.

    python tools/preview_gfx.py [outdir]

Produces:
    tiles_title.png  - 256-tile set with the logo overlay (title screen state)
    tiles_late.png   - 256-tile set with the late-stage BG overlays
    sprites.png      - 64 sprite patterns, 16x16, drawn as a silhouette
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pngwrite import write_rgb
from zanac_assets import GFX_BLOCKS, PALETTE, Rom, decompress, load_rom

BACKDROP = 1  # VDP R7 low nibble -> colour 1 (black)
SCALE = 3
GRID_BG = (40, 40, 48)


def build_tileset(rom: Rom, overlays: tuple[str, ...]) -> tuple[bytearray, bytearray]:
    """Return (patterns, colors), 256 tiles x 8 bytes each."""
    blocks = {b.name: b for b in GFX_BLOCKS}
    patterns = bytearray(2048)
    colors = bytearray(2048)
    for name in ("charset_bitmap", "charset_colors") + overlays:
        block = blocks[name]
        data = decompress(rom, block.src).data
        dst = patterns if block.kind == "pattern" else colors
        off = block.tile_index * 8
        dst[off : off + len(data)] = data
    return patterns, colors


def draw_tile_sheet(patterns: bytes, colors: bytes) -> tuple[int, int, bytes]:
    cols, rows, cell = 16, 16, 8 * SCALE + 1
    w, h = cols * cell + 1, rows * cell + 1
    buf = bytearray(bytes(GRID_BG) * (w * h))

    def put(px: int, py: int, rgb: tuple[int, int, int]) -> None:
        i = (py * w + px) * 3
        buf[i : i + 3] = bytes(rgb)

    for tile in range(256):
        tx, ty = tile % cols, tile // cols
        for row in range(8):
            bits = patterns[tile * 8 + row]
            attr = colors[tile * 8 + row]
            fg, bg = attr >> 4, attr & 0x0F
            for col in range(8):
                idx = fg if (bits >> (7 - col)) & 1 else bg
                rgb = PALETTE[idx or BACKDROP]
                for sy in range(SCALE):
                    for sx in range(SCALE):
                        put(
                            1 + tx * cell + col * SCALE + sx,
                            1 + ty * cell + row * SCALE + sy,
                            rgb,
                        )
    return w, h, bytes(buf)


def draw_sprite_sheet(sprites: bytes) -> tuple[int, int, bytes]:
    """Sprite pattern = 32 bytes: 16 rows of the left half, then the right half."""
    cols, rows, cell = 8, 8, 16 * SCALE + 1
    w, h = cols * cell + 1, rows * cell + 1
    buf = bytearray(bytes(GRID_BG) * (w * h))
    on, off = PALETTE[15], PALETTE[1]

    for pat in range(64):
        px0, py0 = (pat % cols) * cell + 1, (pat // cols) * cell + 1
        base = pat * 32
        for row in range(16):
            halves = (sprites[base + row], sprites[base + 16 + row])
            for half, bits in enumerate(halves):
                for col in range(8):
                    rgb = on if (bits >> (7 - col)) & 1 else off
                    x0 = px0 + (half * 8 + col) * SCALE
                    y0 = py0 + row * SCALE
                    for sy in range(SCALE):
                        i = ((y0 + sy) * w + x0) * 3
                        buf[i : i + 3 * SCALE] = bytes(rgb) * SCALE
    return w, h, bytes(buf)


def main() -> None:
    outdir = Path(sys.argv[1] if len(sys.argv) > 1 else "C:/Temp/zanac-gfx")
    outdir.mkdir(parents=True, exist_ok=True)
    rom = Rom(load_rom())

    for label, overlays in (
        ("title", ("logo_bitmap", "logo_colors")),
        (
            "late",
            (
                "bg_late_bitmap_a",
                "bg_late_colors_a",
                "bg_late_bitmap_b",
                "bg_late_colors_b",
            ),
        ),
    ):
        patterns, colors = build_tileset(rom, overlays)
        w, h, px = draw_tile_sheet(patterns, colors)
        write_rgb(outdir / f"tiles_{label}.png", w, h, px)

    sprites = decompress(rom, 0x6976).data
    w, h, px = draw_sprite_sheet(sprites)
    write_rgb(outdir / "sprites.png", w, h, px)

    print(f"wrote {outdir}")


if __name__ == "__main__":
    main()
