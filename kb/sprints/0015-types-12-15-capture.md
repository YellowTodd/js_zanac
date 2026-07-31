---
id: "0015"
status: done
range: 0x7B07-0x7BCC
strategy: live_debug
budget_turns: 20
---

# Sprint 0015 — Types 12–15 sprite pattern capture

## Goal

Capture type→pattern mappings for entity types 12–15 (handler 0x7B07, shared;
sub-dispatch to 0x7B83/7B98/7BAE/7BCC). Also pick up any other types not seen
in sprint 0013 by collecting more frames with diverse enemy populations.

## Inputs

- `kb/features/entity-sprite-mapping.md` — existing mapping, gaps listed
- `kb/data/entity_jump_table.md` — types 12–15 → 0x7B07

## Verification plan

Same live-capture script as sprint 0013 at entity_dispatch (0x445F), extended
to 40 frames with diverse gameplay.

## Summary (filled at end)

40-frame capture. New confirmed mappings (updated in `entity-sprite-mapping.md`):

- **Types 12/13** → pat 24 (teruzo), color 0x8A, SAT=0x60. Both confirmed, same sprite.
  Shadow: teruzo_sh (pat 25, SAT=0x64) in col-marker — confirms shadow duality.
- **Type 10** → pat 22 (duster) confirmed live; shadow duster_sh (SAT=0x5C) confirmed.
- **Type 19** → transient pat 9 (lg_circle), color 0x80 on first frame, then self-transitions
  to type 0x83 (→ type 3 handler = weapon-0 projectile).
- **Type 35** → also shows teruzo (pat 24), extending confirmed pattern pool.
- **Type 37** → pat 7 (lead), color 0x8F.
- **Type 75** → pat 7 (lead), color 0x00 (transparent = initializing), one of types 73–79 group.
- **Type 39** → now confirmed with duster_sh AND teruzo_sh shadows, proving universal
  shadow-sprite role.

**Static follow-up:** 0x7BAE/0x7BCC are DATA pointers, not code sub-handlers.
Handler 0x7B07 reads 3 bytes (Y, X, color) from each; pattern is hardcoded
`LD (IX+0x03), 0x60` (teruzo, pat 24) at 0x7B4D for ALL types 12–15.
Types 14/15 confirmed: Y=32, X=208/16, color=0x89. All four types fully resolved.
