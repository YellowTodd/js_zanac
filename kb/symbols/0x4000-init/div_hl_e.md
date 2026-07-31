---
address: 0x4329
end: 0x4342
kind: routine
name: div_hl_e
confidence: likely
inputs:
  HL: 16-bit dividend
  E: 8-bit divisor
outputs:
  L: quotient HL / E, rounded to nearest
clobbers: [AF, B, H, L]
calls: []
called_by: [0x4CDB]
tags: [util, math]
sprint: "0040"
---

# div_hl_e

## Summary

Unsigned 16÷8 division `HL / E`, returning the **round-to-nearest** quotient in
`L` (assumes the quotient fits in 8 bits). Restoring division over 8 iterations,
followed by a rounding adjust. Called by the player vertical-collision-distance
code at 0x4CDB (see [[C-entity-framework]] / `player_pos_snapshot`). DB block
decoded in sprint 0040 (previously raw bytes at 0x4329).

## Analysis (source 0x4329–0x4342)

```
4329  LD B,0x08
432B  XOR A
432C  ADC HL,HL          ; shift dividend left, quotient bit enters L bit0 next round
432E  LD A,H
432F  JR C,0x4334        ; overflow → must subtract
4331  CP E
4332  JR C,0x4337        ; H < E → no subtract (quotient bit 0)
4334  SUB E              ; H -= E
4335  LD H,A
4336  XOR A              ; (carry=0)
4337  CCF                ; quotient bit = !(H<E)
4338  DJNZ 0x432C
; --- round to nearest: if 2*remainder >= E, bump quotient ---
433A  RL L               ; shift in the final quotient bit → L = quotient
433C  SLA H              ; remainder *= 2
433E  LD A,H
433F  SUB E              ; 2*remainder - E
4340  RET C              ; < 0 → no rounding (L = floor quotient)
4341  INC L              ; round up
4342  RET
```

## Notes

`H` holds the running remainder during the loop; after `RL L` completes the
8-bit quotient, the tail rounds half-up. Behaviour follows directly from the
decoded instructions; ROM byte-identical after the redisasm patch. The preceding
routine `mul_a_e` (0x4317) is the multiply companion.
