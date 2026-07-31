---
address: 0x6976
end: 0x70B8
kind: data
name: gfx_sprite_patterns
confidence: confirmed
format: rle_graphics
sprint: "0007"
tags: [graphics, sprite, rle]
---

# gfx_sprite_patterns

## Summary
RLE-compressed data for all 64 sprite patterns (patterns 0–63). Decompresses to
64 sprites × 32 bytes = 2 048 bytes loaded into VRAM sprite-generator table at
base 0x1800.

## Analysis
Address range confirmed in `kb/features/graphics-data.md`. End address is 0x70B6
(inclusive); the entity-type jump table begins immediately at 0x70B7.
Compressed size: 0x70B6 − 0x6976 + 1 = 0x741 = 1857 bytes → ratio ≈ 91 %.

Sprite pattern numbering (from `kb/features/zanac-sprite-names.md`):
- Pattern 1: power chip; 2: comet; 3: target; 4: snowflake; 5: small star
- Pattern 6: light bar; 7: lead; 8–9: circles; 10–12: fire (single/double/triple)
- Pattern 13: super hard bolt; 14–15: player ship + complement
- Patterns 16+ : enemies and their complement sprites (see sprite-names.md for full list)
Each 16×16 sprite occupies 32 bytes (two 8×8 half-tiles side by side).

**VRAM destination (confirmed from `load_charset_sprites`):**
Sprite Generator Table: VRAM 0x1800–0x1FFF (64 sprites × 32 bytes = 2 048 bytes).
Decoded once (no Screen-2 section replication needed for sprites).

## Boundary note

The RLE stream terminates with the escape sequence `AA 00` at 0x70B7–0x70B8
(escape byte 0xAA followed by count 0x00 = end of stream). These two bytes are
therefore the **last two bytes of sprite data**, not part of the jump table.

`entity_dispatch` (0x445F) uses the virtual base `LD DE, 0x70B7` so that
`0x70B7 + type×2` addresses each handler. For type 0 (never dispatched) this
would read 0x70B7–0x70B8 = `AA 00` = 0x00AA, which is harmless since type 0
is always skipped. The **physical** jump table begins at 0x70B9 (type 1).
