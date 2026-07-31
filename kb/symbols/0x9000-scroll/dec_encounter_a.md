---
address: 0xBFB3
end: 0xBFBE
kind: routine
name: dec_encounter_a
confidence: confirmed
inputs:  {}
outputs: {}
clobbers: [AF, HL]
calls:   [0xBFC2]
called_by: [0x8371, 0x8E1A, 0x90BF]
tags: [base, gamestate, entity, encounter]
sprint: "0029"
---

# dec_encounter_a

## Summary

Decrements the base-encounter accumulator at 0xE12E (if non-zero), then sets
`spawn_ctrl` (0xE12D) bit 0 to request a spawn-table recompute. Called by
`handler_type80_base_damage` (0x8E1A) among others — base hits reduce the
encounter count.

```
BFB3  LD HL, 0xE12E
BFB6  CALL 0xBFC2        ; dec (HL) if > 0
BFB9  LD HL, 0xE12D
BFBC  SET 0, (HL)        ; request update_spawn_table_ptr
BFBE  RET
```

Counterpart: [[inc_encounter_a]]. See [[dec_encounter_b]] for the 0xE130 form.
