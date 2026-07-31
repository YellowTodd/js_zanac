---
address: 0x8302
end: 0x839e
kind: routine
name: handler_type61_large_descender
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71da, 0x4898, 0x71f6, 0x44ba, 0xbfb3, 0x4a6a]
called_by: [0x445f]
tags: [entity, enemy, descender, base]
sprint: "0051"
---

# handler_type61_large_descender

**Type 61** — large descender that drops on the side opposite the player, halts
at Y=0x60, then dives. Tied into the base-encounter system: at certain states it
calls the encounter helpers (0xbfb3 / 0x4a6a) and remaps its own type to
0x23 / 0x3e / 0x53. Pattern 0xf8 (pat 62).

```
8302  BIT 7,(IX+0x00) / JR NZ,0x834a
8308  LD A,(0xe302) / CP 0x78 / LD D,0x40 / JR NC / LD D,0xb0  ; spawn opposite player X
8313  CALL 0x71da / LD (HL),0xfc          ; col-marker complement 0xFC
8318  LD (IX+0x02),D / LD (IX+0x09),0x02 / LD (IX+0x0c),0x01 / LD (IX+0x03),0xf8  ; X, vy=2, Y-motion
8327  LD HL,0xe149 / LD A,(HL) / INC (HL) / AND 0x07 / LD (IX+0x1d),A  ; cycle index 0..7
8331  LD HL,0x8eaf / ADD A → colour       ; colour = large_descender_color_table[idx]
8339  LD (IX+0x1e),0x20 / SET 7,(IX+0x00)
; active (0x834a):
834a  LD A,(IX+0x01) / CP 0x60 / JR NZ,0x8362 ; reached Y=0x60?
8351  LD (IX+0x0c),0 / DEC (IX+0x1e) / … / LD (IX+0x09),0xfc  ; pause, then vy=-4 (dive up)
8362  CALL 0x4898 / CALL 0x71f6 / CALL 0x44ba
836b  CP 0x23 / RET NZ                      ; state-specific tails:
8371  CALL 0xbfb3 …                          ; type 0x23 → base-encounter handoff →0x3e
838a  … (+0xe148 ≥5) CALL 0x4a6a / type→0x53 ; alt branch
```

## The kill lottery (0x836B, byte-exact 2026-07-30)

The 0x836B tail only runs when the preceding `CALL 0x44ba` has just remapped
this slot to **0x23** (the 61→35 death transition) — i.e. on the frame the
walker dies, whether shot or rammed. It then always calls `dec_encounter_a`
(0xBFB3) and rolls a two-stage lottery **overwriting the explosion type**:

1. `(0xE140) & 0x3F == (0xE103) & 0x3F` — shots-fired counter vs. the score's
   low BCD byte — → `add_score_for_subtype` + type **0x3E (62)**, the invisible
   riser (no other fields touched; type 62's own init takes over).
2. else if `(0xE148) >= 5` (banked bonus counter) → `add_score_for_subtype` +
   type **0x53 (83)** black-shadow fire upgrade with `+0x1C = +0x1D` — the
   **weapon number is the walker's own colour index** (0xE149 rotation), so the
   prize is visibly colour-coded.
3. else the slot stays 0x23 → standard explosion, no score.

## Related

[[large_descender_color_table]] (0x8eaf), [[spawn_col_marker]],
[[base_encounter_ctrl]], [[entity_jump_table]] (61).
