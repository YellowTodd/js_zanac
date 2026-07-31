---
address: 0x791d
end: 0x79b6
kind: routine
name: handler_type7_umber
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x71da, 0x4496, 0x4898, 0x71f6, 0x44ba, 0x8ddb]
called_by: [0x445f]
tags: [entity, enemy, umber]
sprint: "0049"
---

# handler_type7_umber

## Summary

Shared handler for the **umber** cluster (types 7, 8, 9) with three init
entry points and one shared init body + active body. The umber spawns from the
bottom, Y-homes toward the top of the screen (so it exits quickly), and on
reaching the top / stopping spawns a burst of child entities. Each type differs
only in colour and what it bursts into.

| Type | Entry | Colour | Burst behaviour |
|------|-------|--------|-----------------|
| 7 | 0x791d | 0x8F (pat 55, 0xDC) | 7× type-38 fragments (`umber_burst_param_table`) |
| 8 | 0x79be | 0x8B (patched at 0x79c7) | 2× type-41 fragments with Y-homing (+0x18=0x13) |
| 9 | 0x79fb | 0x83 cyan (pat 56, 0xE0) | periodic type-20 spawns via +0x1d=8 timer |

## Init (shared body 0x7923)

```
7923  CALL 0x71da           ; spawn_col_marker
7926  LD (HL), 0xe4         ; col-marker complement sat = 0xE4
7928  LD (IX+0x02), 0x78    ; X = 120 (centre)
792c  LD (IX+0x17), 0x01
7930  LD (IX+0x09), 0x03    ; vy = +3 (down — but Y-homing pulls up, net exits top)
7934  LD (IX+0x15), 0x10    ; y_accel = 16
7938  LD (IX+0x0c), 0x09    ; bflags = Y-motion + Y-homing
793c  LD (IX+0x03), 0xdc    ; pattern 55
7940  LD (IX+0x04), 0x8f    ; colour white
7944  SET 7,(IX+0x00)       ; activate
7948  LD A,(IX+0x00) / SUB 0x88
794d  CALL Z, 0x79c7        ; type 8 (active byte 0x88) → patch colour to 0x8B
7950  DEC A / JP Z, 0x7a04  ; type 9 (0x89) → type-9 init extras
                            ; type 7 falls through to active body
```

Entry points 0x79be (type 8) and 0x79fb (type 9) test BIT 7 then `JP 0x7923`
when uninitialised, else jump to their active code (0x7954 / 0x7a12).

Type-9 extra init (0x7a04): pattern 0xE0 (pat 56), colour 0x83, col-marker
complement 0xE8, +0x1d (spawn timer) = 8.

## Active body (0x7954)

```
7954  LD L,(IX+0x1b) / LD H,(IX+0x1c) / PUSH HL / POP IY   ; IY = child (col-marker)
795d  LD A,(IX+0x09)        ; vy
7960  OR A / JR Z,0x7971    ; vy==0 → stopped at top, do burst
7963  CP 0xff / JR NZ,0x79ae; else just update
                            ; (0xFF/0x00 toggle the pattern/complement pairs)
79ae  CALL 0x4898 (entity_update) / CALL 0x71f6 / JP 0x44ba (entity_post)
```

When stopped, type 7 runs the burst loop at 0x798e–0x79ac: 7 iterations,
`find_free_slot` (0x4496) + write type 0x26 (=38) + copy Y/X + store one byte
from `umber_burst_param_table` (0x79b7) into child +0x1a.

Type 8 burst (0x79cc): two `find_free_slot` calls spawn type 0x29 (=41), copy
Y/X, set child +0x1a=5 and a homing param (+0x18=0x13).

Type 9 active (0x7a12): `DEC (IX+0x1d)`; on reaching 0 reload 8 and spawn one
type 0x14 (=20, lead homing) via `spawn_entity` (0x8ddb).

## umber_burst_param_table (0x79b7–0x79bd)

7 bytes `04 05 02 07 03 06 01` — one per type-7 burst fragment, stored to each
child's +0x1a. See [[umber_burst_param_table]].

## Source note

The 7-byte table at 0x79b7 is now the labelled `DB` block
`umber_burst_param_table:` (sprint 0053). It did not absorb the type-8 entry
0x79be (its last bytes decoded as a 2-byte op, so the entry was already correct).

## Related

[[handler_type4_box]], [[spawn_col_marker]], [[entity_update]], [[entity_post]],
[[entity_jump_table]] (types 7/8/9).
