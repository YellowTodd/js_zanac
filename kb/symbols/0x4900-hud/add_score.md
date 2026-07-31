---
address: 0x4A74
end: 0x4A99
kind: routine
name: add_score
confidence: confirmed
inputs:
  A: award index into score_award_table (0x4AEA)
outputs:
  E103-E105: score increased (BCD) by score_award_table[A], capped at 999999
clobbers: [AF, BC, DE, HL]
calls:   [0x4A9A, 0x49F0]
called_by: [0x91C1]
sprint: "0047"
tags: [score, bcd, hud]
---

# add_score

## Summary
Add a points award to the player score. The award index `A` selects a 3-byte BCD
value from `score_award_table` (0x4AEA); it is BCD-added (`DAA`) to the score at
E103–E105 and the score is re-rendered. On overflow the score is capped at
0x999999.

## Analysis
Source 0x4A74:
```
4A74  LD C,A; ADD A,A; ADD A,C; LD C,A; LD B,0   ; BC = index*3
4A7A  LD HL,score_award_table; ADD HL,BC          ; HL → table[index]
4A7E  LD DE,0xE103                                ; score (lo,mid,hi)
      ; 3-byte BCD add with DAA, carry-propagating
4A91  CALL C,0x4A9A    ; on overflow → cap score to 0x99,0x99,0x99
4A94  CALL 0x49F0      ; re-render score + new-top-score milestone check
4A97  JP 0x4A26
```
`0x49F0` re-renders the score (via `render_score_row2`) and, if it now beats the
top score, arms the `score_display_update` flash (E114 bit 6/7).

A second site (0x91B9) indexes the **same** table at +2 (`0x4AEC`, the hi byte of
each entry) and calls `render_score_bcd` directly to display an award value.

## Live confirmation (sprint 0047)
Micro-exec (trap at the 0x4A26 exit) from score 0: index 1 → +`010000`, index 9 →
+`000100`, index 13 → +`001000`, each equal to `score_award_table[index]` read
from ROM. `tools/sprint0047_verify.py`.

## See also
- `score_award_table.md` (0x4AEA) — the BCD award values.
- `score_display_update.md` — the new-top-score flash armed via 0x49F0.
