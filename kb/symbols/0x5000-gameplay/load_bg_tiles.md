---
address: 0x5C60
kind: routine
name: load_bg_tiles
confidence: confirmed
calls:   [0x5CCF]
called_by: []
tags: [graphics, background, vram]
sprint: "0007"
---

# load_bg_tiles

## Summary
Decompresses the late-stage background tile bitmaps and colors into VRAM. Loads
two bitmap groups and two color groups into specific tile offsets in all three
Screen-2 sections.

## Analysis
Source lines 1993–2024. Four compressed blocks; BC=0x800 stride:

| ROM source | Block | VRAM base (×3 thirds) | Tile offset |
|-----------|-------|----------------------|-------------|
| 0x666F (`gfx_bg_late_bitmap_a`) | bitmap | 0x00B8, 0x08B8, 0x10B8 | 23–42 (PGT) |
| 0x68A9 (`gfx_bg_late_colors_a`) | colors | 0x20B8, 0x28B8, 0x30B8 | 23–42 (CT)  |
| 0x6705 (`gfx_bg_late_bitmap_b`) | bitmap | 0x02D8, 0x0AD8, 0x12D8 | 90–156 (PGT) |
| 0x68DD (`gfx_bg_late_colors_b`) | colors | 0x22D8, 0x2AD8, 0x32D8 | 90–156 (CT)  |

Two ADD HL, BC skips between the bitmap and color groups bypass the SGT range.
No direct call site found in decoded code — likely called from a late-stage
trigger (scroll position or level milestone check).
