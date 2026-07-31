---
address: 0x7e70
end: 0x7e77
kind: data
name: edge_swooper_b_anim
confidence: confirmed
sprint: "0050"
tags: [entity, enemy, swooper, animation]
---

# edge_swooper_b_anim

4-frame animation table for [[handler_type28_edge_swooper_b]] (types 28–29).
Same patterns as [[edge_swooper_a_anim]] but colour 0x87 (cyan (MSX colour 7; dark green is 12)).

| Frame | sat_name | colour | pattern |
|-------|----------|--------|---------|
| 0 | 0xAC | 0x87 | 43 |
| 1 | 0xB0 | 0x87 | 44 |
| 2 | 0xB4 | 0x87 | 45 |
| 3 | 0xB8 | 0x87 | 46 |

In source as `DB` following the `edge_swooper_a_anim:` block (sprint 0053; was
mis-decoded as instructions, now converted via `redisasm data`).
