---
address: 0x82d0
end: 0x8301
kind: routine
name: handler_type44_ground_structure
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71da, 0x71c5, 0x4c8b, 0x4898, 0x71f6, 0x44ba]
called_by: [0x445f, 0x8279]
tags: [entity, enemy, ground-structure]
sprint: "0051"
---

# handler_type44_ground_structure

**Type 44** — main ground structure. Spawned/converted from type 64
(`proto_structure`). Places a structure tile (col-marker sat 0x44), aims at the
player, and runs as a Y+X-moving object. Pattern 0x40 (pat 16), colour 0x83 cyan.

```
82d0  BIT 7,(IX+0x00) / JR NZ,0x82f9
82d6  CALL 0x71da / LD (HL),0x44       ; spawn_col_marker, marker sat = 0x44 (tile)
82db  CALL 0x71c5                       ; random_x_pos
82de  LD A,R / AND 0x03 / INC A / LD (IX+0x17),A  ; homing iters 1–4 (random)
82e6  CALL 0x4c8b                        ; player_pos_snapshot
82e9  LD (IX+0x0c),0x03                   ; bflags Y + X motion
82ed  LD (IX+0x03),0x40 / LD (IX+0x04),0x83 ; pattern 16, cyan
82f5  SET 7,(IX+0x00)
82f9  CALL 0x4898 / CALL 0x71f6 / JP 0x44ba
```

## Related

[[handler_type64_proto_structure]] (converts into this), [[player_pos_snapshot]],
[[spawn_col_marker]], [[entity_jump_table]] (44).
