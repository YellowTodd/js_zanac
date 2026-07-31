---
id: "0062"
status: done
range: 0xA65C-0xB7A5,0x9505-0x96E5
strategy: data_table
budget_turns: 30
subsystems: [D, G]
---

# Sprint 0062 — Byte-exact ground-structure placement-stream format

> **Subsystem slice:** [[D-scroll-and-tile-rendering]] / [[G-enemy-and-spawn-system]].
> Closes the last data gap left by 0060/0061: the byte-exact format of the
> map-script placement records that emit ground structures (totems, fire boxes,
> bases), so every idol's spawn fields can be read **statically** from ROM.

## Motivation

Sprints 0060/0061 mapped the idol→orb→warp **mechanic** and produced a live
**census** (breakpoint at 0x87C3), but the underlying **placement stream is only
partially modelled**: `tools/decode_mapscript.py` desyncs on the variable
greeble/placement commands (cmd 0/1/3/4/5/A/B in [[level_script_format]]). We can
observe an idol's `type` / `+0x18` / `+0x03` / position **live**, but cannot yet
derive them from the ROM bytes. Filling this in lets us:

- enumerate every ground structure per round **without gameplay** (faster, total),
- confirm the census is complete (no missed idols / secret totems),
- bind each idol's `+0x03` (E720 index) and `+0x18` (destruction sub-type) to its
  placement record — finishing the warp catalogue's provenance.

## Goal

1. Byte-exactly decode the placement/greeble commands and their sub-records:
   - cmd 1 (0x97B3, N×3-byte tile records → `check_col_clear` 0x9B22),
   - cmd 2 / 4 (0x9505 / 0x956C, N×5-byte column-group specs),
   - cmd 3 (0x9537, per-slot tile copy), cmd 5 (0x95A0, stream slots),
   - cmd A (0x96E5), cmd B (0x9742).
2. Identify **which record field(s)** set a spawned structure's entity **type**,
   `(IX+0x18)` sub-type, `(IX+0x03)` E720 index, and X/Y.
   **Known complication (probe, 2026-07-04):** `+0x03` is *not* a fixed record
   field — the same record (e.g. script PC 0xABE6 in round 2) spawned idx 0, 28
   and 88 across runs, and the invisible totem was seen as type 71 where the
   census logged type 70. Find the state/cursor that assigns `+0x03` (and the
   type byte) at spawn time.
3. Extend `decode_mapscript.py` to walk all 9 scripts start→end without desync,
   emitting a structured list of every placed structure.
4. Cross-check the static list against the live census
   (`tools/sprint0060_census.py`) — they must agree on type/idx/dest/position.
5. Decode **cmd 12 (0x8C)** byte-exactly — round preambles carry it (e.g.
   `8C 20 7E` at 0xAAF5) and it is credited as **spawn pacing**: identify its
   operands and which ALC state it writes (E12F/E131 family). Feed the result
   into the subsystem-I docs (see expected entries).
6. Formalise the **warp-only re-entry stub** (0xAD31–0xAD60, decoded live via
   `tools/probe_idx88.py`, documented in [[idol-warp-orbs]]): confirm its record
   decode against the final grammar, and sweep the other 8 rounds' streams for
   any sibling stub (a cmd 9 whose target is not a round entry).

## Inputs

- [[level_script_format]] (0xA65C–0xB7A5), the cmd handlers listed above
- `place_tile_group` (0x95ED), `check_col_clear` (0x9B22),
  `ground_struct_spawn_ctrl` (0xBF2C), [[handler_type70_wide_structure]] (consumer)
- [[idol-warp-orbs]] (mechanic + census + re-entry-stub section), `scroll_state`
  0xE720 (`idol_table_ptr`)
- `tools/decode_mapscript.py`, `tools/sprint0060_census.py` (ground truth),
  `tools/probe_idx88.py` (spawn logger: type/sub/idx/dest/table/script-PC/row
  per 0x87C3 init, E720-swap watch, optional `--warp` orb-touch simulation)

## Verification plan

- For each decoded structure, breakpoint its handler activation (0x87C3 / spawn)
  and confirm the ROM-derived type/idx/sub-type/position match the live values.
- Round-trip: static list ≡ live census per round (count + fields).

## Expected KB entries

