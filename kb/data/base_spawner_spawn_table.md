---
address: 0x7af7
end: 0x7b06
kind: data
name: base_spawner_spawn_table
confidence: confirmed
sprint: "0049"
tags: [entity, enemy, spawner, base]
---

# base_spawner_spawn_table

8 × `(enemy_type, count)` pairs read by [[handler_type11_base_spawner]] (0x7ad4)
and consumed by [[base_spawner_active]] (0x7a67). Type 11 selects an entry with
`(data_e130 >> 3) & 0x0E` (difficulty/round driven), writes
`enemy_type → +0x01`, `count → +0x02`, then the active state emits `count`
copies of `enemy_type`, one per fire interval, before retiring.

| # | enemy_type | count | Enemy |
|---|-----------|-------|-------|
| 0 | 0x0A (10) | 30 | duster |
| 1 | 0x10 (16) | 8  | luster |
| 2 | 0x16 (22) | 10 | veybar |
| 3 | 0x17 (23) | 8  | veybar |
| 4 | 0x30 (48) | 6  | ground-gun (type 48) |
| 5 | 0x08 (8)  | 8  | umber (type 8) |
| 6 | 0x41 (65) | 6  | stealth ground (type 65) |
| 7 | 0x24 (36) | 30 | flashing entity |

## Source note

Labelled `DB` block `base_spawner_spawn_table:` in source (sprint 0053; was
mis-decoded as instructions). Its decode had absorbed the leading `DD` of the
teruzo handler entry 0x7b07 — `redisasm data` restored it (`BIT 7,(IX+0)` now
renders correctly).
