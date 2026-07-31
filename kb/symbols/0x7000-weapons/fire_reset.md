---
address: 0x7544
end: 0x7547
kind: routine
name: fire_reset
confidence: confirmed
inputs:  {}
outputs: { "(E14F)": "0", A: "0 (falls into fire_select)" }
clobbers: [AF]
calls: []
called_by: [0x731e, 0x74a1, 0x74cd, 0x750b, 0x75ff]
sprint: "0048"
tags: [fire, weapon, reset]
---

# fire_reset

## Summary

Resets the fire weapon to type 0. Clears **E14F** and falls straight into
[[fire_select]] (0x7548) with A=0, so the bare weapon's counters are loaded and
the HUD refreshed. Called when a weapon expires ([[fire_life_timer]] at 0x731e,
the expiry handlers at 0x74a1/0x74cd/0x750b) and on player (re)spawn
([[player_ship_handler]] at 0x75ff).

## Analysis (0x7544–0x7547)

```
SUB A             ; A = 0
LD (0xe14f),A     ; clear E14F
                  ; fall through to fire_select (0x7548) with A=0
```

## Confirmed (sprint 0048)

Exercised as the tail of the fire-weapon engine; the `fire_select(0)` path it
feeds is confirmed (fire 0 → E14D=0x00). `tools/sprint0048_verify.py`.
