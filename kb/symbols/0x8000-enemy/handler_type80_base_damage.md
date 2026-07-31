---
address: 0x8E14
kind: routine
name: handler_type80_base_damage
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, HL]
calls:   [0xBFB3, 0x5189]
called_by: [0x445F]
tags: [entity, base, collision]
sprint: "0012"
---

# handler_type80_base_damage

## Summary

Entity handler for type 80: fired when a player projectile hits the base.
On first call it invokes `base_encounter_ctrl` entry 0xBFB3 (the DECREMENT
path, which decrements the base health counter at 0xE12E and rewrites the VRAM
HUD display), then spawns an explosion via `CALL 0x5189` with A=0x12 (18 =
explosion animation type).

## Analysis

```
8E14  BIT 7,(IX+0)
8E18  JR NZ, 0x8E2D      ; initialized: running code
8E1A  CALL 0xBFB3        ; decrement base health (base_encounter_ctrl)
8E1D  LD A, 0x12         ; explosion type 18
8E1F  CALL 0x5189        ; spawn explosion entity
8E22  SET 7,(IX+0)       ; mark initialized
8E26  LD (IX+0x0C), 0x00 ; no behavior flags (static entity)
8E2A  JP 0x849C          ; continue to common epilogue
8E2D  CALL 0x8F45        ; running: some update
8E30  LD A, (IX+0x0F)
8E33  OR A
8E34  JP NZ, 0x4898      ; if +0x0F non-zero → entity update
```

## Notes

- 0xBFB3 = `base_encounter_ctrl` decrement entry: calls 0xBFC2 with HL=0xE12E.
  If 0xE12E is non-zero, decrements it and rewrites VRAM columns 0x3839/0x3859.
- The base is destroyed when 0xE12E reaches 0 (health fully depleted).
- How type-80 slots get populated is still uncertain (likely written from the
  player projectile collision handler when hitting the base tile area).
