---
address: 0x5CA5
kind: routine
name: load_charset_sprites
confidence: confirmed
calls:   [0x5CCF]
called_by: [0x412A, 0x428A]
tags: [graphics, vram, sprite]
sprint: "0007"
---

# load_charset_sprites

## Summary
Decompresses the full character set (tiles 0–255), all 64 sprite patterns, and
the character set colors into their permanent VRAM locations. Loads the complete
pattern and color tables for normal gameplay; called once at init and at
`init_screen_mode`.

## Analysis
Source lines 2025–2043. Seven calls to `decompress_block`; BC=0x800 stride:

| ROM source | Block | VRAM dest | Description |
|-----------|-------|-----------|-------------|
| 0x5EFC (`gfx_charset_bitmap`) | bitmap | 0x0000 PGT third 0 | charset tiles |
|   (same) | bitmap | 0x0800 PGT third 1 | replicated |
|   (same) | bitmap | 0x1000 PGT third 2 | replicated |
| 0x6976 (`gfx_sprite_patterns`) | sprites | 0x1800 SGT | 64 sprites |
| 0x64D3 (`gfx_charset_colors`) | colors | 0x2000 CT third 0 | tile colors |
|   (same) | colors | 0x2800 CT third 1 | replicated |
|   (same) | colors | 0x3000 CT third 2 | replicated |

**Replication mechanism**: `decompress_block` restores the original DE (ROM addr)
on exit, so three consecutive calls with the same DE but HL += 0x800 each time
replicate the same tile data across all three Screen-2 PGT/CT thirds.

The sprite patterns (0x6976) are loaded once (SGT has no thirds).

## Call sites
- Line 167 (`LAB_412A`): title-screen path (before `load_logo_tiles`).
- Line 331 (`init_screen_mode` = 0x428A): gameplay screen mode switch.
