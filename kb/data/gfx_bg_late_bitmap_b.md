---
address: 0x6705
end: 0x68A8
kind: data
name: gfx_bg_late_bitmap_b
confidence: confirmed
format: rle_graphics
sprint: "0007"
tags: [graphics, background, rle]
---

# gfx_bg_late_bitmap_b

## Summary
RLE-compressed bitmap tiles for the late-stage background (second block). 67 tiles
after decompression.

## Analysis
Address range confirmed in `kb/features/graphics-data.md`.
Compressed size: 0x68A8 − 0x6705 + 1 = 0x1A4 = 420 bytes.
Note: source line 2010 references `LD DE, 0x6705`, identifying this address as a
decompressor argument — consistent with the confirmed range.

**VRAM destination (from `load_bg_tiles`):** tile offset 90 (0x02D8 bytes in):
VRAM 0x02D8, 0x0AD8, 0x12D8 (PGT thirds 0–2, tiles 90–156).
