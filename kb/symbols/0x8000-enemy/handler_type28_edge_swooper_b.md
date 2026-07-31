---
address: 0x7e78
end: 0x7e9b
kind: routine
name: handler_type28_edge_swooper_b
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71da, 0x4898, 0x71f6, 0x44ba]
called_by: [0x445f]
tags: [entity, enemy, swooper, animated]
sprint: "0050"
---

# handler_type28_edge_swooper_b

**Types 28–29** — animated edge swooper B. Same machinery as
[[handler_type26_edge_swooper_a]] (joins it at 0x7e06 / active body 0x7e3f) but
uses anim table [[edge_swooper_b_anim]] (0x7e70, colour 0x87 dark-green), a short
spawn countdown (+0x1e=4), and different child types / velocities.

| Type | Entry | Spawn X | child type (+0x1d) | vx |
|------|-------|---------|--------------------|-----|
| 28 | 0x7e78 | 192 (right) | 0x3b (59, sideways) | -2 |
| 29 | 0x7e86 | 48 (left) | 0x29 (41, pair fragment) | +2 |

```
; type 28:  LD HL,0xc03b / LD DE,0xfe00 / JR 0x7e92
; type 29:  LD HL,0x3029 / LD DE,0x0200
7e92  LD BC,0x7e70                ; anim table (col 0x87)
7e95  LD (IX+0x1e),0x04            ; spawn countdown = 4
7e99  JP 0x7e06                    ; → swooper-A shared body
```

## Related

[[handler_type26_edge_swooper_a]] (shared 0x7e06 init + 0x7e3f active),
[[edge_swooper_b_anim]] (0x7e70), [[entity_jump_table]].
