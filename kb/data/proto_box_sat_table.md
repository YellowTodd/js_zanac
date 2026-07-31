---
address: 0x7808
end: 0x7825
kind: data
name: proto_box_sat_table
confidence: confirmed
sprint: "0051"
tags: [entity, enemy, box]
---

# proto_box_sat_table

Per-slot box sprite/param bytes for [[handler_type68_proto_box]] (0x77a1),
written to each spawned box's +0x03. Indexed with `(data_e105 >> 4) × 3`; 3 bytes
read (one per box). 30 bytes (10 groups).

```
0x7808: 01 21 01 21 01 21 01 21 41 41 21 01 11 01 11 01
0x7818: 11 01 21 01 41 41 01 21 01 11 21 21 11 01
```

In source as `DB` following the `proto_box_type_table:` block; the box handler
entry at 0x7826 (`BIT 7,(IX+0)`) decodes correctly (sprint 0053 — its leading
`DD`, formerly absorbed by this table's decode, was restored via `redisasm data`).
