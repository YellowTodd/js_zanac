---
address: 0x4ACE
end: 0x4AE9
kind: routine
name: compare_save_hiscore
confidence: confirmed
inputs:
  E103-E105: current score (3-byte BCD, little-endian lo/mid/hi)
  E106-E108: top score (3-byte BCD, little-endian)
outputs:
  E106-E108: set to the score iff score >= top score
  carry: set (RET C) when score < top score (no copy)
clobbers: [AF, BC, DE, HL]
calls: []
called_by: [0x4672, 0x46DD]
tags: [score, hiscore, bcd, game-over, credits]
sprint: "0046"
---

# compare_save_hiscore

## Summary

Compares the current score against the top score and, if the score is greater or
equal, copies it over the top score. Called on two end-of-game paths:
`game_over_handler` (0x4672) and `credits_display` entry (0x46DD).

## Analysis (source 0x4ACE–0x4AE9)

```
4ACE  LD DE,0xE103      ; DE -> score   (lo,mid,hi)
4AD1  LD HL,0xE106      ; HL -> hiscore (lo,mid,hi)
4AD4  LD B,3
4AD6  OR A              ; clear carry
4AD7  LD A,(DE); SBC A,(HL); INC HL; INC DE; DJNZ 0x4AD7
                        ; 3-byte little-endian subtract score - hiscore with
                        ; borrow propagation; final carry = (score < hiscore)
4ADD  RET C             ; score < hiscore -> leave hiscore alone
4ADE  LD DE,0xE106; LD HL,0xE103; LD BC,3; LDIR   ; hiscore <- score
4AE9  RET
```

The low-to-high `SBC` chain is a correct 24-bit unsigned compare because each
`SBC` carries the borrow into the next byte; the carry after the third byte is
the borrow of the whole number.

## Live confirmation (sprint 0046)

Micro-exec with planted E103/E106:

| score (hi:mid:lo) | hiscore in | result | carry |
|---|---|---|---|
| 0x10:00:00 | 0x05:00:00 | hiscore ← score (10:00:00) | 0 |
| 0x01:00:00 | 0x09:00:00 | unchanged (09:00:00) | 1 |
| 0x07:13:42 | 0x07:13:42 | copied (>= path) | 0 |

Also confirmed end-to-end: in the credits screenshot (`tools/sprint0046_verify.py`)
the HUD shows **TOP == SCORE == 2211200**, i.e. the score was promoted to the top
score on `credits_display` entry. `tools/sprint0046_verify.py`.

## See also

- `credits_display.md` (0x46DD caller), `game_over_handler.md` (0x4672 caller).
- `score_display_update.md` / `render_score_bcd.md` — the BCD score it reads.
