---
address: 0x8a16
end: 0x8a25
kind: data
name: base_core_anim
confidence: confirmed
sprint: "0052"
tags: [entity, enemy, base, animation]
---

# base_core_anim

Two 4-frame `(sat_name, colour)` animation tables for
[[handler_type72_base_core]] (0x8983), read via the `entity_update` anim sub
(IX+0x11:0x12). The core starts on the first table, then switches to the second
(all colour 0x81 = black) as it nears destruction.

| Frame | phase 1 (0x8a16) | phase 2 (0x8a1e) |
|-------|------------------|------------------|
| 0 | 0x1C / 0x8F | 0x1C / 0x81 |
| 1 | 0x20 / 0x83 | 0x20 / 0x81 |
| 2 | 0x24 / 0x8A | 0x24 / 0x81 |
| 3 | 0x20 / 0x8B | 0x20 / 0x81 |

Kept as DB after the 0x8983 code block (sprint 0052 disassembly); ROM
byte-identical.
