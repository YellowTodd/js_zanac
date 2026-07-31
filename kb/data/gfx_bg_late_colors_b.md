---
address: 0x68DD
end: 0x6975
kind: data
name: gfx_bg_late_colors_b
confidence: confirmed
format: rle_graphics
sprint: "0007"
tags: [graphics, background, rle]
---

# gfx_bg_late_colors_b

## Summary
RLE-compressed color tiles for the late-stage background (second block). 69 tiles
after decompression.

## Analysis
Address range confirmed in `kb/features/graphics-data.md`.
Compressed size: 0x6975 − 0x68DD + 1 = 0x99 = 153 bytes.

**VRAM destination (from `load_bg_tiles`):** tile offset 90 (0x02D8 into CT):
VRAM 0x22D8, 0x2AD8, 0x32D8 (CT thirds 0–2, tiles 90–156).
