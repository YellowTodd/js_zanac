---
title: Level-data block map (0x9B64–0xBE27)
tags: [scroll, level-map, tile, data-block]
sprint: "0037"
---

# Level-data block map — 0x9B64–0xBE27

The single largest contiguous data block in the ROM (~8899 bytes) is the
**level / scroll data** for all rounds. Sprint 0029 documented the *formats*
(map-script commands, tile tables, spawn tables); this guide carves the whole
block into its named constituent sub-regions and gives each an owner and format
so nothing in the range is "unclassified" any more. Per-round *byte content*
remains data (not annotated byte-by-byte) — but every byte now has a known
purpose and reader.

## Layout

| Range | Bytes | Region | Format / reader |
|-------|-------|--------|-----------------|
| 0x9B64–0xA443 | 2272 | **Tile-column / greeble data — region 1** | → [[tile_column_data_region1]] (KB'd 0066). Column-descriptor + tile-source records read by `scroll_map_reader`; pointed to by map-script `cmd 2/4/5/B` operands. See below. |
| 0xA444–0xA653 | 528 | **`tile_tables`** (5 base-layer columns) | 24-byte vertical tile columns; `sub_9888`/`sub_4236`. → [[tile_tables]] |
| 0xA654–0xA65B | 8 | Tile strip | → [[tile_strip_a654]] (KB'd 0066). `6F 70 71 72 1D 72 7B 7C` — a fixed tile column continuing `tile_tables` |
| 0xA65C–0xB7A4 | 4425 | **Map scripts** (9 scripts) | Row-triggered command stream. → [[level_script_format]] |
| 0xB7A5 | — | Script[0] (terminal/entry) | Highest entry in the 0x945C pointer table |
| 0xB7A6–0xBE26 | 1665 | **Tile-column / greeble data — region 2** + round/boss data | → [[tile_column_data_region2]] (KB'd 0066). Same records as region 1 + direct-read round-transition text at 0xBBB4/0xBBF3/0xBBFD, 0xBCB2. See below. |
| 0xBE27– | (code) | `update_spawn_table_ptr` | Routine, not data. → [[update_spawn_table_ptr]] |
| 0xBE76–0xBF2B | 182 | **`spawn_table`** (3 sub-tables) | Timer reloads / position pairs / entity-type list. → [[spawn_table]] |

## Map scripts — the 9-entry pointer table (0x945C)

`sub_9444` (0x9444) selects a script by scroll position from this table (LE
words, index 0..8); the value is stored to `stage_index` (0xE701). Addresses are
**ascending with descending index**, so they double as script boundaries:

| Idx | Ptr | Script range |
|-----|-----|--------------|
| 8 | 0xA65C | 0xA65C–0xA750 |
| 7 | 0xA751 | 0xA751–0xAAEE |
| 6 | 0xAAEF | 0xAAEF–0xAD60 |
| 5 | 0xAD61 | 0xAD61–0xAF1E |
| 4 | 0xAF1F | 0xAF1F–0xB1DD |
| 3 | 0xB1DE | 0xB1DE–0xB3FC |
| 2 | 0xB3FD | 0xB3FD–0xB619 |
| 1 | 0xB61A | 0xB61A–0xB7A4 |
| 0 | 0xB7A5 | 0xB7A5 (terminal) |

Each script is a forward-only `[row:2 LE][cmd:1][operands]` stream; see
[[level_script_format]] for the 13-command table and `tools/decode_mapscript.py`.

## Tile-column / greeble data (regions 1 & 2)

The two data regions bracketing the scripts hold the actual background
decoration ("greebles") and ground-structure tile patterns that the scripts
splice into the scrolling map. The scripts reference them **by pointer**:
`cmd 2` column-group specs carry a 16-bit `ptr` (byte3/4) and `cmd B`
wide-structure records carry a pointer; a scan of the script bytes shows these
pointers cluster into exactly these two regions (heaviest at 0x9C00–0x9F00 and
0xA100–0xA3FF in region 1, and 0xB800–0xBC00 in region 2).

Two record shapes are visible:

- **3-byte placement records** — region 1 opens with `00 01 6D | 00 01 6B |
  00 01 69 | …` (a `[00][01][tile]` triple, descending tile IDs), matching the
  `cmd 1` placement-record format (count N + N×3).
- **Structure records with embedded tile-column pointers** — e.g. region 2
  `… 08 44 A7 B9 …` where `A7 B9` = LE pointer 0xB9A7 into the same region;
  and blocks like `01 08 7D B9 B8 0B 85 …` at 0xB904. Runs of a single tile ID
  (e.g. 18× `0xB1` at 0xB994, or `F1 F1 F0 F0 …` near 0xBE1C) are solid-fill
  tile strips for large ground structures.

Round-transition / boss-intro data also lives in region 2 and is read directly
by code (not via the script pointers): 0xBBB4 (`sub_9433` round setup), 0xBBFD
and 0xBBF3 (round-number glyph blit at 0x9260/0x929A), 0xBCB2 (0x93E4), and the
per-round script pointer 0xA6F4 (0x92AF) inside the script region.

## PRNG "false readers"

Three `LD (HL/DE),0xBxxx` immediates land in this block but are **not** level-data
consumers — they are pseudo-random-number entropy grabs that read ROM bytes as a
random pool (each is immediately followed by `LD A,R`):

| Addr | Reader | Note |
|------|--------|------|
| 0xB007 | 0x7C02, 0x7CAD | `LD DE,0x4001; LD HL,0xB007; LD A,R` — RNG seed |
| 0xB78E | 0x715D | `LD A,(0xB78E); ADC A,(HL)` — RNG mix |
| 0xB8FD | 0x7DBF | `LD DE,0xB8FD; LD A,R` — RNG seed |

They are noted here so future readers don't mistake weapon/entity code for a
level-data reader.

## Left open

- Byte-exact decode of the structure-record format in regions 1 & 2 (the
  variable greeble/structure sub-records parsed by `0x97BC`/`0x95A8`/`0x95C0`).
  The *pointer wiring* (which script points where) and the record *shapes* are
  known; the semantics of every field are not.
- Per-round visual mapping (which greeble block draws what on screen) — would
  need live screenshots per round rather than static analysis.
