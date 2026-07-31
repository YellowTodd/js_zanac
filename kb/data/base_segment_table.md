---
address: 0x8df1
end: 0x8e13
kind: data
name: base_segment_table
confidence: confirmed
sprint: "0052"
tags: [entity, enemy, base, segment]
---

# base_segment_table

7 × 5-byte parameter entries for the base segments
([[handler_type73_base_segment]] 0x8a5a), indexed by `(type − 0xc9) × 5` for
types 73–79. Each entry: `sat_name, HP, y_off, x_off, motion/param`.

| type | addr | sat | HP | y_off | x_off | p5 |
|------|------|-----|----|-------|-------|----|
| 73 | 0x8df1 | 0x20 | 0x28 | 0x00 | 0x00 | 0x7F |
| 74 | 0x8df6 | 0x20 | 0x14 | 0x00 | 0x00 | 0x08 |
| 75 | 0x8dfb | 0x1C | 0x0A | 0xFC | 0xFC | 0x06 |
| 76 | 0x8e00 | 0x20 | 0x14 | 0xFC | 0x00 | 0x0A |
| 77 | 0x8e05 | 0x1C | 0x14 | 0x00 | 0xFC | 0x0A |
| 78 | 0x8e0a | 0x20 | 0x28 | 0x00 | 0x00 | 0x0A |
| 79 | 0x8e0f | 0x24 | 0x63 | 0x04 | 0x04 | 0x10 |

(y_off/x_off are signed: 0xFC = −4.) Type 79's HP 0x63 (99) marks it the
toughest segment. Was part of the mis-decoded region; kept as DB after the
0x8a5a code block (sprint 0052).
