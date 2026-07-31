---
address: 0xBFAB
end: 0xBFB2
kind: routine
name: inc_encounter_a
confidence: confirmed
inputs:  {}
outputs: {}
clobbers: [AF, HL]
calls:   [0xBFCB]
called_by: [0x8F58, 0x9334]
tags: [base, gamestate, entity, encounter]
sprint: "0029"
---

# inc_encounter_a

## Summary

Increments the base-encounter accumulator at 0xE12E (gated by the boss-active
flag), then requests a spawn-table recompute by setting `spawn_ctrl` (0xE12D)
bit 0 (which makes `ground_struct_spawn_ctrl` call `update_spawn_table_ptr`
next frame). Falls into the shared display tail at 0xBFD6.

```
BFAB  LD HL, 0xE12E
BFAE  CALL 0xBFCB        ; inc (HL) unless 0xE150 bit1 set; saturate at 0xFF
BFB1  JR 0xBFB9          ; -> SET 0,(0xE12D); RET   (set recompute request)
```

See `kb/symbols/0x9000-scroll/sub_bfa0.md` and `base_encounter_ctrl.md` for the
shared 0xBFD6 HUD-display tail. Counterpart: [[dec_encounter_a]].
