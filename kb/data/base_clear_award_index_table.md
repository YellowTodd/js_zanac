---
address: 0x9302
end: 0x9314
kind: data
name: base_clear_award_index_table
confidence: confirmed
sprint: "0065"
tags: [score, base, data-table, n-hud, g-enemy]
---

# base_clear_award_index_table (0x9302–0x9314, 19 B)

## Summary

Score-award index table for **base / progress-milestone bonuses**, a sibling of
[[structure_award_index_table]] that feeds the same score machinery. 19 bytes:

```
0A 0C 0D 10 0E 0F 0E 0F 0F 10 11 11 00 00 00 11 12 13 14
```

Indices `0x00–0x12` (0–18); values are indices into [[score_award_table]]
(0x4AEA). The `00 00 00` at slots 12–14 = "no award" for those milestones.

## Reader (0x91A9, in the base HUD/award handler)

```
0x9198  A = (IX+0x57) & 0x1F          ; base-encounter / milestone counter
0x91A9  HL = 0x9302 + A ; A = (HL)     ; award index
0x91B5  (unless (IX+0x57) bit6) A*3 -> 0x4AEC -> render_score_bcd (display)
0x91C1  CALL add_score (0x4A74)        ; add score_award_table[A] BCD to E103
```

`(IX+0x57)&0x1F` is the base-progress counter (same field the base-attack path
reads); as more of a base is cleared the counter climbs and the awarded index
rises (0x0A→0x14), i.e. escalating bonuses. The award index then drives both the
on-screen BCD display (`render_score_bcd`) and the actual score add
([[add_score]] → [[score_award_table]]) — identical to how `data_4b2a` works for
wide-structure sub-types.

## When the clear routine runs

The award path (0x9165 → 0x9198 → 0x91A9) executes when the base's remaining
segment count **`0xE152` reaches 0** (checked at 0x908A, `(IX+0x52)==0` with
`IX=0xE100`). Each base segment destroyed decrements 0xE152 (`DEC (HL)` @0x8BB4
when a segment's HP `+0x19` hits 0). So the award fires exactly once, when the
last segment of the base dies.

## Confidence

`confirmed`. **Live-confirmed (sprint 0065, `tools/verify_base_clear.py`):** in a
real round-1 base fight (invincible, boosted ship; segments shot down until
`E152` reached 0), the clear routine ran and the reader at 0x91AD loaded
index **A = 0x0A** with counter `(E157)&0x1F = 0`, **matching ROM `0x9302[0] =
0x0A` exactly** — proving the reader reads this table and feeds
`add_score`/`score_award_table`. (The final segment was nudged to 0 to guarantee
completion; the encounter, attackers and prior segment kills were all genuine.)

## See also

[[structure_award_index_table]], [[score_award_table]], [[add_score]],
[[base_attack_patterns]].
