---
address: 0x7d0f
end: 0x7db3
kind: routine
name: handler_type22_veybar
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x71da, 0x4c91, 0x4cf7, 0x4496, 0x8ddb, 0x4898, 0x71f6, 0x44ba]
called_by: [0x445f]
tags: [entity, enemy, veybar]
sprint: "0050"
---

# handler_type22_veybar

## Summary

The **veybar** family: types 22–23 (this entry, 0x7d0f) and types 24–25
(`handler_type24_veybar_fast`, 0x7db4) which join the same init tail (0x7d2d)
and the same **active body (0x7d4c)**. Pattern 0x84 (pat 33). Descends while
Y-homing; a type-22 veybar fires a type-37 lead bullet at the player.

## Init — types 22/23 (0x7d0f)

```
7d0f  BIT 7,(IX+0x00) / JR NZ,0x7d4c       ; active → shared body
7d15  LD DE,0xc8ff / (R&1 ? LD DE,0x2801)   ; right: X=200 vx=-1 | left: X=40 vx=+1
7d21  LD (IX+0x0c),0x09                       ; bflags = Y-motion + Y-homing
7d25  LD (IX+0x04),0x83                        ; colour = EC | 3 light green
7d29  LD (IX+0x1d),0x50                         ; descent/morph countdown = 80
7d2d  CALL 0x71da / LD (HL),0x98               ; spawn_col_marker, complement 0x98
7d32  LD (IX+0x0b),E / LD (IX+0x02),D           ; vx, X from DE
7d38  LD (IX+0x17),0x01 / LD (IX+0x09),0x04      ; vy = 4
7d40  LD (IX+0x15),0x14 / LD (IX+0x03),0x84       ; y_accel=0x14, pattern 33
7d48  SET 7,(IX+0x00)
```

## Active body (0x7d4c) — shared 22–25

```
7d4c  (IY = col-marker child)
7d55  BIT 0,(IX+0x05) / JR NZ,0x7d83        ; phase-1 done → plain update
7d5b  DEC (IX+0x1d) / JR NZ,0x7d64 / SET 0,(IX+0x05)
7d64  LD A,(IX+0x1d) / CP 0x40 / JR NC,0x7d83 ; second half of countdown drives morph
7d6b  RRCA / RRCA / … / LD A,0x94 / SUB E      ; pattern sat = 0x94 - (countdown>>2 step)
7d76  LD (IX+0x03),A / ADD A,0x14 / LD (IY+0x03),A  ; entity + child sprite morph
7d7e  CP 0xa0 / CALL Z,0x7d8c                    ; at one morph step → fire sub
7d83  CALL 0x4898 / CALL 0x71f6 / JP 0x44ba      ; entity_update + post
```

## Fire sub (0x7d8c) — type 22 only

```
7d8c  LD A,(IX+0x00) / SRL A / CP 0x4b / JR NZ,0x7dab  ; only type 22 (0x96>>1)
7d95  LD (IX+0x17),0x04 / CALL 0x4c91 / CALL 0x4cf7    ; aim at player
7d9f  LD (IX+0x17),0x01 / LD (IX+0x15),0x0c / SET 1,(IX+0x0c)  ; restore + add X-homing
7dab  CALL 0x4496 / RET C / LD A,0x25 / JP 0x8ddb        ; spawn type-37 lead bullet
```

## Related

[[handler_type24_veybar_fast]] (24–25, joins 0x7d2d/0x7d4c),
[[handler_type37_lead_bullet]], [[set_velocity_from_dir]], [[spawn_col_marker]],
[[entity_jump_table]] (22–23).

## Corrections (2026-07-30)

**The fire gate is the type PAIR, not type 22.** 0x7D8F is `SRL A`, which
discards bit 0, so `(0x80|22) >> 1 == (0x80|23) >> 1 == 0x4B`: the `CP 0x4B`
at 0x7D91 admits **both 22 and 23**. And types 24/25 only fail that test -
`JR NZ,0x7DAB` lands *inside* the same sub, so they still allocate a slot and
spawn a **type-37 lead bullet**; they merely skip the self-aim and the X-motion
enable. Every veybar fires.

**Colour 0x83 is light green** (MSX colour 3), not cyan (7).

**There is no homing target.** `+0x13` is never written, so Y homing pulls
`vy` toward 0 from `+0x0400` at 0x14/frame: the veybar descends, decelerates,
and after ~51 frames climbs back out. Related: for types 22/23 the behaviour
byte is 0x09, which has **no bit 1**, so the `(IX+0x0B) = +/-1` written at
0x7D32 is dead - X motion only switches on at 0x7DA7, by which point
`set_velocity_from_dir` has already overwritten the velocity.

**The morph gate** at 0x7D6B reduces to "`+0x1D & 0x0F == 0` while below
0x40", i.e. counts 0x30/0x20/0x10/0x00 -> sprites 0x88/0x8C/0x90/0x94. The
fire happens at exactly `+0x1D == 0x20`, once.
