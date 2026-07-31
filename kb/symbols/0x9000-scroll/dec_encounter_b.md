---
address: 0xBFBF
end: 0xBFC1
kind: routine
name: dec_encounter_b
confidence: confirmed
inputs:  {}
outputs: {}
clobbers: [AF, HL]
calls:   [0xBFC2]
called_by: [0x9329]
tags: [base, gamestate, encounter]
sprint: "0029"
---

# dec_encounter_b

## Summary

Decrements the second base-encounter counter at 0xE130, by loading its address
and falling into the shared decrement helper [[dec_encounter_inner]] (0xBFC2).

```
BFBF  LD HL, 0xE130
BFC2  ; fall into dec_encounter_inner
```

Counterpart of [[dec_encounter_a]] (which operates on 0xE12E).
