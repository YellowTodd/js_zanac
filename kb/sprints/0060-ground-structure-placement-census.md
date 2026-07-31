---
id: "0060"
status: done
range: 0xA65C-0xB7A5
strategy: live_capture
budget_turns: 30
subsystems: [G, D, M]
---

# Sprint 0060 — Ground-structure placement stream & per-round idol census

> **Subsystem slice:** [[G-enemy-and-spawn-system]] / [[D-scroll-and-tile-rendering]]
> (feeds [[M-secrets-and-warps]]). Decodes how idols/bases are *placed* by the
> map data so the warp catalogue in [[idol-warp-orbs]] can be completed with an
> exact per-round idol census.

## Motivation

Sprint 0059 fully mapped the idol→orb→warp **mechanism** and the per-round
**warp destinations** (from the 0xE720 idol tables), but the **exact idol census
per round is open**: which physical idols exist, where, their entity type
(70/71/81/82/87–89), their sub-type `(IX+0x18)`, and their `(IX+0x03)` index into
the 0xE720 table (which binds each idol to a specific `+0x1C/1D` warp pointer).
That data lives in the **ground-structure placement records** of the map script
(the greeble/placement commands not yet byte-exactly modelled).

## Goal

1. Byte-exactly decode the map-script placement commands that emit wide
   structures — the variable-length commands flagged in [[level_script_format]]
   (cmd 0/1/3/4/5/A/B; see `place_tile_group` 0x95ED and the greeble records).
2. For each structure record, extract entity **type**, **`+0x18`** sub-type,
   **`+0x03`** table index, and screen/scroll position.
3. Cross-reference each `+0x03` against the round's 0xE720 idol table to resolve
   the structure's `+0x1C/1D`, and classify: normal base / orb (kill-all) /
   **warp idol** (+ destination round).
4. Produce a **per-round idol census** table: count, positions, types, and which
   are warp idols with destinations — completing [[idol-warp-orbs]].
5. Confirm the **type-82 ⇔ warp-idol ("smiling face")** binding (0059 left it at
   `likely`): verify where `+0x18` is assigned per structure type and whether
   type 82 → the 0x52 orb branch.

## Inputs

- [[idol-warp-orbs]] (mechanism + partial destination catalogue), [[handler_type70_wide_structure]]
- [[level_script_format]] (0xA65C–0xB7A5), `place_tile_group` (0x95ED), the
  greeble/placement handlers (0x9505/0x9537/0x956C/0x95A0/0x96E5/0x9742)
- `scroll_state` 0xE720 (`idol_table_ptr`), `tools/decode_mapscript.py`
- Live: `tools/sprint0059_e720.py` (per-round E720 dumps)

## Verification plan

- Extend `decode_mapscript.py` to model the variable commands well enough to walk
  each script without desync (currently desyncs on greebles).
- Live-confirm a handful of decoded idols by breakpointing `handler_type70_wide_structure`
  activation (0x87B0) and reading `+0x03/+0x18/+0x1C/1D` for real spawns.
- Screenshot a confirmed **type-82** idol to verify the "smiling face" tile
  (`0x30 + (IX+0x1C)`) and correlate with its warp destination.

## Expected KB entries

- `kb/data/ground_structure_placement.md` — the placement-record format.
- `kb/data/idol_census.md` (or extend [[idol-warp-orbs]]) — per-round idol table.
- Upgrade the type-82 / smiling-face binding in [[idol-warp-orbs]] to `confirmed`.

## Summary

Rather than statically decode the fragile placement stream, the census was done
by **live capture**: a non-breaking breakpoint at 0x87C3 (wide-structure init,
after `+0x1C/1D` is loaded from the 0xE720 idol table, before `+0x03` is
overwritten) logs each idol's type/idx/dest + the live E701, while the round runs
at max speed with the ship invincible (`tools/sprint0060_census.py`).

**Findings:**

- **Warp idols are entity type 71** (not type 82). Every specific-round warp
  destination is carried by a type-71 structure; the destination = `+0x1C/1D` read
  from `(0xE720)[+0x03]`. Per-round census in [[idol-warp-orbs]]:
  R1→R2; **R2→R1/R2/R3**; **R5→R4/R6**; R7→R7(self)/R8; R0/3/4/6/8 have none.
  Backward warps **R2→R1** and **R5→R4** confirmed.
- **Round 7 loops** (player-reported, census-confirmed): its idol table offers
  only R7-self (0xB61A) and R8 (0xB7A5).
- **Type 82 = "digit" idol**, not the warp marker: its small `+0x1C` renders a
  digit via the 0xD2 draw and its orb resolves to round 0. The 0059 "type-82 /
  0xD2 = smiling face warp idol" claim was **wrong** and is corrected.
- **"Smiling face" confirmed**: `tools/sprint0060_shot.py` broke exactly as the
  round-2 → round-1 warp idol initialised and captured a grey face construction
  at its position (type 71, dest 0xA751). The face is in the **background tile
  graphics**, not an entity-handler foreground draw.

**Still open (data, not structure):** the byte-exact placement-stream record
format (which greeble record assigns each idol's `+0x03`/position). The live
census made this unnecessary for the warp catalogue, so it is left as a minor
data gap rather than a blocker.

## KB changes

- [[idol-warp-orbs]] — completed per-round census (type-71 warp idols), corrected
  visual section, round-7 loop; guide `sprint: 0060`.
- [[handler_type70_wide_structure]] — corrected type-82 (digit idol) note.
- [[entity_jump_table]] — types 71 (warp/face), 72 (orb), 82 (digit) updated.
- [[M-secrets-and-warps]] — smiling-face/type-71, round-7 loop, census done.
- Tools: `tools/sprint0060_census.py`, `tools/sprint0060_shot.py`.
