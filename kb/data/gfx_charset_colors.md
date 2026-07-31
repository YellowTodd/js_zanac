---
address: 0x64D3
end: 0x666E
kind: data
name: gfx_charset_colors
confidence: confirmed
format: rle_graphics
sprint: "0007"
tags: [graphics, hud, rle]
---

# gfx_charset_colors

## Summary
RLE-compressed color data for the full 256-tile character set. Decompresses to
256 tiles × 8 bytes = 2 048 bytes of color-table entries.

## Analysis
Address range confirmed in `kb/features/graphics-data.md`.
Compressed size: 0x666E − 0x64D3 + 1 = 0x19C = 412 bytes → ratio ≈ 20 %.
High compression consistent with a palette of few color pairs across all tiles.

**VRAM destination (confirmed from `load_charset_sprites`):**
Loaded into all three Color Table thirds:
- Third 0: VRAM 0x2000–0x27FF
- Third 1: VRAM 0x2800–0x2FFF
- Third 2: VRAM 0x3000–0x37FF
(Same single compressed block decoded three times.)
