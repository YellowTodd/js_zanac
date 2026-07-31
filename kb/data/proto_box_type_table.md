---
address: 0x77ea
end: 0x7807
kind: data
name: proto_box_type_table
confidence: confirmed
sprint: "0051"
tags: [entity, enemy, box]
---

# proto_box_type_table

Per-slot box **type** bytes for [[handler_type68_proto_box]] (0x77a1). The
spawner indexes a 3-byte group with `(data_e104 & 0x0F) × 3` then emits 3 boxes,
reading one byte per box. All values are 4/5/6 (the box variants —
[[handler_type4_box]]). 30 bytes (10 groups).

```
0x77ea: 05 06 05 04 05 06 05 04 04 05 05 05 04 06 04 04 04 04 06 05 04 04
0x7800: 05 06 05 04 06 04 04 06
```

The tail (0x7800–0x7807) is what sprint 0049 provisionally called `data_7800`;
it is part of this table, not a separate block. In source as the labelled `DB`
block `proto_box_type_table:` (sprint 0053; [[proto_box_sat_table]] follows it in
the same run).
