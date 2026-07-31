---
address: 0xE12B
kind: data
name: prng_state
confidence: likely
sprint: "0027"
tags: [gamestate, random]
---

# prng_state (0xE12B:0xE12C)

16-bit PRNG state. Updated by the code block at 0x43C0 (embedded in a DB
section, decoded as Z80):

```z80
; 0x43C0
LD  A, R              ; A = refresh register (pseudo-random)
LD  HL, (0xE12B)      ; load 16-bit state
ADD A, H              ; mix R into H
LD  H, A
ADD A, L              ; mix into L
LD  L, H
LD  H, A
RLC H                 ; rotate H left
RRC L                 ; rotate L right
LD  (0xE12B), HL      ; store back
RET
```

`LD (0xE12B), HL` writes L → 0xE12B (lo) and H → 0xE12C (hi).
Both bytes have PC=0x43CE when the watchpoint fires (same instruction).
The Z80 R register provides real entropy since it increments on every
instruction fetch.

Observed values during gameplay vary widely; treated as effectively random.
