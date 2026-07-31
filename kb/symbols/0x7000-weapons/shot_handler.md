---
address: 0x7221
end: 0x7252
kind: routine
name: shot_handler
confidence: confirmed
inputs:  { IX: "shot entity slot", "(E10E)": "shot_vy_raw", "(E10F)": "shot_sat_name" }
outputs: {}
clobbers: [AF, HL]
calls: [0x5189, 0x4898]
called_by: []
sprint: "0048"
tags: [shot, weapon, entity, player, handler]
---

# shot_handler

## Summary

Entity handler for the player's normal **shot** (type-2 entity spawned by
[[player_ship_update]]). On its first frame it initialises the shot's sprite,
plays the shot SFX, and sets an upward velocity from [[shot_power_table]]'s
cached values; on later frames (IX+0x00 bit 7 set) it just advances the entity
via the generic post step (0x4898).

## Analysis (0x7221–0x7252)

```
BIT 7,(IX+0x00); JP NZ,0x4898       ; already inited -> entity advance
LD A,(0xe10f); LD (IX+0x03),A       ; sprite name = shot_sat_name
SRL A; SRL A; ADD 0x03; CALL 0x5189 ; play_sfx (shot pitch from sprite name)
LD (IX+0x04),0x8f                    ; colour/attr
LD (IX+0x05),0x00
LD (IX+0x0c),0x01                    ; entity type/flags
LD A,(0xe10e); CPL                   ; shot_vy_raw, negated = upward
LD (IX+0x08),0x00; LD (IX+0x09),A    ; Y velocity (high byte)
SET 7,(IX+0x00); RET                 ; mark inited
```

The shot moves straight up (negated `shot_vy_raw`); the X velocity is 0 (no
horizontal drift). Sprite name + SFX pitch scale with the shot power level via
[[load_shot_params]] / [[shot_power_table]].

## Confirmed (sprint 0048)

The spawn path that creates these entities (0x76d9 in `player_ship_update`) fired
repeatedly while holding the shot key. `tools/sprint0048_live.py`.
