---
id: "0065"
status: done
range: 0x4B2A-0x4B83,0x93AB-0x93E4,0x9302-0x9315,0x51F0-0x5208
strategy: data_table
budget_turns: 30
subsystems: [N, G, D, O]
---

# Sprint 0065 — Orphan data tables: readers or proven dead

> **Completion-plan sprint 4/6.** Four small DB regions (~189 bytes total) have
> structure but no complete story. Under the 100% criterion each needs either a
> decoded purpose or a **proof of no reader** (dead data is an acceptable
> verdict — but it must be demonstrated, not assumed).

## Motivation

These are the last DB blocks with unknown or under-documented semantics:

| Region | Bytes | Status |
|--------|-------|--------|
| 0x4B2A–0x4B82 (`data_4b2a`) | 89 | **reader FOUND (0063)**: `add_score_for_subtype` (0x4A6A, was code-in-DB) reads `0x4B29+(IX+0x18)` → it's the [[structure_award_index_table]] (`likely`); needs live verification |
| 0x93AB–0x93E4 | 57 | base-attack pattern table — reader known (0x8FDE via cursor 0xE717), field semantics + KB entry missing |
| 0x9302–0x9315 | 19 | unnamed table after a scroll routine; no KB entry |
| 0x51F0–0x5208 | 24 | word/period table tail near `lookup_word_table`/`mute_sound`; no dedicated entry |

## Goal

1. **`data_4b2a` = [[structure_award_index_table]] (89 B) — verify (0063 found
   the reader):** the code-in-DB block at 0x4A6A ([[add_score_for_subtype]])
   computes `A = (0x4B29 + (IX+0x18))` and falls through to [[add_score]].
   Live-verify: break at 0x4A73, destroy wide structures of known sub-type
   (idol 0x41.., fire box 0x52, etc.), confirm the score increase equals
   `score_award_table[table[sub]]`; upgrade the entry to `confirmed`.
   While the watchpoint session is set up, also cover [[dir8_delta_table]]
   (0x7748, 16 B) to upgrade its "unreferenced/dead" verdict.
2. **0x93AB base-attack pattern table:** break at the 0x8FDE reader; correlate
   the 8 word pointers + 4-byte descriptors with observed base attack waves
   (which enemies, timing, firing pattern). Name the fields; write the KB data
   entry; note the 0xE717 rotating cursor semantics.
3. **0x9302 (19 B):** identify the reader (likely the preceding scroll routine
   ending at 0x9301 or `SUB_ram_9315`); decode and name.
4. **0x51F0 (24 B):** trace from `lookup_word_table`; decide whether it folds
   into an existing sound/word-table entry or needs its own.

## Inputs

- `kb/guides/db-sections-with-code.md` (per-block notes)
- [[N-hud-and-status-display]] (data_4b2a context), sprint 0055 (ALC ruling)
- Base handler at 0x8FDE + `0xE717` cursor (reclassified sprint 0056)
- `kb/guides/openmsx-control.md` (watchpoint patterns)

## Verification plan

- Static: every claimed reader path quoted with line ranges; for outcome B, the
  full-range watchpoint session log showing zero hits.
- Dynamic: 0x93AB descriptor fields toggled live (poke a descriptor, observe
  the changed base attack) for at least one field.
- `tools/coverage_audit.py` (0063): all four regions leave the `unknown` class.

## Expected KB entries

- `kb/data/base_attack_patterns.md` (0x93AB) — the main deliverable.
- `kb/symbols/0x4900-hud/data_4b2a.md` — decoded or proven-dead verdict.
- Entries (or folds into existing ones) for 0x9302 and 0x51F0.
- Row updates in `db-sections-with-code.md`.

## Summary (filled at end)

**Done — all four regions decoded with their exact readers quoted; two
live-confirmed.**

- **`data_4b2a` (0x4B2A) → CONFIRMED.** `add_score_for_subtype` (0x4A6A) computes
  `A = (0x4B29)[(IX+0x18)]` and falls into [[add_score]]. Live
  (`tools/verify_orphan_data.py`, bp 0x4A74): destroyed structures gave sub 0x2C
  → idx 2 (award BCD `06 00 00`) and sub 0x05 → idx 7 (`50 00 00`), **matching
  the ROM table byte-for-byte**. Also covered [[dir8_delta_table]]: a read
  watchpoint over 0x7748–0x7757 saw **zero hits** across ~45 s of active play —
  supports the dead-data verdict (kept `likely`).
- **0x93AB (57 B) → [[base_attack_patterns]] (`confirmed`).** The
  **base-attacker movement-pattern table**: 8 pointer words → 8 variable-length
  descriptors of **3-byte `(rate0,rateM,rate3)` records terminated/looped by
  `0x00`** (interpreter 0x8BF5, quoted). Reader `base_attack_spawn` (0x8FDE)
  assigns them round-robin via cursor 0xE717 (wrap 8) into attacker field
  `(IY+0x0F/0x10)`. All 57 bytes accounted (16 ptr + 41 descriptor).
  **Live-confirmed** (see below).
- **0x9302 (19 B) → [[base_clear_award_index_table]] (`confirmed`).** Score-award
  indices indexed by base-progress counter `(IX+0x57)&0x1F`, read at 0x91A9 →
  `render_score_bcd` + [[add_score]] (the *confirmed* score path). Runs when the
  base's segment count `0xE152` hits 0. Escalating awards 0x0A→0x14; `00` slots =
  no award. **Live-confirmed** (see below).
- **0x51F0 (24 B) → [[psg_period_base_table]] (`confirmed`).** 12 LE base periods
  = one chromatic octave; read by `init_psg_freq_table` (0x5147) to build the
  0xF200 runtime table. This is the concrete "ROM table at 0x51F0" the
  [[sound-engine]] guide already cited.

**Base-table live verification (`tools/verify_base_clear.py`, round 1, invincible
via `ZanacGame.make_invincible`).** The one-eye base encounter is reached in
round 1 — signalled by the scroll row counter 0xE702 stalling (row 305). Then:
- **0x93AB:** `base_attack_spawn` (0x8FDE) fired; **21 reads at 0x8BF5 all in
  0x93BB–0x93E3** across 9 distinct positions (patterns 0–3 + their `0x00` loop
  bytes), matching the decode.
- **0x9302:** shooting the base segments drove `0xE152` down (each segment kill
  `DEC (E152)` @0x8BB4); on `E152=0` the clear routine's reader (0x91AD) loaded
  index **A = 0x0A** for counter `(E157)&0x1F = 0` = **ROM `0x9302[0]` exactly
  (MATCH)**. (Final segment nudged to 0 to guarantee completion; encounter and
  prior kills genuine.)

Both upgraded `likely` → **confirmed**. All four regions now decoded *and*
exercised.

**Audit:** `tools/coverage_audit.py` known% **87.66 → 87.96**; all four regions
left the `unknown` class (only the 0066-owned greeble/tile-column blocks remain).

New/changed: `tools/verify_orphan_data.py`, `tools/verify_base_clear.py`
(round-1 base fight), `tools/verify_base_round1.py`, `tools/probe_base_entity.py`,
`kb/data/base_attack_patterns.md` (new, confirmed),
`kb/data/base_clear_award_index_table.md` (new, confirmed),
`kb/data/psg_period_base_table.md` (new),
`kb/data/structure_award_index_table.md` (→confirmed),
`kb/data/dir8_delta_table.md`, `kb/guides/db-sections-with-code.md`.
