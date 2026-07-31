---
address: 0x7e68
end: 0x7e6f
kind: data
name: edge_swooper_a_anim
confidence: confirmed
sprint: "0050"
tags: [entity, enemy, swooper, animation]
---

# edge_swooper_a_anim

4-frame animation table for [[handler_type26_edge_swooper_a]] (types 26–27).
Read by `entity_update`'s anim sub (0x4912) via IX+0x11:0x12; 4 `(sat_name, colour)`
pairs (anim max +0x10 = 4).

| Frame | sat_name | colour | pattern |
|-------|----------|--------|---------|
| 0 | 0xAC | 0x8E | 43 |
| 1 | 0xB0 | 0x8E | 44 |
| 2 | 0xB4 | 0x8E | 45 |
| 3 | 0xB8 | 0x8E | 46 |

Labelled `DB` block `edge_swooper_a_anim:` in source (sprint 0053; was
mis-decoded as instructions, now converted via `redisasm data`).
