---
address: 0x5EF0
end: 0x5EFB
kind: data
name: gfx_logo_colors
confidence: confirmed
format: rle_graphics
sprint: "0007"
tags: [graphics, title-screen, rle]
---

# gfx_logo_colors

## Summary
RLE-compressed color data for the Zanac logo tiles. Decompresses to **61 color
tile entries × 8 bytes = 488 bytes**, matching `gfx_logo_bitmap` tile for tile.
Twelve compressed bytes expand 40× because the logo uses only three colour
pairs, all on a transparent background.

## Analysis
Address range confirmed in `kb/features/graphics-data.md`.
Immediately follows `gfx_logo_bitmap` at 0x5EEF.

### Decoded content (corrected 2026-07-30)

The stored bytes are `FF F0 00 F0 28 E0 90 60 30 FF FF 00`. Decoding them by
hand against `decompress_block` (special = 0xFF, initial mode = copy):

| Stream | Meaning | Output |
|--------|---------|--------|
| `FF` + `F0` | single special → switch to repeat mode | — |
| `F0 00` | value 0xF0, count 0 ⇒ 256 | 256 × `F0` |
| `F0 28` | value 0xF0, count 0x28 | 40 × `F0` |
| `E0 90` | value 0xE0, count 0x90 | 144 × `E0` |
| `60 30` | value 0x60, count 0x30 | 48 × `60` |
| `FF FF 00` | double special, cmd 0 | STOP |

256 + 40 + 144 + 48 = **488 bytes**, and the stream ends at 0x5EFC — exactly
where `gfx_charset_bitmap` begins, so the extent is self-checking.

Colour pairs are foreground-on-transparent: `F0` = white (37 tiles, the
wordmark), `E0` = grey (18 tiles, the shading and baseline bar), `60` = dark
red (6 tiles, 0xE7–0xEC — the PONYCA mark drawn by `draw_title_text`).

The earlier "29 tiles / 232 bytes" figure was wrong; it did not match the 61
tiles `gfx_logo_bitmap` defines at the same VRAM offset.

**VRAM destination (confirmed from `load_logo_tiles`):**
Loaded at tile offset 176 (0x0580 bytes into each CT third):
- VRAM 0x2580, 0x2D80, 0x3580 (CT thirds 0–2, tiles 176–236).
