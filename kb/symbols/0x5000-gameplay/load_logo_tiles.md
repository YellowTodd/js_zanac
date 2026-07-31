---
address: 0x5C3C
kind: routine
name: load_logo_tiles
confidence: confirmed
calls:   [0x5CCF]
called_by: [0x412A]
tags: [graphics, title-screen, vram]
sprint: "0007"
---

# load_logo_tiles

## Summary
Decompresses the Zanac logo tile bitmaps and colors into VRAM, targeting tile
positions 176–236 in all three Screen-2 sections. Called during title-screen
initialization and again when returning to the title after a game.

## Analysis
Source lines 1976–1992. Two compressed blocks; each decoded into 3 VRAM thirds
(BC=0x800 stride; same ROM address re-used for all 3 calls):

| ROM source | Block | VRAM dest (×3 thirds) | Tile offset |
|-----------|-------|----------------------|-------------|
| 0x5D2C (`gfx_logo_bitmap`) | bitmap | 0x0580, 0x0D80, 0x1580 | 176–236 (PGT) |
| 0x5EF0 (`gfx_logo_colors`) | colors | 0x2580, 0x2D80, 0x3580 | 176–236 (CT)  |

The two skipped VRAM sections between bitmap and colors (0x1D80, 0x2080 in SGT
range) are bypassed with two consecutive ADD HL, BC.

## Call sites
- Line 168 (`LAB_412A`): title-screen initializer (after `CALL sub_5ca5`).
- Line 1593: called with `CALL 0x5189` (weapon init) before it; likely a
  "restart title" or "redraw logo" path after game over.
