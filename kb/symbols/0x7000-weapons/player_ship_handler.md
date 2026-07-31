---
address: 0x75d5
end: 0x7611
kind: routine
name: player_ship_handler
confidence: confirmed
inputs:  { IX: "player entity slot (slot 0, 0xE300)" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls: [0x7544, 0xbfd6, 0x4c4d, 0x7771]
called_by: []
sprint: "0048"
tags: [player, ship, entity, handler, spawn]
---

# player_ship_handler

## Summary

Entity handler for the **player ship** (entity slot 0). On its first frame
(IX+0x00 bit 7 clear) it spawns/respawns the ship: sets start position
(X=0xa0, Y=0x78), sprite/attr, a blink-on-spawn flag (IX+0x05 bit 7, blink
frames IX+0x1b=0x40), resets the fire weapon ([[fire_reset]] 0x7544), zeroes the
shot power level (E10B) and E130, redraws the HUD ([[update_status_bar]] 0x4c4d),
and loads the shot params ([[load_shot_params]] 0x7771). Then it falls straight
into [[player_ship_update]] (0x7612) for the per-frame logic.

## Analysis (0x75d5–0x7611)

```
BIT 7,(IX+0x00); JR NZ,0x7612      ; already spawned -> per-frame update
SET 7,(IX+0x00)
LD (IX+0x01),0xa0 / (IX+0x02),0x78 ; Y=0xa0, X=0x78
LD (IX+0x03),0x38 / (IX+0x04),0x8f ; sprite name / attr
LD (IX+0x0c),0x00 / (IX+0x17),0x05 ; type / speed
LD (IX+0x1b),0x40 ; SET 7,(IX+0x05) ; spawn-blink: 0x40 frames
CALL 0x7544                         ; fire_reset
XOR A; LD (0xe10b),A; LD (0xe130),A ; shot level = 0
CALL 0xbfd6
CALL 0x4c4d                         ; update_status_bar
CALL 0x7771                         ; load_shot_params
                                    ; fall into player_ship_update (0x7612)
```

## Confirmed (sprint 0048)

The per-frame update it feeds is confirmed live (movement/shoot/fire), and the
spawn position/HUD are visible in normal play. `tools/sprint0048_live.py`.
