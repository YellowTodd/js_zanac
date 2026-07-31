---
address: 0x7de2
end: 0x7e67
kind: routine
name: handler_type26_edge_swooper_a
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71da, 0x4496, 0x8ddb, 0x4898, 0x71f6, 0x44ba]
called_by: [0x445f]
tags: [entity, enemy, swooper, animated]
sprint: "0050"
---

# handler_type26_edge_swooper_a

**Types 26–27** — animated edge swooper A. Enters from a screen edge, runs a
4-frame animation ([[edge_swooper_a_anim]] 0x7e68, pats 43–46), Y-homes, and
periodically spawns a child entity (whose type is stored in +0x1d).

| Type | Entry | Spawn X | child type (+0x1d) | vx |
|------|-------|---------|--------------------|-----|
| 26 | 0x7de2 | 200 (right) | 0x25 (37, lead bullet) | -1 |
| 27 | 0x7df3 | 40 (left) | 0x14 (20, lead homing) | 0 (drift) |

## Init prologues + shared body (0x7dff)

```
; type 26:  LD HL,0xc825 / LD DE,0xff40 / LD BC,0x7e68 / JR 0x7dff
; type 27:  LD HL,0x2814 / LD DE,0x00c0 / LD BC,0x7e68
7dff  LD (IX+0x1e),0x18                  ; spawn countdown = 24
7e06  LD (IX+0x1d),L                       ; child type to spawn (L)
7e09  LD (IX+0x11),C / LD (IX+0x12),B       ; anim table ptr (0x7e68 / 0x7e70)
7e0f  LD (IX+0x02),H                          ; spawn X
7e12  LD (IX+0x0a),E / LD (IX+0x0b),D          ; vx_frac, vx
7e18  CALL 0x71da                               ; spawn_col_marker
7e1b  LD (IX+0x08),0x80 / LD (IX+0x09),0x02      ; vy ≈ 2.5 down
7e23  LD (IX+0x17),0x01 / LD (IX+0x15),0x07       ; y_accel = 7
7e2b  LD (IX+0x0c),0x0f                            ; bflags = Y + X + anim + Y-homing
7e2f  LD (IX+0x10),0x04 / LD (IX+0x0d),0x04 / LD (IX+0x0e),0x04  ; 4-frame anim
7e3b  SET 7,(IX+0x00)
```

## Active body (0x7e3f) — shared with swooper B

```
7e3f  DEC (IX+0x1e) / JR NZ,0x7e55         ; spawn cadence
7e44  LD (IX+0x1e),0x20 / CALL 0x4496 / JR C,0x7e55
7e4d  LD A,(IX+0x1d) / LD C,0x04 / CALL 0x8ddb  ; spawn child (type +0x1d)
7e55  CALL 0x4898 / CALL 0x71f6
7e5b  LD DE,0xffeb / ADD HL,DE / LD A,(IX+0x03) / ADD A,0x10 / LD (HL),A  ; child sprite = own+0x10
7e65  JP 0x44ba
```

## Related

[[handler_type28_edge_swooper_b]] (28–29, joins 0x7e06/0x7e3f),
[[edge_swooper_a_anim]] (0x7e68), [[set_velocity_from_dir]], [[entity_jump_table]].

## Corrections (2026-07-30)

**vx values.** Type 26 is `0xFF40` = **-0.75**/frame and type 27 is `0x00C0` =
**+0.75**/frame; both fractional bytes are non-zero and are written to +0x0A.
An earlier table gave -1 and "0 (drift)".

**Address slip.** The `LD (IX+0x1E),0x18` is at **0x7E02**, not 0x7DFF (which
is `LD BC,0x7E68`). This matters because types 28/29 `JP 0x7E06` and must skip
*both*. Type 26's own `LD BC,0x7E68` at 0x7DEE is dead - `JR 0x7DFF` reloads
the identical value.

**Invisible for three frames.** +0x03 and +0x04 are never initialised, so the
main sprite is pattern 0 / colour 0 until `anim_sub` first fires on frame 4.
The enemy is collidable the whole time. The marker's pattern is also written
*after* it has already been pushed (0x7E5F follows 0x7E58), so the black half
lags the parent by one frame.
