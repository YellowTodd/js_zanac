---
address: 0x7db4
end: 0x7de1
kind: routine
name: handler_type24_veybar_fast
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71da, 0x4898, 0x71f6, 0x44ba]
called_by: [0x445f]
tags: [entity, enemy, veybar]
sprint: "0050"
---

# handler_type24_veybar_fast

**Types 24–25** — fast veybar. Same sprite/morph/active body as
[[handler_type22_veybar]] (joins its init tail at 0x7d2d and active body at
0x7d4c) but adds **X-homing** (bflags 0x1b) and a faster horizontal entry; does
not fire (the fire sub gates on type 22 only).

```
7db4  BIT 7,(IX+0x00) / JP NZ,0x7d4c        ; active → shared veybar body
7dbb  LD (IX+0x14),0xff                        ; X-home target dir (right side)
7dbf  LD DE,0xb8fd / (R&1 ? +0x14=0x00, DE,0x3803)  ; right X=184 vx=-3 | left X=56 vx=+3
7dcf  LD (IX+0x0c),0x1b                          ; bflags = Y + X + Y-homing + X-homing
7dd3  LD (IX+0x16),0x10                           ; x_accel = 16
7dd7  LD (IX+0x04),0x89                            ; colour
7ddb  LD (IX+0x1d),0x58                             ; morph countdown = 88
7ddf  JP 0x7d2d                                      ; → veybar init tail (col-marker, vy, sat)
```

## Related

[[handler_type22_veybar]] (shared 0x7d2d init tail + 0x7d4c active body),
[[entity_jump_table]] (24–25).
