---
address: 0x5D2C
end: 0x5EEF
kind: data
name: gfx_logo_bitmap
confidence: confirmed
format: rle_graphics
sprint: "0007"
tags: [graphics, title-screen, rle]
---

# gfx_logo_bitmap

## Summary
RLE-compressed bitmap data for the Zanac logo tiles shown on the title screen.
Decompresses to 61 tiles × 8 bytes = 488 bytes of 8×8 pixel bitmaps.

## Analysis
Address range confirmed in `kb/features/graphics-data.md`.
Compressed size: 0x5EEF − 0x5D2C + 1 = 452 bytes → ratio ≈ 93 %.

This region is the START of the large DB block following `sub_5d1a` (0x5D1A).
The static disassembler emitted everything from 0x5D2C onwards as `DB` lines
because there are no labeled code-entry points into this range.

**VRAM destination (confirmed from `load_logo_tiles`):**
Loaded at tile offset 176 (0x0580 bytes into each PGT third):
- VRAM 0x0580, 0x0D80, 0x1580 (PGT thirds 0–2, tiles 176–236).
