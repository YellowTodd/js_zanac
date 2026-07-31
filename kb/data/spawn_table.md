---
address: 0xBE76
end: 0xBF2B
kind: data
name: spawn_table
confidence: confirmed
sprint: "0029"
tags: [entity, spawn, level-map, ground-structure]
---

# Ground-structure entity spawn tables

Decoded sprint 0029 from `update_spawn_table_ptr` (0xBE27, formerly "sub_be27").
As the level scrolls, that routine re-points `ground_struct_spawn_ctrl`'s
`spawn_table_ptr` (0xE133) into a flat list of entity-type bytes, and selects a
spawn-timer reload value, based on the current scroll position.

## Three sub-tables

### 0xBE76 — spawn-timer reload values (7 bytes)

```
BE76: 38 32 2C 22 1C 14 00
```

Indexed by `(position >> 5)` (computed in `update_spawn_table_ptr`); the value
is stored to `spawn_timer_reload` (0xE138). Values descend → spawns get faster
deeper into the stage.

### 0xBE7C — position → {offset, count} pairs

Indexed by an even offset derived from the scroll position. Each pair gives a
byte used to compute the slice of the entity list and a count compared against
`spawn_subtable_ctr` (0xE135). Spans 0xBE7C–0xBECB.

> **Confirmed against the ROM (2026-07-30).** [[update_spawn_table_ptr]] used to
> render this index as `DE = A & 0x7E`, taken from the unhalved position, which
> conflicted with the `>> 1` here. The instructions at 0xBE3B are
> `SRL A / LD C,A / AND 0x7E`: `SRL A` halves `A` in place, so both the pair
> index and the timer base come from the halved value. **This file was right**;
> that entry has been corrected. The distinction matters because the same `DE`
> is reused at 0xBE6B as the offset into the 0xBECC entity list, so a doubled
> index would spawn the wrong types at every position.

### 0xBECC — flat entity-type list (96 bytes)

`spawn_table_ptr` = `0xBECC + position_offset`. `ground_struct_spawn_ctrl`
reads one byte per spawn; `0x00` terminates the list.

```
BECC: 40 2C 2C 2C 2C 38 38 2C 0C 0A 0D 0A 0E 0F 0A 0A
BEDC: 39 0B 30 31 0A 39 39 40 12 18 10 19 07 1E 30 31
BEEC: 2E 24 2F 19 18 07 08 1E 24 24 08 16 17 2F 2E 1A
BEFC: 1B 0B 44 40 3A 1C 17 08 16 1D 0A 22 32 30 2F 1D
BF0C: 22 22 11 33 3A 34 11 32 36 09 08 07 0A 19 35 37
BF1C: 09 41 0B 1C 1D 24 33 22 3A 1E 42 36 37 09 41 43
```

Entity types seen include: 0x44 (68, ground structure), 0x38 (56, box/pickup),
0x0A–0x0F (enemies), 0x39 (57), 0x0B (11, base projectile spawner), 0x30/0x31
(48/49), 0x16–0x1E, 0x22, 0x33, 0x34, 0x40–0x43. (The live observation
0xBECF = `2C 2C 38 38 …` is this list at base+3.)

The list is **flat type bytes, no per-entry parameters** — spawn position is
computed separately (`spawn_pos` accumulator 0xE12E/0xE12F advances +8 per
spawn). See `kb/symbols/0x9000-scroll/ground_struct_spawn_ctrl.md`.