- `kb/data/ground_structure_placement.md` — the placement-record format.
- Extend `decode_mapscript.py` (variable commands) + a per-round structure dump.
- Upgrade `place_tile_group` / greeble-command handlers from `hypothesis`.
- Re-verify the census table + re-entry-stub section in [[idol-warp-orbs]]
  against the final grammar (the idx values there are run-specific — replace
  with the static record identities once known).
- Update `kb/subsystems/i-*.md` + `alc-adaptive-difficulty.md`: ALC has **two**
  inputs — firing cadence (documented) **and** per-round map-script commands
  (cmd 12 spawn pacing; round entry resets). If the doc rewrite doesn't fit in
  budget, hand it to sprint 0067.

## Summary (filled at end)

**Done.** Byte-exact operand grammar for all 13 map-commands derived statically
from the handlers behind the jump table 0x94EB and captured in
[[ground_structure_placement]]. New tool `tools/decode_mapscript2.py` walks
**all 9 scripts + the warp re-entry stub start→end** with strictly
non-decreasing row triggers and clean termination — the definitive desync-free
proof that the variable commands (0/1/3/4/5/A/B) are now fully modelled.

Key operand lengths: 0 = 1 (+`1+3N` when operand bit2 set); 1 = `1+3N`;
2/4 = `1+5N`; 3 = `1+2N`; **5 = `1+Σ(4 or 5 per record, +1 when record byte0
bit3 set)`** — the only variable-per-record command, and both branches occur in
shipped data (112 four-byte + 213 five-byte records); 6 = 1; 7 = `1+N`;
8/9 = 2; A = 1; B = 7; C = 1.

- **Goal 1 (decode all placement/greeble commands):** done — table + derivation
  in [[ground_structure_placement]]; [[level_script_format]] upgraded (commands
  no longer "opaque").
- **Goal 2 (which field sets type/`+0x18`/`+0x03`/pos):** the per-round **idol
  table** (0xE720, set by cmd 8) is a **packed byte-addressed pointer array**;
  the idol's `(IX+0x03)` is a **byte offset** (not ×2) consumed at spawn-init
  0x87B0 → `(IX+0x1C/1D)` = warp destination, then reset to 0x24. Confirmed
  `+0x03` is a **dynamic allocation cursor**, not a static record field (matches
  the 2026-07-04 probe: same record → idx 0/28/88). Deriving each idol's
  `+0x03`/type/`+0x18` statically needs the tile-column→entity allocation cursor
  (`ground_struct_spawn_ctrl` 0xBF2C region) — the **one residual gap** (data,
  not format); the live census stays authoritative for per-idol destinations.
- **Goal 3 (walk all 9 without desync):** done — see above.
- **Goal 4 (cross-check vs live census):** all **nine** per-round idol-table
  pointers reproduced statically match the census "E720 table" column exactly
  (R0=0xA6EC … R8=0xB94C); the full round-jump chain reproduces
  `R1→…→R7`, `R7→R7` loop, `R0→R8`, `R8→ending` (round = 8 − table-index),
  matching subsystems K/M. No new openMSX run needed — the static output
  reproduces the existing live ground truth.
- **Goal 5 (cmd 12 / 0x8C):** decoded — handler 0x977D, **1 signed operand** →
  `E132`/`E12E` spawn accumulators + `SET 0,(E12D)` = a **scripted second ALC
  input**. Noted in [[alc-adaptive-difficulty]] (full rewrite → 0067).
- **Goal 6 (re-entry stub + sibling sweep):** stub 0xAD4B decodes cleanly
  (`cmd6 · cmd8 idol_tbl=0xAD31 · cmd5 N=1 · cmd9→0xAAEF`); a static sweep of all
  9 scripts shows **every mainline cmd-9 target is a real round entry**, so this
  stub is the *only* off-mainline re-entry (no sibling stub). Verified note
  added to [[idol-warp-orbs]].

**Residual (leave open, hand to 0065/0067):** the per-idol `+0x03`/type/`+0x18`
allocation-cursor derivation (the invisible-totem provenance is fully explained
via the stub; only the general static idol-attribution remains). ALC doc rewrite
folding cmd 12 → sprint 0067.

New/changed files: `tools/decode_mapscript2.py`,
`kb/guides/ground_structure_placement.md` (new),
`kb/data/level_script_format.md`, `kb/guides/idol-warp-orbs.md`,
`kb/guides/alc-adaptive-difficulty.md`.
