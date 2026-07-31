---
address: 0x732a
end: 0x7330
kind: routine
name: fire_dec_ammo
confidence: confirmed
inputs:  { "(E14D)": "ammo/durability" }
outputs: {}
clobbers: [AF, HL]
calls: [0x7594]
called_by: [0x72a8, 0x73e2]
sprint: "0048"
tags: [fire, weapon, ammo]
---

# fire_dec_ammo

## Summary

Small helper: decrements the fire-weapon ammo counter **E14D** once and tail-calls
[[update_fire_display]] (0x7594) to refresh the HUD. Used by fire-weapon handlers
that consume one unit of ammo per shot/hit (e.g. the init paths at 0x72a8 and
0x73e2) rather than per the 60-frame [[fire_life_timer]] cadence.

## Analysis (0x732a–0x7330)

```
LD HL,0xe14d; DEC (HL)
JP 0x7594            ; update_fire_display (tail-call)
```

## Confirmed (sprint 0048)

On the confirmed fire-dispatch path; E14D writes and the 0x7594 redraw are
confirmed by the engine + display tests. `tools/sprint0048_verify.py`.
