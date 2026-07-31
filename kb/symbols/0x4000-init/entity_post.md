---
address: 0x44BA
end: 0x44D3
kind: routine
name: entity_post
confidence: confirmed
calls:   [0x45A0, 0x44D4, 0x44F9, 0x4560, 0x453E]
called_by: []
tags: [entity, collision, dispatch]
sprint: "0035"
---

# entity_post

## Summary

Entity dispatch epilogue called by every entity handler after processing. It
computes the current entity's hitbox bounds, runs the software collision check
against the player / shot / ground-target slots, and on a hit transforms both
colliding entities.

> Correction (sprint 0035): the `CALL 0x45A0` here is **not** the sprite-shadow
> push. 0x45A0 is `hitbox_setup_ix` (computes IX hitbox bounds → BC/BC'; see
> `collision_routine.md`). The actual SAT-shadow push is `sprite_sat_write`
> (0x48B8), reached via `entity_update` (0x4898) earlier in each handler.

**Note:** this function body lives in a DB block in the disassembler output
(source line 595). The bytes are valid Z80 code; Ghidra's static analysis missed
the entry point because it is only reachable via indirect `JP HL` from
`entity_dispatch`.

## Analysis

```
44BA  CALL 0x45A0    ; hitbox_setup_ix — compute IX hitbox bounds → BC/BC'
44BD  CALL 0x44D4    ; collision_dispatch / check_hit_player
44C0  JP C, 0x453E   ; hit → collision_response
44C3  CALL 0x44F9    ; collision_dispatch / check_hit_shots
44C6  RET NC         ; no hit → done
44C7  JP 0x453E      ; hit → collision_response
44CA  CALL 0x45A0    ; (alt entry) recompute IX bounds
44CD  CALL 0x44F9    ; shots-only check
44D0  RET NC
44D1  JP 0x453E
```

The 0x44D4 and 0x44F9 helpers are now documented in `collision_dispatch.md`
(they are two distinct collision-target dispatchers, not finalization helpers),
and the 0x453E hit handler in `collision_response.md`.

## The two entries use *different* fire-weapon gates (2026-07-30)

`0xE14E` is the fire-weapon collision mask, and **which bit is tested depends on
which entry point the handler used** - this is easy to miss because the two
tests are 0x50 bytes apart:

| entry | used by | fire gate |
|-------|---------|-----------|
| **0x44BA** | airborne enemies, boxes | `collision_dispatch` 0x44D4 -> **bit 0**; also tests the player slot |
| **0x44CA** | ground structures (0x8806), base segments (0x8B7A) | shots-only sweep 0x44F9, whose tail at **0x4526 tests bit 1**; never tests the player |

The consequence is load-bearing for gameplay: `fire_init_table` gives **fire 0 -
the weapon the player starts each round with - mode 0x02**, so bit 1 only. It
can damage ground structures and base segments, and *nothing* in the air. Gate
it on bit 0 everywhere and the default fire silently does nothing to statues,
which reads as "the statues need far more hits than the original".

## See also

- `collision_dispatch.md` — 0x44D4 / 0x44F9, the target-slot dispatchers.
- `collision_response.md` — 0x453E, type remap on hit.
- `collision_routine.md` — 0x45A0 (`hitbox_setup_ix`) and 0x4560 (the
  `collision_check` primitive).
