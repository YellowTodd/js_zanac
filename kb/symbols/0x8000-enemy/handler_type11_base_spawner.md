---
address: 0x7AD4
end: 0x7AF6
kind: routine
name: handler_type11_base_spawner
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x7A67]
called_by: [0x445F]
tags: [entity, base, projectile]
sprint: "0012"
---

# handler_type11_base_spawner

## Summary

Entity handler for type 11: the base projectile spawner. On every call it reads
the base health counter (0xE130), uses the upper nibble as an index into a
2-byte Y/X position table at 0x7AF7, places a projectile at that position, and
immediately transitions the slot to **type 69** (running base projectile) by
overwriting the type byte and jumping to the type-69 handler.

There is **no bit-7 first-frame guard** — this handler executes fully every
frame the slot exists with type 11.

## Analysis

```
7AD4  LD A, (0xE130)     ; read base health counter
7AD7  RRCA               ; >> 1
7AD8  RRCA               ; >> 2
7AD9  RRCA               ; >> 3
7ADA  AND 0x0E           ; keep bits 1-3 (even index 0,2,4,6,8,A,C,E)
7ADC  LD C, A
7ADD  LD B, 0
7ADF  LD HL, 0x7AF7      ; Y/X pair table (8 pairs max)
7AE2  ADD HL, BC         ; index into table
7AE3  LD (IX+0x00), 0x45 ; overwrite type → 69 (0x45 → ADD A,A = 0x8A → type 69)
7AE7  LD A, (HL)         ; Y position from table
7AE8  LD (IX+0x01), A
7AEB  INC HL
7AEC  LD A, (HL)         ; X position from table
7AED  LD (IX+0x02), A
7AF0  LD (IX+0x03), 0x28 ; pattern byte = 0x28
7AF4  JP 0x7A67          ; jump directly into type-69 running handler
```

### The table at 0x7AF7 is (enemy type, count) — not positions (2026-07-30)

**Correction.** This entry and `game_state_block` both described 0x7AF7 as 8
**Y/X position pairs**. It is not: both bytes are copied straight into +0x18 /
+0x19 at 0x7A6D/0x7A73 and then **overwritten** by `random_x_pos` (0x71C5) at
0x7A82, which sets +0x02 to a random column and +0x01 to 0. They can only be
*(enemy type, count)*, and `base_spawner_active` uses them exactly that way:
+0x18 is the type it emits, +0x19 the ammo. `base_spawner_spawn_table.md`
(sprint 0049) already had this right.

| idx = (0xE130>>4)&7 | type | count | |
|---|---|---|---|
|0|0x0A (10)|30| duster |
|1|0x10 (16)|8| luster |
|2|0x16 (22)|10| veybar |
|3|0x17 (23)|8| veybar |
|4|0x30 (48)|6| |
|5|0x08 (8)|8| umber |
|6|0x41 (65)|6| |
|7|0x24 (36)|30| flashing |

So this is a **wave spawner**, not a base-projectile emitter: 0xE130 is the
encounter accumulator (bumped by `SUB_bfc8`, frozen while 0xE150 bit 1 is set),
and its bits 4-6 pick which enemy wave to send. Nothing in this path reads the
attack list at 0xE780 or the cursor 0xE71E — those belong to
[[base_tick]] and `place_tile_group` upstream.

## Connection to base encounter

```
place_tile_group sets 0xE150=1 (base active), writes attack-list to (0xE71E)
→ some entity-table entry gets type=11 (TBD how 11 is written)
→ entity_dispatch calls handler_type11_base_spawner each frame
→ spawns type-69 projectile at position derived from 0xE130 (health)
```

## Notes

- Type 0x45 = 69; `ADD A,A` for dispatch gives 0x8A → table index 0x8A
  at 0x70B7 + 0x8A = 0x7141 → handler 0x7A67 ✓
- 0xE130 is the base health / base-animation counter (also read by
  `base_encounter_ctrl` 0xBFCB and `handler_type35_base_eye`).
