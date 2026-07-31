---
address: 0x7253
end: 0x730a
kind: routine
name: fire_weapon_handler
confidence: confirmed
inputs:  { IX: "fire-weapon entity slot", "(E14B)": "fire_num" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls: [0x5189, 0x5c2e]
called_by: []
sprint: "0048"
tags: [fire, weapon, entity, handler, dispatch]
---

# fire_weapon_handler

## Summary

Entity handler for the active **fire-weapon entity** (the type-3 entity spawned
by [[player_ship_update]] when the fire key is pressed). On its first frame
(IX+0x00 bit 7 clear) it plays the fire SFX (`A=6; CALL 0x5189`) and dispatches
through `fire_init_dispatch`; on every later frame it dispatches through
`fire_update_dispatch`. Both dispatches go through [[dispatch_inline_table]]
(0x5c2e) keyed on `fire_num` (E14B), selecting one of the eight per-weapon
handlers (see [[fire-weapon-dispatch]]).

## Analysis (0x7253–0x730a)

```
BIT 7,(IX+0x00); JP NZ,0x7279     ; already inited -> update path
SET 7,(IX+0x00)                   ; mark inited
LD A,0x06; CALL 0x5189            ; play_sfx (fire)
LD A,(0xe14b); CALL 0x5c2e        ; -> fire_init_dispatch (0x7269) [fire_num]
        DW 72b3,72a8,729d,7331,73ce,73c8,73ce,728f
0x7279: LD A,(0xe14b); CALL 0x5c2e ; -> fire_update_dispatch (0x727f) [fire_num]
        DW 72de,72ea,72f5,735d,7439,7464,7494,7306
```

## Confirmed (sprint 0048)

Planting `fire_num` and running from the init (0x7263) and update (0x7279) call
sites landed on the tabulated handler for fire 0/3/4/7. `tools/sprint0048_verify.py`.
