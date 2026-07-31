---
address: 0x4A6A
end: 0x4A73
kind: routine
name: add_score_for_subtype
confidence: confirmed
sprint: "0063"
inputs:
  IX: entity slot (uses (IX+0x18) destruction sub-type)
outputs:
  E103-E105: score increased via add_score
calls: []
called_by: [0x8833]
tags: [score, hud, wide-structure, code-in-db]
---

# add_score_for_subtype  (LAB_ram_4a6a)

## Summary

Score-award prologue for **wide ground structures**: looks up the award index
for the entity's destruction sub-type and **falls through into
[[add_score]]** (0x4A74). Was hidden as a 10-byte DB block until sprint 0063
(disassembled via `redisasm.py`, ROM byte-identical ✓) — which is why
`data_4b2a` appeared to have "no reader".

```
LD  E, (IX+0x18)    ; destruction sub-type (0x01-0x59)
LD  D, 0x00
LD  HL, 0x4b29      ; = structure_award_index_table base - 1
ADD HL, DE          ; 0x4B29 + sub-type -> 0x4B2A-0x4B82
LD  A, (HL)         ; A = award index
                    ; falls through to add_score (A -> score_award_table[A])
```

## Analysis

- Called from the `0x8833` orb path in [[handler_type70_wide_structure]]
  (`CALL 0xbfc8` (encounter) + `0x4a6a` + spawn children) — already listed in
  that entry's `calls:` before the code was disassembled.
- The base is **0x4B29** = the last byte of [[score_award_table]] (end:
  0x4B29), so sub-types 0x01–0x59 index the 89-byte table at
  **0x4B2A–0x4B82** ([[structure_award_index_table]], the former `data_4b2a`)
  — the extents match exactly.
- Sub-type 0 would read 0x4B29 itself (inside score_award_table's last award);
  wide structures use sub-types ≥ 0x41 in practice (see the destruction map in
  [[idol-warp-orbs]]).

## See also

[[add_score]], [[score_award_table]], [[structure_award_index_table]],
[[handler_type70_wide_structure]].
