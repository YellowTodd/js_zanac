---
address: 0x453E
end: 0x455F
kind: routine
name: collision_response
confidence: confirmed
inputs:
  IX: current entity slot (one collision party)
  IY: target slot that overlapped (other collision party)
outputs:
  IX_0x18: original type of IX (low 7 bits), saved for the handler
  IX_0x00: remapped post-collision type (from table 0x716B)
  IY_0x00: remapped post-collision type (from table 0x716B)
clobbers: [AF, DE, HL]
calls: []
called_by: [0x44C0, 0x44C7, 0x44D1, 0x44AD, 0x44B7]
tags: [collision, entity, death]
sprint: "0044"
---

# collision_response  (LAB_ram_453e)

## Summary

The "a collision happened" handler, jumped to from every `entity_post` path
once `collision_dispatch` returns carry. It transforms **both** colliding
entities into their post-collision type by looking each current type up in the
transition table at **0x716B**, and stashes the current entity's original type
in `IX+0x18` for the type-specific death/score handler to read.

## Analysis

```
453E  LD A,(IX+0); AND 0x7F      ; A = current type, strip "active" bit 7
4543  LD (IX+0x18),A             ; save original type → slot+0x18
4546  LD E,A; LD D,0
4549  LD HL,0x716B; ADD HL,DE    ; HL → transition_table[type]
454D  LD A,(HL); LD (IX+0),A     ; IX type ← transition_table[type]
4551  LD A,(IY+0); AND 0x7F      ; other party's type
4557  LD HL,0x716B; ADD HL,DE... ; (DE recomputed from IY type)
455B  LD A,(HL); LD (IY+0),A     ; IY type ← transition_table[type]
455F  RET
```

Both entities' type bytes (`slot+0x00`) are replaced with the value the
transition table maps them to — typically an explosion/despawn type. The next
dispatch tick will run the new type's handler instead.

`IX+0x18` preserves the pre-hit type so the explosion handler can still award
the correct score / spawn the correct debris for what was destroyed.

## Table 0x716B

`transition_table[type & 0x7F]` → post-collision type. Now documented as
`death_transition_table` (0x716B–0x71C4, 90 entries). The same table base is
referenced twice here (0x4549, 0x4557). Three main death classes: most enemies →
35 (explosion), bullets/shots → 40 (instant despawn), ground structures → 80
(base damage); the player (1) → 60 (death explosion).

> Note: `collision_routine.md` (sprint 0030) records that a *partial* decode in
> sprint 0021 mistakenly placed `LD HL,0x716B` inside the hitbox check at 0x4560.
> The genuine `LD HL,0x716B` references are **here**, at 0x4549 / 0x4557.

## Live confirmation (sprint 0044)

Captured at 0x453E (type in) and at the RET 0x455F (type out) over real
shot-vs-enemy collisions:

| IX type in | IX type out | exp `tbl[t]` | IY type in | IY type out | exp |
|---|---|---|---|---|---|
| 44 (ground struct) | 35 | 35 | 2 (player shot) | 40 | 40 |
| 4 (box enemy) | 35 | 35 | 2 (player shot) | 40 | 40 |

Both parties' `slot+0x00` are replaced with `death_transition_table[type&0x7F]`
exactly. (Sprint 0030 had earlier observed a 0x453E hit with IX type 0x44 / IY
type 0x02, confirming the resolution point; sprint 0044 confirms the remap
values.) `tools/sprint0044_verify.py`.

## See also

- `death_transition_table.md` — 0x716B, the post-collision type map applied here.
- `collision_dispatch.md` — produces the carry that lands here.
- `entity_post.md` — the `JP C,0x453E` / `JP 0x453E` callers.
