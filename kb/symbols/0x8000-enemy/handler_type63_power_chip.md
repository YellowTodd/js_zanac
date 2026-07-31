---
address: 0x78af
end: 0x7903
kind: routine
name: handler_type63_power_chip
confidence: confirmed
inputs:  { IX: "pickup entity slot" }
outputs: { "(E10B)": "shot_level incremented" }
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x4898, 0x44b0, 0x5189, 0xbfc8, 0x7771, 0x4c4d, 0x7548, 0x48d0]
called_by: [0x445f]
tags: [item, pickup, power-chip, shot]
sprint: "0054"
---

# handler_type63_power_chip

**Type 63** — the floating **power chip**. A box of type 6 turns into this on
destruction (see [[handler_type4_box]] / [[H-items-and-pickups]]). The chip
drifts ([[entity_update]]) and, when the player's body touches it (collision via
0x44b0 clears its active bit), it raises the normal-shot power level by one and
reloads the shot parameters. (Previously hypothesised as a "player-respawn
handler" — corrected sprint 0054.)

## Decode

```
78af  CALL 0x4898               ; entity_update (drift)
78b2  BIT 7,(IX+0x00) / RET Z   ; not active → return
78b7  CALL 0x44b0               ; collision: clears bit7 on player contact
78ba  BIT 7,(IX+0x00) / RET NZ  ; not collected → return
; ── collected ──
78bf  LD A,0x17 / CALL 0x5189   ; pickup SFX #0x17
78c4  LD IY,0xe300              ; player slot
      (IY+0x00)=0x81            ; ensure player type
      SET 7,(IY+0x05)           ; player flag (brief invuln/flash)
      (IY+0x1b)=0x40            ; player timer
      CALL 0xbfc8               ; inc encounter counter E130 (pickup/difficulty)
78d7  LD A,(0xe10b) / INC A / CP 0x06 / JR C,0x78f8   ; shot_level + 1, < 6 ?
; ── normal: apply chip (0x78f8) ──
78f8  LD (0xe10b),A             ; store new shot_level
      CALL 0x7771               ; load_shot_params → E10D/E/F
      CALL 0x4c4d               ; update_status_bar (HUD)
      JP 0x48d0                 ; entity_clear (consume chip)
; ── maxed (level already 5→6): bonus (0x78df) ──
78df  INC (0xe148)             ; bonus counter
      INC (0xe14f) / CP 0x05 / JP C,0x48d0   ; every 5th maxed chip…
      (0xe14f)=0 / LD A,(0xe14b) / CALL 0x7548 / JP 0x48d0  ; …restart current fire weapon
```

## Confirmed (sprint 0054, micro-exec)

- jump-table[63] = 0x78AF.
- Running 0x78D7 with `shot_level`=3 → 4, and `shot_power_table[4]` reloaded into
  E10D/E/F (`02 04 28` → `02 0a 30`). `tools/sprint0054_verify.py`.

## Related

[[handler_type4_box]] (the box that drops it), [[load_shot_params]] (0x7771),
[[shot_power_table]], [[H-items-and-pickups]], [[entity_jump_table]] (63).
