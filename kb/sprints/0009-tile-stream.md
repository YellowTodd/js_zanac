---
id: "0009"
status: done
range: 0x95A8-0x9B24
strategy: forward_from_caller
budget_turns: 30
---

# Sprint 0009 — Ground-structure tile-stream helpers

## Goal
Decode the four sub-routines called from `scroll_map_reader` at 0x95A8 and
0x95ED (and their shared helper 0x9B22). Sprint 0008 labelled these as
"collision detection helpers" — verify or correct that hypothesis.

## Inputs
- `kb/symbols/0x9000-scroll/scroll_map_reader.md` — callers and context
- `source/zanac.asm` lines 6251–6294 (sub_95A8 and sub_95C0)
- `source/zanac.asm` lines 6295–6385 (sub_95ED / sub_95EF)
- `source/zanac.asm` lines 6720–6743 (second call site: inner stream loop)
- `source/zanac.asm` lines 6781–6790 (first call site: LAB_9a68)
- `source/zanac.asm` lines 6881–6924 (sub_9B22)

## Verification plan
- Static: check that every `CALL 0x95A8` and `CALL 0x95ED` site is consistent
  with the hypothesized role.
- Dynamic: set openMSX breakpoint at 0x9B22; read (0xE620 + HL) before and
  after to confirm it is scanning name-table tile values.

## Summary (filled at end)

**Hypothesis corrected:** 0x95A8 and 0x95ED are NOT player/bullet vs. tile
collision helpers. They are ground-structure tile-stream management routines,
part of the background-scroll engine's pipeline for placing ground obstacles
and base encounters as the level scrolls.

**`load_stream_slots` (0x95A8):**
Called from `scroll_map_reader`'s LAB_9a68 path and from LAB_9506. Reads a
count byte then N slot-configuration records from HL. For each record: decodes
a 4-bit stream-slot index, computes its 4-byte offset within the 0xE2E0 slot
table (IY = 0xE2E0 + index×4), and delegates to `init_stream_slot` (0x95C0)
to write the entry. Purpose: activate a new set of stream slots for an
incoming column group of ground-structure tiles.

**`init_stream_slot` (0x95C0):**
Helper for `load_stream_slots`. Reads tile-Y, an optional per-slot timer byte
(bit 3 of the slot index), and a 16-bit pointer into ROM tile-data from HL.
Writes the 4-byte slot entry at IY: `IY+0 = tile-Y + C` (row offset), timer
or data byte at `IY+1`, data pointer at `IY+2:3`. If the first tile at the
pointer is 0 (segment boundary), calls `place_tile_group` (0x95ED) to advance
to the next tile group.

**`place_tile_group` (0x95ED / also entered as 0x95EF):**
Called when a stream pointer hits a 0-byte (end of tile segment). Reads the
next tile-group descriptor from ROM: a control byte C (bit 7 = base structure,
bits 5-6 = width flags, bits 0-4 = column count B) and then B×3 tile
placement records. For each record calls `check_col_clear` (0x9B22) to test
the target name-table column; if clear, writes 3 bytes (Y-position, X-offset,
tile-pattern computed from `IY+0 × 8 + data`) to a placement buffer at HL.
When bit 7 of C is set, also advances a "base-attack" pointer at (0xE71E) and
increments (0xE151) / sets (0xE150)=1, signalling an active base encounter.

**`check_col_clear` (0x9B22):**
Scans the name-table shadow starting at 0xE620 at stride 32 (one MSX screen
row per step) for 21 rows. Three-phase check:
1. Walk backward 21 rows to find the first non-zero entry.
2. Walk forward 21 rows: if tile & 0x7F equals 0x14, 0x25, or 0x26, return
   carry clear (column is OK to use).
3. Walk backward again: if tile & 0x7F equals 0x27 or ≥ 0x46, return carry
   SET (column blocked by an existing ground structure). Otherwise carry clear.

**New KB files:**
`load_stream_slots` (0x95A8), `init_stream_slot` (0x95C0),
`place_tile_group` (0x95ED), `check_col_clear` (0x9B22).

**Updated KB files:**
`scroll_map_reader` — corrected calls list to use new names.

**Still uncertain:**
- 0xE620: address of the name-table shadow scanned by `check_col_clear`. Is it
  32×24 = 768 bytes (name table = 0xE620–0xE91F) or a different layout?
- 0xE150–0xE152: base-encounter counters written by `place_tile_group` when
  bit 7 of the tile-group control byte is set.
- 0xE71E: "base-attack list" write pointer incremented by `place_tile_group`.
- IX+0x1D (entity slot field): incremented by `place_tile_group` for
  multi-column (bit 5/6) structures; purpose not yet decoded.
- The ROM tile-stream data immediately following sub_9B22 (starting ~0x9B25)
  — likely the first ground-structure tile-group table.

**Next sprint candidates:**
- **0010 — Name-table shadow**: Confirm 0xE620 layout; read the routine(s)
  that write to it and verify that `check_col_clear` tile IDs 0x14, 0x25–0x27,
  0x46+ correspond to passable/blocking background tiles.
- **0011 — Base encounter**: Trace the consumers of 0xE150/0xE151/0xE71E to
  understand how a ground base is spawned and how it shoots.
- **0012 — Level map format**: Decode the ROM tile-stream data at 0x9B25+
  and the level map tables at 0xA444/0xA4A4/0xA564.
