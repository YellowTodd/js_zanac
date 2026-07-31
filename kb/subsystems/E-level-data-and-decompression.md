---
letter: E
title: Level Data & Decompression
coverage: done
status: done
---

# E — Level Data & Decompression

## Role

The data side of the background: the level/map script format, the tile-group
tables, the tile-column / greeble data, and the custom-RLE decompressor that
unpacks tile and graphics data into VRAM. Feeds tiles to
[[D-scroll-and-tile-rendering]] and graphics assets to the screens. The bulk map
data for all rounds lives in one large ROM block (0x9B64–0xBE27), now carved
into named sub-regions by [[level-data-block-map]].

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x412A | `load_bg_level` | likely | stage-multiple-of-8 level-load path (shared [[A-boot-and-init]]) |
| 0x51E6 | `lookup_word_table` | confirmed | dictionary word lookup |
| 0x5C60 | `load_bg_tiles` | confirmed | load BG tile patterns to VRAM |
| 0x5CA5 | `load_charset_sprites` | confirmed | load charset/sprite patterns |
| 0x5CCF | `decompress_block` | confirmed | the custom-RLE decompressor |
| 0x5D1A | `decompress_unit` | confirmed | emit one copy/repeat unit (sprint 0037) |
| 0x5C07 | `vdp_write_byte` | confirmed | VDP data-port write primitive (sprint 0037) |
| 0x5C2E | `dispatch_inline_table` | confirmed | shared computed-jump trampoline (also decompressor cmd dispatch) |
| 0xBE27 | `update_spawn_table_ptr` | confirmed | advance per-stage spawn pointer |

Shared VRAM text printers physically inside the decompressor block (used by
title/HUD, not decompression): `vram_string_copy` (0x5C10), `vram_print_inline`
(0x5C1F), `vdp_set_addr_write` (0x5C25), `vram_print_inline_hl` (0x5C28).

## Data

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x9B64–0xA443 | tile-column / greeble data (region 1) | confirmed | structure/placement records; pointed to by map-script cmd 1/2/3/B |
| 0xA444–0xA653 | `tile_tables` | confirmed | 5 base-layer 24-byte tile columns (incl. 0xA624/0xA63C fixed) |
| 0xA65C–0xB7A5 | `level_script_format` | confirmed | 9 row-triggered map scripts (ptr table 0x945C) |
| 0xB7A6–0xBE26 | tile-column / greeble data (region 2) + round/boss data | confirmed | structure records + round-transition text |
| 0xBE76–0xBF2B | `spawn_table` | confirmed | ground-structure spawn tables (3 sub-tables) |
| 0x5D2C–0x70B7 | gfx_* assets | confirmed | charset/logo/bg/sprite bitmaps+colors (see [[J-title-screen]], graphics-data) |

## Compression format

Custom **RLE with an escape byte + mode toggle** (matches `xtra/zanac-decoder.py`,
not LZ77): single-special = toggle copy/repeat; double-special + {00,01,02} =
STOP / SET-SPECIAL / MULTI. The STOP handler restores the original DE/HL so one
compressed block can be mirrored across all three Screen-2 thirds. See
[[decompress_block]].

## Guides

- `level-data-block-map` (full carve-up of 0x9B64–0xBE27), `graphics-data`,
  `db-sections-with-code`, `redisasm-protocol`.

## Status

**Done.** All E routines documented; the decompressor internals (sprint 0037)
and the string-print family are decoded; the level-data block is carved into
named sub-regions with owners and formats. Remaining "left open" items are
per-round *content* (byte-exact greeble-record fields and visual mapping), which
is data, not undocumented structure — see [[level-data-block-map]].

## Sprints

Done: 0007 (decompressor), 0029 (level data format), 0056 (map-script command
handlers), 0037 (decompressor internals + block map — closing slice).
