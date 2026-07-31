---
address: 0x44D4
end: 0x453D
kind: routine
name: collision_dispatch
confidence: confirmed
inputs:
  IX: current entity slot (hitbox bounds pre-computed by 0x45A0 into BC/BC')
outputs:
  carry: set if the current entity overlaps any tested target slot
clobbers: [AF, DE, HL, IY, BC]
calls: [0x4560]
called_by: [0x44BA, 0x44CA]
tags: [collision, entity, dispatch]
sprint: "0044"
---

# collision_dispatch

## Summary

Two **distinct** collision-target dispatch helpers (not two entry points to one
routine) called from `entity_post` (0x44BA) after `0x45A0` has loaded the
current entity's hitbox bounds into `BC`/`BC'`. Each helper walks a fixed list
of candidate target slots, type-checks each one, and calls `collision_check`
(0x4560) to test the current IX entity against that target. Returns carry set on
the first overlap so `entity_post` can branch to `collision_response` (0x453E).

These answer the sprint's open question: **0x44D4 and 0x44F9 are separate
helpers**, each guarding a different collision relationship.

## `check_hit_player` — 0x44D4–0x44F8

Tests the current entity against the **player ship** and the active **ground
target**. Used to detect *enemy-hits-player*.

```
44D4  LD A,(0xE14E); AND 0x01     ; ground-collision enabled?
44D9  JR Z,0x44EA                  ; no → skip ground target
44DB  LD IY,0xE380                 ; ground/fire-weapon target slot
44DF  LD A,(IY+0); CP 0x83         ; occupied by a type-0x83 ground struct?
44E4  JR NZ,0x44EA
44E6  CALL 0x4560                  ; collision_check IX vs E380
44E9  RET C                        ; hit → return carry
44EA  LD A,(0xE300); CP 0x81       ; player-ship slot occupied (type 0x81)?
44EF  JR NZ,0x453C                 ; no → clear carry, return
44F1  LD IY,0xE300
44F5  CALL 0x4560                  ; collision_check IX vs player ship
44F8  RET                          ; carry = collision result
```

The sub-entry at **0x44EA** (player-ship-only check, skipping the ground target)
is reached directly from the alternate `entity_post` variant at 0x44B3.

## `check_hit_shots` — 0x44F9–0x453B

Tests the current entity against the **three player shot slots** and the ground
target. Used to detect *player-shot-hits-enemy*.

```
44F9  LD IY,0xE320; LD A,(IY+0); CP 0x82   ; shot slot 0 (type 0x82)?
       JR NZ,..; CALL 0x4560; RET C         ; hit → carry
4508  LD IY,0xE340; ... CP 0x82             ; shot slot 1
       CALL 0x4560; RET C
4517  LD IY,0xE360; ... CP 0x82             ; shot slot 2
       CALL 0x4560; RET
4526  LD A,(0xE14E); BIT 1,A                ; ground-collision (bit 1) enabled?
       JR Z,0x453C
452D  LD IY,0xE380; CP 0x83; CALL 0x4560; RET
```

## Shared tail — 0x453C

```
453C  OR A      ; clear carry (no collision)
453D  RET
```

## Slot map confirmed

| Slot   | Type | Occupant                         |
|--------|------|----------------------------------|
| 0xE300 | 0x81 | player ship                      |
| 0xE320 | 0x82 | player shot 0                    |
| 0xE340 | 0x82 | player shot 1                    |
| 0xE360 | 0x82 | player shot 2                    |
| 0xE380 | 0x83 | ground struct / fire-weapon target |

`0xE14E` is the **collision-enable mask**: bit 0 gates the ground target in
`check_hit_player`, bit 1 gates it in `check_hit_shots`.

## Live confirmation (sprint 0044)

Executes ~124×/0.5 s during gameplay (per-entity collision testing in
`entity_post`). When a player shot overlapped a spawned enemy, the carry path led
straight into `collision_response` (0x453E), which fired and remapped both
parties' types — see `collision_response.md` and `death_transition_table.md`.
`tools/sprint0044_verify.py`.

## See also

- `collision_routine.md` — `hitbox_setup_ix` (0x45A0) and the `collision_check`
  primitive (0x4560) these helpers call.
- `collision_response.md` — 0x453E, the destination when carry is set.
- `entity_post.md` — the caller.
