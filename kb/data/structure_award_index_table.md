---
address: 0x4B2A
end: 0x4B82
kind: data
name: structure_award_index_table
confidence: confirmed
sprint: "0065"
tags: [score, wide-structure, data-table]
---

# structure_award_index_table  (asm label `data_4b2a`)

## Summary

89-byte table of **score-award indices** for wide-ground-structure destruction
sub-types: `award_index = (0x4B29)[(IX+0x18)]` for sub-types **0x01–0x59**.
Read by [[add_score_for_subtype]] (0x4A6A), which falls through into
[[add_score]] — so each byte here selects a 3-byte BCD award from
[[score_award_table]] (0x4AEA).

Values are all small (0x00–0x13), consistent with award indices. Examples:
sub-type 0x41 → `0x0A`, 0x52 (fire box) → `0x06`, 0x59 → `0x08`.

## Provenance

- Listed for years as "`data_4b2a` — no reader found" (ALC ruled out, sprint
  0055) because its only reader was itself **inside an undisassembled DB
  block** at 0x4A6A. Sprint 0063's coverage audit surfaced that block; the
  disassembled code indexes exactly 0x4B29 + sub-type, and the table's extent
  (0x4B2A–0x4B82 = sub-types 0x01–0x59) matches the destruction-sub-type range
  in [[idol-warp-orbs]] byte-for-byte.
- **Live-confirmed (sprint 0065, `tools/verify_orphan_data.py`):** breakpoint at
  0x4A74 during play logged, for each destroyed structure, `(IX+0x18)` sub-type
  → the award index `A` actually loaded. Captured sub 0x2C → **idx 2**
  (award BCD `06 00 00`) and sub 0x05 → **idx 7** (award BCD `50 00 00`), both
  **matching the ROM table** `(0x4B29)[sub]` byte-for-byte. Confirmed the reader
  reads this table and feeds [[score_award_table]] via [[add_score]]. Upgraded
  `likely` → **confirmed**.
- Asm label is still `data_4b2a`; rename in sprint 0068.

## See also

[[add_score_for_subtype]], [[score_award_table]], [[add_score]],
[[handler_type70_wide_structure]].
