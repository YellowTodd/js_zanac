---
address: 0x68A9
end: 0x68DC
kind: data
name: gfx_bg_late_colors_a
confidence: confirmed
format: rle_graphics
sprint: "0007"
tags: [graphics, background, rle]
---

# gfx_bg_late_colors_a

## Summary
RLE-compressed color tiles for the late-stage background (first block). 20 tiles
after decompression.

## Analysis
Address range confirmed in `kb/features/graphics-data.md`.
Compressed size: 0x68DC − 0x68A9 + 1 = 0x34 = 52 bytes.

**VRAM destination (from `load_bg_tiles`):** tile offset 23 (0x00B8 into CT):
VRAM 0x20B8, 0x28B8, 0x30B8 (CT thirds 0–2, tiles 23–42).
