---
address: 0xE149
kind: data
name: spawn_variant_ctr
confidence: confirmed
sprint: "0027"
tags: [spawn, gamestate, entity]
---

# spawn_variant_ctr

Counter incremented each time a specific entity type is spawned (by handler
at 0x832B). The low 3 bits (& 0x07) are used as the variant index stored in
the new entity's slot at offset +0x1D, cycling through 8 variants:

```z80
; 0x8327
LD  HL, 0xE149
LD  A, (HL)
INC (HL)              ; E149++
AND 0x07              ; variant = old_value & 7
LD  (IX+0x1D), A      ; store variant in entity slot
```

The full byte wraps at 256 (not masked), so it counts up indefinitely
but variant index only uses bits 0–2.

Observed: starts at 0 (title), increments to 1 after first game-start spawn,
reaches 0x0B by base_approach (round 5).
