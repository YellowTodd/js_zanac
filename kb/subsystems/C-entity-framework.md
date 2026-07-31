---
letter: C
title: Entity Framework
coverage: done
status: done
---

# C — Entity Framework

## Role

The generic machinery that drives every moving object (player, shots, enemies,
bullets, ground structures, pickups): the 32-byte slot pool, the type-indexed
dispatcher, the per-slot motion/animation/homing integrator, the SAT shadow
push, and the software collision system. This is the *engine*; the per-type
*behaviours* live in [[G-enemy-and-spawn-system]] and [[F-player-ship-and-weapons]].

## Slot model

Entity slots are 32 bytes each starting at `entity_table` (0xE300). Fixed slots:
E300=player ship (type 0x81), E320/E340/E360=player shots (0x82),
E380=ground/fire-weapon target (0x83); the rest are a general pool. Field layout
(IX+offset) documented in `entity_table` / `db-sections-with-code`.

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x445F | `entity_dispatch` | confirmed | type byte → `entity_jump_table` → `JP HL` (bit 7 shifts out: index = `(type&0x7F)*2`) |
| 0x4496 | `alloc_entity_slot` | confirmed | find free pool slot |
| 0x44BA | `entity_post` | confirmed | epilogue: hitbox setup + collision routing |
| 0x44D4 | `collision_dispatch` | confirmed | per-target collision dispatchers |
| 0x453E | `collision_response` | confirmed | type remap on hit (`death_transition_table` 0x716B) |
| 0x4560 | `collision_routine` | confirmed | hitbox check/setup pair |
| 0x45C9 | `collision_size_table` | confirmed (data) | hitbox half-size pairs |
| 0x4898 | `entity_update` | confirmed | homing + fall into motion/SAT |
| 0x4C8B | `player_pos_snapshot` | confirmed | player Y/X → 0xE129/0xE12A + above-flag (collision/homing input) |
| 0x48D0 | `entity_clear` | confirmed | zero a slot (despawn) |
| 0x40BA | `reset_entities` | confirmed | clear whole pool (shared [[A-boot-and-init]]) |

## Data

- `entity_table` (0xE300), `entity_jump_table` (0x70B9),
  `death_transition_table` (0x716B), `collision_size_table` (0x45C9).

## Guides

- `entity-sprite-mapping`, `db-sections-with-code`.

## Gaps / open questions

None — all C routines `confirmed` (sprint 0044). The full type→handler map is
enumerated in [[entity_jump_table]] (per-type *behaviours* remain G's scope), the
collision-result table is now [[death_transition_table]] (0x716B, converted to a
labeled DB block), and `player_pos_snapshot` is confirmed.

## Sprints

Done: 0005, 0011, 0014, 0021, 0024, 0030, 0035,
0044 (confirm dispatcher/collision/update/snapshot + `death_transition_table`).
