---
address: 0x8296
end: 0x82cf
kind: routine
name: handler_type36_flashing
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71c5, 0x4898, 0x44ba, 0x7904]
called_by: [0x445f]
tags: [entity, enemy, flashing]
sprint: "0050"
---

# handler_type36_flashing

**Type 36** — slow flashing entity. Drifts down very slowly and XORs its colour
by 0x0E every frame (flicker). Pattern 0x34 (pat 13). Has 16 hit points
(+0x19=0x10) and runs the box hit-sub (0x7904).

```
8296  BIT 7,(IX+0x00) / JR Z,0x82b3          ; uninit → init at 0x82b3
; active:
829c  LD A,(IX+0x04) / XOR 0x0e / LD (IX+0x04),A  ; colour flicker
82a4  CALL 0x4898 / BIT 7,(IX+0) / RET Z
82ac  CALL 0x44ba / CALL 0x7904 / RET            ; entity_post + hit/health sub
; init (0x82b3):
82b3  CALL 0x71c5                                 ; random_x_pos
82b6  LD (IX+0x0c),0x01                            ; bflags = Y-motion
82ba  LD (IX+0x08),0x80                             ; vy_frac = 0x80 (vy=0 → ~0.5px/frame)
82be  LD (IX+0x03),0x34                              ; pattern 13
82c2  LD (IX+0x04),0x8f
82c6  LD (IX+0x19),0x10                                ; 16 hit points
82ca  SET 7,(IX+0x00) / JR 0x829c
```

## Related

[[random_x_pos]] (0x71c5), `0x7904` box hit-sub (see [[handler_type4_box]]),
[[entity_jump_table]].
