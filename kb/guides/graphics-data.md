# Graphics data

The graphics are stored in a game-specific RLE compressed format.

Tiles or character blocks are 8x8 pixels and occupy 8 bytes as bitmap in VRAM plus 8 bytes as colors.

Sprites are 16x16 pixels occupying 32 bytes in VRAM.

The confirmed locations are:

- bitmap tiles for Zanac logo in title screen: 0x5D2C - 0x5eef = 61 tiles after decoding

- color tiles for Zanac logo in title screen: 0x5EF0 - 0x5efb = **61 tiles** after decoding
  (corrected 2026-07-30 — was recorded as 29; hand-decoding the 12 compressed
  bytes gives 488 bytes = 61 tiles, matching the bitmap block one-for-one, and
  the stream ends exactly at 0x5EFC where `gfx_charset_bitmap` starts. See
  [[gfx_logo_colors]].)

- bitmap tiles for full character set (alphabet, digits and main background graphics): 0x5EFC - 0x64d2 = 256 tiles tiles after decoding

- color tiles for full character set (alphabet, digits and main background graphics):
0x64D3 - 0x666e = 256 tiles tiles after decoding

- bitmap tiles for last stages background: 0x666F - 0x6704 = 20 tiles tiles after decoding

- more bitmap tiles for last stages background: 0x6705 - 0x68a8 = 67 tiles tiles after decoding

- color tiles for last stages background: 0x68A9 - 0x68dc = 20 tiles tiles after decoding

- more color tiles for last stages background: 0x68DD - 0x6975 = 69 tiles after decoding

- patterns for all sprites: 0x6976 - 0x70b8 = 64 sprites after decoding

## Full-coverage confirmation (sprint 0066)

The graphics region **0x5D2C–0x70B8 is fully tiled** by the KB `gfx_*` data
entries above — no gaps, no overlaps (verified against `tools/coverage_audit.py`
extents). Per-asset byte map:

| Range | Bytes | Asset |
|-------|-------|-------|
| 0x5D2C–0x5EEF | 452 | `gfx_logo_bitmap` |
| 0x5EF0–0x5EFB | 12 | `gfx_logo_colors` |
| 0x5EFC–0x64D2 | 1495 | `gfx_charset_bitmap` |
| 0x64D3–0x666E | 412 | `gfx_charset_colors` |
| 0x666F–0x6704 | 150 | `gfx_bg_late_bitmap_a` |
| 0x6705–0x68A8 | 420 | `gfx_bg_late_bitmap_b` |
| 0x68A9–0x68DC | 52 | `gfx_bg_late_colors_a` |
| 0x68DD–0x6975 | 153 | `gfx_bg_late_colors_b` |
| 0x6976–0x70B8 | 1859 | `gfx_sprite_patterns` |

(0x70B9+ is `entity_jump_table`, not graphics.) **Visual-confirmed (sprint
0066):** the title screen renders `gfx_logo_bitmap` + `gfx_charset_bitmap`
correctly, and an in-game frame renders `gfx_sprite_patterns` (ship/enemy/item)
and the tile-column/greeble terrain ([[tile_column_data_region1]] /
[[tile_column_data_region2]] + [[tile_tables]] via `scroll_map_reader`) —
`tools/zanac_shot.py`.
