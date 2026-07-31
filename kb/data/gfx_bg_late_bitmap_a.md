---
address: 0x666F
end: 0x6704
kind: data
name: gfx_bg_late_bitmap_a
confidence: confirmed
format: rle_graphics
sprint: "0007"
tags: [graphics, background, rle]
---

# gfx_bg_late_bitmap_a

## Summary
RLE-compressed bitmap tiles for the late-stage background (first block). 20 tiles
after decompression.

## Analysis
Address range confirmed in `kb/features/graphics-data.md`.
Compressed size: 0x6704 − 0x666F + 1 = 0x96 = 150 bytes.

**VRAM destination (from `load_bg_tiles`):** tile offset 23 (0x00B8 bytes in):
VRAM 0x00B8, 0x08B8, 0x10B8 (PGT thirds 0–2, tiles 23–42).
