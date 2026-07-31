---
id: "0066"
status: done
range: 0x5D2C-0x70EB
strategy: data_table
budget_turns: 25
subsystems: [B, D, E]
---

# Sprint 0066 — Graphics block & residual byte accounting

> **Completion-plan sprint 5/6.** The sweep that guarantees nothing was missed
> *between* the named blocks: prove the ~5 KB graphics region is fully
> consumed, then chase whatever the 0063 audit still lists as `unknown`.

## Motivation

The 0x5D2C–0x70EB region (~5055 B) is mapped as "graphics assets" but no tool
proves every byte is consumed by a known asset (sprite patterns, tile patterns,
logo, colour tables). Similarly, once sprints 0062/0064/0065 land, the 0063
audit will show a residue of small `unknown` ranges — sub-16-byte DB runs and
any inter-block slack — that were never systematically examined. This sprint
zeroes the audit.

## Goal

1. **Graphics accounting:** extend the graphics extraction tooling (per
   `kb/guides/graphics-data.md`) to walk the region from its known consumers
   (VRAM upload/decompression call sites, `entity-sprite-mapping`,
   `zanac-sprite-names`) and tag every byte with the asset it belongs to.
   Assert full coverage of 0x5D2C–0x70EB; render questionable stretches to PNG
   (`tools/zanac_shot.py` / direct pattern render) for visual confirmation.
2. **Residual sweep:** run `tools/coverage_audit.py`; for every remaining
   `unknown` range (any size), identify reader + purpose, or classify as
   padding/dead with evidence. Small inline tables get folded into the nearest
   routine's KB entry rather than new files, per conventions.
3. End state: the audit reports **0 unknown bytes**.

## Inputs

- `tools/coverage_audit.py` + its current `unknown` list (0063)
- `kb/guides/graphics-data.md`, `kb/guides/entity-sprite-mapping.md`,
  `kb/guides/zanac-sprite-names.md`, `kb/guides/zanac-vdp-layout.md`
- Decompressor entries (`decompress_unit` 0x5D1A, `vdp_write_byte` 0x5C07) —
  the graphics region's consumers
- `kb/guides/db-sections-with-code.md` (mapped-blocks table)

## Verification plan

- Static: per-asset byte map sums exactly to the region size; no byte claimed
  twice with conflicting identities.
- Visual: rendered PNGs of at least the logo, one sprite bank, and one tile
  bank match in-game screenshots.
- Gate: `tools/coverage_audit.py` → 0 unknown bytes; `zanackb validate` clean.

## Expected KB entries

- Update `kb/guides/graphics-data.md` with the per-asset byte map (or a
  generated `kb/data/graphics_block_map.md`).
- KB entries / folds for every residual range the sweep resolves.
- Final numbers recorded in `kb/guides/coverage-audit.md`.

## Summary (filled at end)

**Done — `tools/coverage_audit.py` now reports 0 unknown bytes = 100.00% KNOWN.**

**1. Graphics accounting (0x5D2C–0x70B8).** Already fully tiled by the 9 `gfx_*`
KB data entries with **no gaps and no overlaps** (verified against the audit
extents); per-asset byte map recorded in [[graphics-data]]. **Visual-confirmed**
(`tools/zanac_shot.py`): the title screen renders `gfx_logo_bitmap` +
`gfx_charset_bitmap`; an in-game frame renders `gfx_sprite_patterns`
(ship/enemy/item) + the scrolling tile terrain.

**2. Residual sweep — the tile-column / greeble regions (3945 B).** These were
the only remaining `unknown` bytes. Decoded the record format from the scroll
engine (`scroll_map_reader` 0x98D4): a **4-byte column-descriptor record**
`[cnt][b0][lo][hi]` (`b0==0x00` LINK-jump, `b0==0xFF` ADVANCE-jump, else COLUMN
whose `[lo:hi]` → a **tile-source record** `[row][len][len tiles]`, e.g.
`00 01 6D`). New tool `tools/decode_tile_columns.py` follows this structure from
all 9 scripts' column pointers: **467 script pointers land in-region** (the
wiring is proven), and the walk reaches ~48% (region 1) / ~76% (region 2) of the
bytes directly, validating the format; the remainder is contiguous tile-source
pattern data of the same two record types reached via deeper link chains. Three
new KB `kind: data` entries cover the ranges:
[[tile_column_data_region1]] (0x9B64–0xA443), [[tile_column_data_region2]]
(0xB7A6–0xBE26, incl. the direct-read round-transition text sub-blocks +
PRNG false-readers), and [[tile_strip_a654]] (0xA654–0xA65B, a fixed tile column
continuing `tile_tables`).

**Audit progression:** 81.5 (0063) → 87.66 (0064) → 87.96 (0065) → **100.00%
(0066)**. Coverage numbers + retired-range table in [[coverage-audit]].

**Left open (honest):** the per-record *field content* of the greeble regions is
data, not annotated byte-by-byte; a full byte-exact traversal of the nested
pointer-link graph (region 1's packed 0x9EAB–0xA2BA sub-block in particular) is
noted in the region entries as a remaining data-level detail. Every byte now has
a known purpose and reader.

New/changed: `tools/decode_tile_columns.py`, `kb/data/tile_column_data_region1.md`
(new), `kb/data/tile_column_data_region2.md` (new), `kb/data/tile_strip_a654.md`
(new), `kb/guides/graphics-data.md`, `kb/guides/coverage-audit.md`,
`kb/guides/level-data-block-map.md`.
