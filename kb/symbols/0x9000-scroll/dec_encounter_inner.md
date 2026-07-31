---
address: 0xBFC2
end: 0xBFC7
kind: routine
name: dec_encounter_inner
confidence: confirmed
inputs:  { HL: "pointer to the counter byte (0xE12E or 0xE130)" }
outputs: {}
clobbers: [AF]
calls:   []
called_by: [0xBFB3, 0xBFBF]
tags: [base, gamestate, encounter]
sprint: "0029"
---

# dec_encounter_inner

## Summary

Shared decrement primitive for the base-encounter counters. Decrements `(HL)`
only if it is non-zero, then falls into the shared HUD-display tail at 0xBFD6.

```
BFC2  LD A, (HL)
BFC3  AND A
BFC4  JR Z, 0xBFD6      ; already 0: skip, go update display
BFC6  JR 0xBFD5         ; else DEC (HL), then display tail
```

The 0xBFD6 tail (`LD HL,0x3839; CALL 0x5C25; …`) writes the counter values to
the VRAM name table via WRTVRM — the base-encounter HUD readout. See
`kb/symbols/0x9000-scroll/base_encounter_ctrl.md`. Increment form:
[[inc_encounter_inner]].
