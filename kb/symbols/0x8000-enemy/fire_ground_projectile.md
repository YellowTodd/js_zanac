---
address: 0x816d
end: 0x8188
kind: routine
name: fire_ground_projectile
confidence: confirmed
inputs:  { IX: "ground-gun entity slot" }
outputs: {}
clobbers: [AF, BC, HL]
calls:   [0x4496, 0x8ddb]
called_by: [0x8094]
tags: [entity, enemy, ground-gun, projectile]
sprint: "0051"
---

# fire_ground_projectile

Fire sub of [[handler_type46_ground_projectiles]] (types 46–55), reached at
0x816d after `entity_update`/`0x71f6`. Flashes the gun muzzle and spawns one
projectile child. This is the `LAB_816D` target of sprint **0039** (part 2).

```
816d  LD (IX+0x03),0x4c               ; own sprite → muzzle flash (tile 0x4C)
8171  LD L,(IX+0x1b) / LD H,(IX+0x1c) / INC HL ×3 / LD (HL),0x54  ; child(+3) = muzzle complement 0x54
817c  CALL 0x4496 / RET C             ; find_free_slot (abort if full)
8180  LD A,(IX+0x1f)                  ; A = child type (per-pair from 0x8189 subtable)
8183  LD C,(IX+0x1d)                  ; C = spawn param
8186  JP 0x8ddb                       ; spawn_entity (tail)
```

Child type comes from +0x1f, set per gun-pair from the 0x8189 subtable (types 38
or 21 — see [[handler_type46_ground_projectiles]]). Closes sprint 0039.

## Related

[[handler_type46_ground_projectiles]], [[spawn_entity]] (0x8ddb), [[entity_jump_table]].
