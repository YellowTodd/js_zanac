---
address: 0x48D0
end: 0x48DD
kind: routine
name: entity_clear
confidence: confirmed
inputs:  { IX: "entity slot base address" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   []
called_by: [0x8525, 0x852C]
tags: [entity, dispatch]
sprint: "0012"
---

# entity_clear

## Summary

Zeroes the entire 32-byte entity slot at IX, setting type byte to 0 (inactive)
and clearing all state. The entity is effectively despawned.

## Analysis

```
48D0  PUSH IX            ; HL = IX (entity slot address)
48D2  POP HL
48D3  LD (HL), 0x00      ; slot[0] = 0 (type = inactive)
48D5  LD E, L
48D6  LD D, H            ; DE = slot address
48D7  LD BC, 0x0017      ; BC = 23
48DA  INC DE             ; DE = slot + 1
48DB  LDIR               ; copy slot[0..22] to slot[1..23]
                         ; since slot[0]=0, propagates zero fill
48DD  RET
```

The LDIR trick: source HL = slot, dest DE = slot+1. Each step copies the
just-zeroed byte one position forward, filling all 32 bytes with 0 in
23 iterations (the first byte was already zeroed by the explicit write).

## Verification

Disassembled live from openMSX (sprint 0012). Pattern matches the type-39
handler which calls this when its countdown timer expires.
