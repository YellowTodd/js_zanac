---
address: 0x4317
end: 0x4328
kind: routine
name: mul_a_e
confidence: likely
inputs:
  A: 8-bit multiplier
  E: 8-bit multiplicand
outputs:
  HL: A * E (16-bit product)
clobbers: [AF, B, D, E, HL]
calls: []
called_by: []
tags: [util, math]
sprint: "0040"
---

# mul_a_e

## Summary

Unsigned 8×8→16 multiply, `HL = A × E`. Standard shift-and-add: for each of the
8 bits of `A`, conditionally add the running multiplicand `DE` into `HL`, then
double `DE`. Lives in a DB block decoded in sprint 0040 (previously raw bytes at
0x4317).

## Analysis (source 0x4317–0x4328)

```
4317  LD B,0x08          ; 8 bits
4319  LD HL,0x0000       ; product = 0
431C  LD D,L             ; D = 0  → DE = (0:E) = multiplicand
431D  RR A               ; shift next multiplier bit into carry
431F  JR NC,0x4322       ; bit clear → skip add
4321  ADD HL,DE          ; product += current multiplicand
4322  SLA E              ; DE <<= 1
4324  RL D
4326  DJNZ 0x431D
4328  RET
```

## Notes

No direct caller is currently referenced in the disassembly (reached only via a
computed/indirect call, or presently unused). The companion routine `div_hl_e`
(0x4329) immediately follows. Behaviour follows directly from the decoded
instructions; ROM byte-identical after the redisasm patch.
