---
id: "0063"
status: done
range: 0x4000-0xBFFF
strategy: tooling
budget_turns: 20
subsystems: [all]
---

# Sprint 0063 — Byte-coverage audit tool (the 100% criterion)

> **Completion-plan sprint 1/6.** Turns "100% mapped" from a judgment call into
> a measurable gate: every ROM byte 0x4000–0xBFFF classified, unknowns listed.
> All later completion sprints (0062, 0064–0068) use this tool as their exit
> check.

## Motivation

All 15 subsystems are marked done, but "done" means *structural* understanding.
The completion criterion is stricter: **the meaning of every disassembled code
and data byte is understood.** Today that can't be verified — coverage tracking
lives in hand-maintained tables (CLAUDE.md, `db-sections-with-code.md`) that
have already drifted (e.g. 0x8983/0x8A5A listed both as patched and as
unmapped), and DB runs ≤16 bytes have never been systematically audited.

## Goal

Write `tools/coverage_audit.py`:

1. Parse `source/zanac.asm` and map every ROM byte 0x4000–0xBFFF to a class:
   - `code` — an instruction line (has an address comment, not a DB);
   - `data-kb` — inside a DB run covered by a KB entry (join on the KB
     frontmatter `address` field + a size/extent, from the entry's `length`/
     `size` field where present, else the enclosing labeled DB run);
   - `data-inline` — inline string/data consumed by the string-print family
     (0x5C10/1F/25/28 call sites) or another documented inline idiom;
   - `unknown` — everything else.
2. Emit: total % per class, and the exact address ranges of every `unknown`
   byte (with the nearest label before/after for orientation).
3. Sanity checks: byte count totals 32768; every KB symbol/data `address`
   actually exists in the asm; flag KB entries whose address lands mid-run.
4. Reconcile the output against `db-sections-with-code.md` and the CLAUDE.md
   region table; fix the stale rows there.

## Inputs

- `source/zanac.asm` (parsed mechanically — do not read in bulk)
- `kb/symbols/**/*.md`, `kb/data/*.md` frontmatter (schema:
  `kb/guides/conventions.md`)
- `kb/guides/db-sections-with-code.md`, `kb/guides/level-data-block-map.md`
- The DB-block census from the 2026-07-04 planning session: 24 blocks >16 B,
  ~17.3 KB total, most already KB-named

## Verification plan

- Static: the tool's `unknown` list must contain (at least) the known open
  regions — 0x4B2A–0x4B82, 0x93AB–0x93E4, 0x9302–0x9315, 0x51F0–0x5208 — and
  nothing that a KB entry demonstrably covers (spot-check 10 named blocks).
- Idempotence: running twice gives identical output; committing no asm changes.
- `zanackb validate` still passes after any KB frontmatter fixes (e.g. adding
  missing size fields discovered by the join).

## Expected KB entries

- `tools/coverage_audit.py` + a `kb/guides/coverage-audit.md` note (how to run,
  how classes are decided, current numbers).
- Corrected rows in `db-sections-with-code.md`; refreshed CLAUDE.md region
  table.
- Possibly small frontmatter additions (explicit `size`) to existing data
  entries so the join is exact.

## Summary (filled at end)

**Done 2026-07-05.** `tools/coverage_audit.py` classifies all 32768 ROM bytes
(code / data-kb / data-inline / padding / unknown) by parsing `zanac.asm`
(DB/DW/string literals, inline-print/dispatch idiom incl. 0x5C2E, all-0xFF
padding) and joining KB frontmatter extents (`address:`..`end:`; no-`end`
entries cover their contiguous DB run). Result: **81.52% known**, 7 unknown
ranges (6056 B), every one owned by a later sprint (0062/0064/0065/0066) —
table + numbers in `kb/guides/coverage-audit.md`.

Findings beyond the tool:

- **0x4A6A was code hiding `data_4b2a`'s reader**: patched via `redisasm`
  (ROM byte-identical ✓) → [[add_score_for_subtype]] reads
  `0x4B29+(IX+0x18)` and falls into `add_score`, so `data_4b2a` =
  [[structure_award_index_table]] (score-award indices per destruction
  sub-type, extent 0x01–0x59 matches byte-for-byte). Sprint 0065's reader-hunt
  goal converted to a live-verify.
- **Overlapping decode at 0x8E13/0x8E14** (DJNZ displacement 0xDD doubles as
  the DD-prefix of `handler_type80_base_damage`'s entry) — documented in
  `db-sections-with-code.md`; 0x8E15/0x8E17 are phantom lines.
- 9 new KB entries for documented-but-unjoined tables: `credits_control_table`,
  `dir_angle_thresholds`, `dir_remap_table`, `pause_text`,
  `scroll_speed_ramp_table`, `glyph_col_data`, `cmd11_index_table`,
  `dir8_delta_table`, `structure_award_index_table` (+ routine entry
  `add_score_for_subtype`).
- Stale rows fixed in `db-sections-with-code.md` (0x8983/0x8A5A/0x4CF7/0x4AEA/
  0x43C0-dup/0x945C) and CLAUDE.md (0x4B2A row, coverage note).

Still uncertain / next: the 0xA654–0xA65B 8-byte gap (looks like one fixed
8-tile column — assign in 0062/0066); `likely` entries created here get their
cheap upgrades in 0065/0067. **Next sprint: 0062** (placement-stream format).
