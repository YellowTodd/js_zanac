---
address: 0x4898
end: 0x48A8
kind: routine
name: entity_update
confidence: confirmed
inputs:
  IX: entity slot pointer
outputs: {}
clobbers: [AF, BC, DE, HL]
calls: [0x4942, 0x496B, 0x48A9]
called_by: []
tags: [entity, motion, homing, sprite]
sprint: "0044"
---

# entity_update

## Summary

Per-slot motion driver shared by most active entity handlers. Reads the entity's
**behaviour-flags byte** at `IX+0x0C` and conditionally applies homing, then
falls through into `sprite_shadow_push` (0x48A9), which applies linear motion +
animation and queues the entity's SAT shadow entry. So a single `CALL 0x4898`
both advances the entity and emits its sprite for the frame.

Called from ~25 sites across the enemy/player handlers (search `CALL 0x4898`).

## Analysis

```
4898  BIT 3,(IX+0x0C)            ; Y-homing enabled?
489C  CALL NZ,0x4942             ;   → Y_homing_sub  (steer Y velocity toward player)
489F  BIT 4,(IX+0x0C)            ; X-homing enabled?
48A3  CALL NZ,0x496B             ;   → X_homing_sub  (steer X velocity toward player)
48A6  LD C,(IX+0x0C)             ; C = behaviour flags (for the fall-through)
                                 ; ── falls into sprite_shadow_push (0x48A9) ──
```

## Behaviour-flags byte (IX+0x0C)

| Bit | Meaning              | Handler          |
|-----|----------------------|------------------|
| 0   | apply Y velocity     | Y_motion_sub 0x48DE |
| 1   | apply X velocity     | X_motion_sub 0x48F8 |
| 2   | run animation        | anim_sub 0x4912  |
| 3   | Y homing             | Y_homing_sub 0x4942 |
| 4   | X homing             | X_homing_sub 0x496B |

Bits 0–2 are consumed by `sprite_shadow_push`; bits 3–4 here. Homing runs
*before* linear motion, so a homing entity adjusts its velocity then integrates
it the same frame.

## Position model (confirmed via Y_motion_sub at 0x48DE)

Position is 16-bit fixed point per axis:
- Y integer at `IX+0x01`, Y fraction at `IX+0x06`; Y velocity at `IX+0x08/0x09`.
- X integer at `IX+0x02`, X fraction at `IX+0x07`; X velocity at `IX+0x0A/0x0B`.

`Y_motion_sub` does `(IX+1:6) += (IX+8:9)`; if the new Y integer ≥ 0xD0 it jumps
to `entity_clear` (0x48D0) to despawn the slot (gone off the top/bottom).
Off-screen clamping/despawn is therefore handled **inside the motion subs**, not
by a separate clamp step. (Corrects the sprint hypothesis that velocity lived at
IX+0x02/0x03 and position at IX+0x0A/0x0B.)

## Live confirmation (sprint 0044)

- Executes ~88×/0.5 s on the entity hot path (called from the per-type handlers).
- Homing routing: spawning a **type-10 duster** (bflags `0x13` = bits 0,1,4 →
  Y-motion, X-motion, **X-homing**) drove the X-homing sub at 0x496B 252× and the
  Y-homing sub at 0x4942 0× — exactly matching bit 4 set / bit 3 clear. Confirms
  bits 3/4 gate the homing calls before the `sprite_shadow_push` fall-through.
  `tools/sprint0044_verify.py`.

## See also

- `sprite_shadow_push.md` — 0x48A9, the linear-motion + SAT-queue tail this
  falls into.
- `sprite_sat_write.md` — 0x48B8, the SAT-shadow append.
- `entity_clear.md` — 0x48D0, slot despawn.
