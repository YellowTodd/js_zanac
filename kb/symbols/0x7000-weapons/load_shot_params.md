---
address: 0x7771
end: 0x778e
kind: routine
name: load_shot_params
confidence: confirmed
inputs:  { "(E10B)": "shot power level 0-5" }
outputs: { "(E10E)": "shot_vy_raw", "(E10D)": "shot_max_simultaneous", "(E10F)": "shot_sat_name" }
clobbers: [AF, BC, HL]
calls: []
called_by: [0x760f]
sprint: "0048"
tags: [shot, weapon, power, player]
---

# load_shot_params

## Summary

Loads the normal-shot parameters for the current power level. Reads `shot_level`
(E10B, masked to low nibble), indexes [[shot_power_table]] (0x778f) by level×3,
and copies the 3-byte record into the live shot state: **E10E** (`shot_vy_raw`),
**E10D** (`shot_max_simultaneous`), **E10F** (`shot_sat_name`). Called once during
player (re)spawn from [[player_ship_handler]] (0x760f).

## Analysis (0x7771–0x778e)

```
LD HL,0x778f                     ; shot_power_table
LD A,(0xe10b); AND 0x0f; LD B,A; ADD A,A; ADD A,B; LD C,A; LD B,0; ADD HL,BC  ; +level*3
LD A,(HL); LD (0xe10e),A; INC HL ; vy
LD A,(HL); LD (0xe10d),A; INC HL ; cap
LD A,(HL); LD (0xe10f),A; RET    ; sprite name
```

## Confirmed (sprint 0048)

For levels 0-5, E10E/E10D/E10F matched `shot_power_table[level]` exactly.
`tools/sprint0048_verify.py`.
