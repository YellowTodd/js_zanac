---
address: 0x43C0
end: 0x43D1
kind: routine
name: prng_next
confidence: likely
inputs: {}
outputs:
  HL: new 16-bit PRNG state (also stored at 0xE12B)
clobbers: [AF, HL]
calls: []
called_by: [0x71C5, 0x83A5, 0x8686]
tags: [util, random]
sprint: "0040"
---

# prng_next

## Summary

Advance the 16-bit pseudo-random state at `prng_state` (0xE12B), seeding entropy
from the Z80 `R` (memory-refresh) register, and return the new state in `HL`.
Called from the spawn/enemy code (0x71C5, 0x83A5, 0x8686) — i.e. it drives
spawn/wave randomisation ([[G-enemy-and-spawn-system]], and likely
[[I-alc-adaptive-difficulty]]). DB block decoded in sprint 0040.

## Analysis (source 0x43C0–0x43D1)

```
43C0  LD A,R             ; A = refresh register (changes each instruction → entropy)
43C2  LD HL,(0xE12B)     ; HL = current prng_state
43C5  ADD A,H; LD H,A    ; mix R into H
43C7  ADD A,L; LD L,H; LD H,A  ; cross-mix into L and H
43CA  RLC H              ; rotate H left
43CC  RRC L              ; rotate L right
43CE  LD (0xE12B),HL     ; store new state
43D1  RET
```

## Notes

The same algorithm is recorded from the data side in `prng_state` (0xE12B). The
`R`-register seed means the sequence depends on instruction timing/count since
boot, so it is not reproducible across runs. ROM byte-identical after the
redisasm patch. See [[prng-state]].
