---
address: 0xBFCB
end: 0xBFD5
kind: routine
name: inc_encounter_inner
confidence: confirmed
inputs:  { HL: "pointer to the counter byte (0xE12E)" }
outputs: {}
clobbers: [AF]
calls:   []
called_by: [0xBFAB]
tags: [base, gamestate, encounter]
sprint: "0029"
---

# inc_encounter_inner

## Summary

Shared increment primitive for the base-encounter counter, **gated by the
boss-active flag**. If 0xE150 bit 1 is set (boss active) the increment is
skipped; otherwise `(HL)` is incremented with saturation at 0xFF. Falls into the
shared HUD-display tail at 0xBFD6.

```
BFCB  LD A, (0xE150)
BFCE  BIT 1, A
BFD0  JR NZ, 0xBFD6     ; boss active: don't increment
BFD2  INC (HL)
BFD3  JR NZ, 0xBFD6     ; no wrap: go update display
BFD5  DEC (HL)          ; wrapped 0xFF→0x00: saturate back to 0xFF, then display
```

Decrement form: [[dec_encounter_inner]]. The 0xBFD6 tail refreshes the
base-encounter HUD readout (see `base_encounter_ctrl.md`).
