---
name: coverage-audit
description: "How tools/coverage_audit.py measures the 100% criterion: per-byte classification of ROM 0x4000-0xBFFF (code / data-kb / data-inline / padding / unknown), current numbers, and the ownership of each remaining unknown range."
kind: guide
confidence: confirmed
sprint: "0063"
tags: [tooling, coverage, completion-plan]
---

# Byte-coverage audit

`tools/coverage_audit.py` (sprint 0063) makes the completion criterion —
*"the meaning of every disassembled code and data byte is understood"* —
measurable. It classifies **every ROM byte 0x4000–0xBFFF** and lists the exact
ranges still unaccounted for.

```
.venv/bin/python tools/coverage_audit.py               # ranges ≥4 B
.venv/bin/python tools/coverage_audit.py --all-ranges  # every range
```

## Classes

| Class | Meaning |
|-------|---------|
| `code` | instruction line in `zanac.asm` (address comment, not DB/DW) |
| `data-kb` | DB/DW byte inside a KB entry's extent — `address:`..`end:` (inclusive) from `kb/symbols/**` + `kb/data/*` frontmatter; entries without `end:` cover the contiguous DB run at their address |
| `data-inline` | DB/DW run immediately after a `CALL` into the inline family: string print 0x5C10/0x5C1F/0x5C25/0x5C28 or DW-dispatch 0x5C2E — or a line whose comment says `inline` |
| `padding` | DB line of all-0xFF bytes (≤16 B): inter-routine filler (0x9403, 2 B) and the ROM tail (0xBFFB–0xBFFF, 5 B) |
| `unknown` | everything else — the work queue |

Sanity checks: total = 32768; DB spans must meet the next line's address;
KB addresses that start no asm line are flagged (legit mid-DB-row data starts
like `logo_tile_rows` 0x4827 — or real anomalies, see below).

## Current numbers (2026-07-05, post-0066 — **100%**)

```
code          15220   46.45%
data-kb       17445   53.24%
data-inline      96    0.29%
padding           7    0.02%
unknown           0    0.00%   ->  KNOWN = 100.00%
```

**Completion gate met.** Every ROM byte 0x4000–0xBFFF is now classified. The
final unknown ranges were retired by sprints 0064 (sound tracks), 0065 (the four
orphan tables) and 0066 (graphics accounting + the tile-column/greeble regions).

### Progression

| After sprint | KNOWN % | What landed |
|--------------|---------|-------------|
| 0063 (baseline) | 81.52 | audit tool + 9 unjoined tables |
| 0064 | 87.66 | sound-track scores (2011 B) |
| 0065 | 87.96 | 4 orphan tables (0x51F0/0x9302/0x93AB/0x4B2A) |
| 0066 | **100.00** | tile-column/greeble regions 1+2 + strip (3945 B) |

### Retired unknown ranges (all owned, now KB-joined)

| Range | Bytes | Retired by |
|-------|-------|-----------|
| 0x51F0–0x5207 | 24 | 0065 → [[psg_period_base_table]] |
| 0x5236–0x5A10 | 2011 | 0064 → [[sound_track_scores]] |
| 0x9302–0x9314 | 19 | 0065 → [[base_clear_award_index_table]] |
| 0x93AB–0x93E3 | 57 | 0065 → [[base_attack_patterns]] |
| 0x9B64–0xA443 | 2272 | 0066 → [[tile_column_data_region1]] |
| 0xA654–0xA65B | 8 | 0066 → [[tile_strip_a654]] |
| 0xB7A6–0xBE26 | 1665 | 0066 → [[tile_column_data_region2]] |

## Findings from the first run (0063)

- **0x4A6A was code, not data**: a 10-byte DB block hiding
  `add_score_for_subtype` — the reader of `data_4b2a`, which is therefore the
  [[structure_award_index_table]] (score-award indices by destruction
  sub-type). Patched + ROM-verified.
- **Overlapping decode at 0x8E13/0x8E14**: `DJNZ 0x8df2`'s displacement byte
  0xDD doubles as the DD-prefix of `handler_type80_base_damage`'s first
  instruction (entered via the jump table). The asm shows the DJNZ view;
  0x8E15/0x8E17 are phantom lines. Details in `db-sections-with-code.md`.
- Nine documented-but-unjoined tables got KB extents (credits table, dir
  tables, PAUSE text, scroll-speed ramp, glyph/cmd11 tables, dir8 deltas).

## Maintenance

- New KB data entries should carry `end:` so the join is exact.
- Re-run after every completion-plan sprint; update the numbers here.
- Exit gate for the plan: **0 unknown bytes** (sprint 0066 target).
