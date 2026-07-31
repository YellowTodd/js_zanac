---
id: "0006"
status: done
range: 0x70B7-0x7FFF
strategy: forward_from_caller
budget_turns: 30
---

# Sprint 0006 — Entity type survey

## Goal
For each entry in `entity_jump_table` (0x70B7), decode the first-frame
initialization block of the handler to find which sprite pattern it writes.
Cross-reference against `kb/features/zanac-sprite-names.md` to assign a name to
every active entity type (1–25+).

## Inputs
- `kb/data/entity_jump_table.md` — handler addresses for all 26 entries
- `kb/features/zanac-sprite-names.md` — pattern 0–63 → semantic name
- `kb/data/entity_table.md` — slot layout (offset 0 = type, offsets 1–11 = pos/vel)
- `kb/data/gfx_sprite_patterns.md` — boundary note (handlers start above 0x70EB)
- `source/zanac.asm` lines around handler addresses (computed per type)

## Verification plan
- Static: type 1 handler already confirmed to write slot Y=0xA0, X=0x78.
  Equivalent init block in each handler reveals the pattern number.
- Pattern written to sprite shadow: look for `LD (HL), N` immediately before
  `LD A, (IX+1); LD (HL), A` (the Y/X write sequence).

## Summary

**Sprite shadow write routine confirmed (0x48A9 = `sprite_shadow_push`):**
Each entity handler calls this to append a 4-byte SAT shadow entry:
`{slot[1]−17, slot[2], slot[3], slot[4]}` = `{Y, X, SAT-name, SAT-color}`.
SAT name byte encoding: pattern_index = `slot[3] >> 2` (TMS9918A 16×16 mode).

**Graphics data incorporated:**
Nine `kb/data/gfx_*.md` entries created for all confirmed compressed-data regions
(0x5D2C–0x70B6). The "big DB block" is now fully accounted for: graphics data,
then entity jump table, then entity handler code — all in the same unlabeled
0x5D2C+ region.

**Type 1 = player ship confirmed:**
Handler at 0x75D5 initialises `slot[3]=0x38 → pattern_index=14 → player ship`
(sprite names: patterns 14-15 = player ship + shadow). Y_init=0xA0 (bottom of
screen), X_init=0x78 (center). The player entity at 0xE100 stores *game state*
(lives, weapon level); the entity slot at 0xE300[0] stores the *sprite state*.

**Type 2: dynamic pattern.** `slot[3] = (0xE10F)` (level parameter), vy set from
`~(0xE10E)`. Pattern varies per difficulty level — cannot be statically fixed.

**Type 3: player-bullet spawner.** Calls `sub_5189` (bullet-slot allocator) with
weapon type A=6, then dispatches on `fire_num` via `sub_5c2e` computed jump.
Does not render directly through the entity slot SAT shadow path.

**Types 4–6 (shared 0x7826): periodic-spawn entities.** Countdown in slot[3]
before initialization; once countdown reaches 0, CALL 0x71DA sets position and
pattern is written elsewhere. Pattern TBD.

**`sub_5c2e` pattern identified:** `CALL sub_5c2e; DW t0; DW t1; …` — A is used
as a word-table index from the return address. Enables compact dispatch by weapon
or difficulty level.

**Updated KB:**
- `entity_table.md`: slot[1] = sprite bottom-edge row (SAT_Y = slot[1]-17);
  slot[3] = SAT name byte; slot[4] = SAT color byte — all confirmed.
- `entity_jump_table.md`: type 1 = player ship (confirmed), type 2 = dynamic.

**Still uncertain:**
- Types 3–26 pattern mapping (dynamic or handler-internal).
- Why player ship entity lives in `entity_dispatch` table AND has a separate struct
  at 0xE100 (game state vs. sprite state split).
- Whether `entity_dispatch` type IDs have any relation to sprite pattern IDs.

**Next sprint candidates:**
- **0007 — Decompressor**: Find the RLE decode routine called to load `gfx_*` data
  into VRAM (sprint 0002 found `LD DE, 0x5D2C` at `SUB_ram_5c3c`; that's the entry
  point). Confirming the compression format enables future sprite extraction.
- **0008 — 0x9A79 (enemy-update ISR call)**: Decode the routine called every
  VBLANK; expected to contain sprite coordinate update + collision.
- **0009 — Live entity survey (openMSX)**: Read 0xE300 slots during gameplay to
  map entity type IDs → observed sprite patterns; correlate with `zanac-sprite-names.md`.
