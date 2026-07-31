---
address: 0xB7A6
end: 0xBE26
kind: data
name: tile_column_data_region2
confidence: likely
sprint: "0066"
tags: [scroll, level-map, tile, greeble, data-block, round-text, d-scroll, e-level]
---

# tile_column_data_region2 (0xB7A6–0xBE26, 1665 B)

Region 2 of the tile-column / greeble data (region 1 =
[[tile_column_data_region1]]), following the map scripts. Same two record types
consumed by `scroll_map_reader` (0x98D4): 4-byte **column-descriptor records**
`[cnt][b0][lo][hi]` (with `b0==0x00` LINK / `b0==0xFF` ADVANCE) and variable
**tile-source records** `[row][len][len tiles]`. Full format + reader quoted in
[[tile_column_data_region1]].

## Verification (`tools/decode_tile_columns.py`)

- **40 script column pointers target this region** (13 distinct entry points).
- Following the engine's record logic reaches **~76%** of the region's bytes
  directly; the rest is contiguous tile-source pattern data plus the direct-read
  text sub-blocks below.

## Direct-read sub-blocks (not via the scroll pointers)

Part of this region is read straight by round-transition code, not through the
column-group slots (per [[level-data-block-map]]):

| Addr | Reader | Content |
|------|--------|---------|
| 0xBBB4 | `sub_9433` (round setup) | round-setup data |
| 0xBBF3, 0xBBFD | round-number glyph blit (0x9260 / 0x929A) | round-number tiles |
| 0xBCB2 | 0x93E4 | round-transition data |

Solid-fill tile strips (e.g. 18× `0xB1` at 0xB994, `F1 F1 F0 F0 …` near 0xBE1C)
are large ground-structure fills.

## PRNG false-readers (not level-data consumers)

Two `LD (…),immediate` sites land in this region but only grab ROM bytes as
PRNG entropy (each followed by `LD A,R`): **0xB78E** (reader 0x715D) and
**0xB8FD** (reader 0x7DBF). Noted so they aren't mistaken for level-data reads.
(0xB007 is the third, in region 1's address space; see [[level-data-block-map]].)

`confidence: likely` — record formats/reader confirmed and pointer wiring
proven; byte-exact traversal of the full nested link graph is left open.

## See also

[[tile_column_data_region1]], [[tile_tables]], [[level_script_format]],
[[level-data-block-map]], [[scroll_map_reader]], [[spawn_table]].
