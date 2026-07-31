---
address: 0x5EFC
end: 0x64D2
kind: data
name: gfx_charset_bitmap
confidence: confirmed
format: rle_graphics
sprint: "0007"
tags: [graphics, hud, rle]
---

# gfx_charset_bitmap

## Summary
RLE-compressed bitmap data for the full character set: alphabet, digits, and
main background/HUD graphics. Decompresses to 256 tiles × 8 bytes = 2 048 bytes.

## Analysis
Address range confirmed in `kb/features/graphics-data.md`.
Compressed size: 0x64D2 − 0x5EFC + 1 = 0x5D7 = 1495 bytes → ratio ≈ 73 %.

**VRAM destination (confirmed from `load_charset_sprites`):**
Loaded into all three Pattern Generator Table thirds:
- Third 0: VRAM 0x0000–0x07FF
- Third 1: VRAM 0x0800–0x0FFF
- Third 2: VRAM 0x1000–0x17FF
(Same single compressed block decoded three times.)
