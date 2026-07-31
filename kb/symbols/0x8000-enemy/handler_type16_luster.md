---
address: 0x7beb
end: 0x7d0e
kind: routine
name: handler_type16_luster
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x71da, 0x4496, 0x8ddb, 0x4cf7, 0x4898, 0x71f6, 0x44ba]
called_by: [0x445f]
tags: [entity, enemy, luster]
sprint: "0049"
---

# handler_type16_luster

## Summary

Shared handler for the **luster** family (types 16, 17, 18) — three init entry
points feeding a common init body (0x7c05) and two running bodies (0x7c43 plain
/ child-spawner, 0x7cd8 timed bullet-firer). Pattern 0x74 (pat 29) at spawn,
toggling to 0x78 (pat 30). Each spawns from a random screen side. Confirmed in
[[entity_jump_table]].

| Type | Entry | bflags | Motion | Colour | Running body |
|------|-------|--------|--------|--------|--------------|
| 16 | 0x7beb | 0x01 (Y) | straight fall vy=2 | 0x8E | 0x7c43 spawns type-38 on Y-threshold |
| 17 | 0x7c8a | 0x13 (Y+X+Xhom) | vy=2, x_accel=0x40, tgt via +0x1e=0xE0 | 0x8E | 0x7c43 |
| 18 | 0x7cb3 | 0x13 (Y+X+Xhom) | vy=2, x_accel=0x0E, +0x1d=0x30 timer | 0x8B | 0x7cd8 fires type-37 every 0x30 frames |

## Per-type init prologues

Each entry loads colour C, motion fields, and two `(X, vel)` packed words
DE/HL, then `JP 0x7c05` (16 falls through):

```
; type 16  (0x7beb)
  LD C,0x8e / LD (IX+0xc),0x01 / LD (IX+9),0x02 / LD (IX+0x1e),0xc0
  LD DE,0x4001 / LD HL,0xb007            ; (X=0x40,v=1) or (X=0xb0,v=7)
; type 17  (0x7c8a)
  LD (IX+0x17),0x04 / LD (IX+0xc),0x13 / LD (IX+9),0x02 / LD (IX+0xb),0xfc
  LD (IX+0x16),0x40 / LD (IX+0x1e),0xe0 / LD C,0x8e
  LD DE,0x3001 / LD HL,0xb007            ; (X=0x30,v=1) or (X=0xb0,v=7)
  JP 0x7c05
; type 18  (0x7cb3)
  LD (IX+0x17),0x02 / LD (IX+9),0x02 / LD (IX+0x16),0x0e / LD (IX+0xc),0x13
  LD (IX+0x1d),0x30 / LD C,0x8b
  LD DE,0x60ff / LD HL,0x9000            ; (X=0x60,v=0xff) or (X=0x90,v=0)
  JP 0x7c05
```

## Common init body (0x7c05)

```
7c05  LD A,R / AND 0x01 / JR Z,0x7c0c / EX DE,HL   ; pick side (DE vs HL word)
7c0c  CALL 0x71da / LD (HL),0x7c                    ; spawn_col_marker, complement 0x7C
7c0f  LD (IX+0x02),D                                ; X = high byte of chosen word
7c14  LD (IX+0x03),0x74                              ; pattern 29
7c18  LD (IX+0x04),C                                 ; colour
7c1b  SET 7,(IX+0x00)
7c1f  LD A,(IX+0x00) / SUB 0x92 / JR Z,0x7c32        ; type 18 (active 0x92) → bullet timer setup
7c26  LD (IX+0x1d),E / INC A / JR NZ,0x7c43          ; type 16 → running; type 17 (0x91) continues
7c2c  LD (IX+0x14),D / JP 0x7c43                      ; (type 17 X-home target)
7c32  LD (IX+0x14),E / RRC E / LD A,0x03 / JR Z,..    ; type 18 X-home dir from vel byte
      LD A,0xfd / LD (IX+0x0b),A / JP 0x7cd8
```

## Running body A — 0x7c43 (types 16/17)

```
7c43  (IY = col-marker child)
7c4c  LD B,(IX+0x01) / A=B+0x18 / AND (IX+0x1e) / SUB 0x18 / CP B / JR Z,0x7c7f
7c5a  A=B+0x10 / AND (IX+0x1e) / SUB 0x10 / CP B / JP NZ,0x79ae   ; Y on grid?
7c66  LD (IX+0x03),0x78 / LD (IY+0x03),0x80           ; flip to pattern 30
      CALL 0x4496 / JP C,0x79ae / LD A,0x26 / LD C,(IX+0x1d) / CALL 0x8ddb / JP 0x79ae  ; spawn type-38
7c7f  LD (IX+0x03),0x74 / LD (IY+0x03),0x7c / JP 0x79ae               ; flip back to pattern 29
```

Periodically (when Y aligns to the `+0x1e` mask grid) the luster drops a type-38
fragment and pulses its sprite between patterns 29/30.

## Running body B — 0x7cd8 (type 18)

```
7cd8  (IY = child) / DEC (IX+0x1d) / JR NZ,0x7cfc
7ce6  LD (IX+0x1d),0x30 / LD (IX+0x03),0x74 / LD (IY+0x03),0x7c
      CALL 0x4496 / JR C,0x7cfc / LD A,0x25 / CALL 0x8ddb            ; fire type-37 lead bullet
7cfc  LD A,(IX+0x1d) / CP 0x08 / JP NZ,0x79ae
      LD (IX+0x03),0x78 / LD (IY+0x03),0x80 / JP 0x79ae              ; muzzle flash near reload
```

Type 18 fires a type-37 (lead bullet) on a 48-frame cadence while homing toward
the player horizontally.

## Related

[[set_velocity_from_dir]], [[spawn_col_marker]], [[spawn_entity]] (0x8ddb),
[[handler_type7_umber]] (0x79ae shared tail), [[entity_jump_table]] (16/17/18).
