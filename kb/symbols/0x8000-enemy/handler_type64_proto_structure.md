---
address: 0x8279
end: 0x8295
kind: routine
name: handler_type64_proto_structure
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, DE, HL]
calls:   []
called_by: [0x445f]
tags: [entity, enemy, spawner, structure]
sprint: "0051"
---

# handler_type64_proto_structure

**Type 64** — a one-shot type selector. Picks an enemy/structure type by reading
into the [[spawn_table]] entity-type list at **0xbecc** (an offset inside the
0xbe76–0xbf2b spawn data), indexed by difficulty (`data_e130`) plus a small
random jitter, then overwrites its own type so the dispatcher runs the chosen
handler next frame. (Earlier guessed as a fixed type-44 converter — actually a
*table-driven* converter that can become many types: seen 0x40/0x2c/0x38/0x0c/
0x0a/0x39/0x30/0x31/0x07/0x1e/…)

```
8279  LD A,(0xe130) / SRL A / LD E,A      ; E = difficulty/2
827f  LD A,R / AND 0x03 / ADD A,E          ; + random 0..3
8284  CP 0x60 / JR C,0x828a / LD A,0x5f     ; clamp index to ≤ 0x5F
828a  LD E,A / LD D,0 / LD HL,0xbecc / ADD HL,DE  ; &proto_structure_type_table[idx]
8291  LD A,(HL) / LD (IX+0x00),A / RET       ; own type = table entry
```

## Related

[[spawn_table]] (the 0xbecc read target), [[handler_type44_ground_structure]]
(one common target), [[entity_jump_table]] (64).
