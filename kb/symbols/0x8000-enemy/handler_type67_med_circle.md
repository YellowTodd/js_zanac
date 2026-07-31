---
address: 0x839f
end: 0x8445
kind: routine
name: handler_type67_med_circle
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x43c0, 0x48b8]
called_by: [0x445f]
tags: [entity, enemy, med-circle]
sprint: "0051"
---

# handler_type67_med_circle

**Type 67** — med_circle. Spawns at a random position (prng), morphs/flickers
sprite + colour each frame, and runs a lifetime countdown stored as a 16-bit
value in +0x1b/+0x1c (0x1e78). Pattern 0x20 (pat 8), colour 0x86. 5 hit points.

> Correction: sprint-0013 / entity_jump_table called +0x1b/1c a "child_ptr
> (0x1e5e, not a valid slot)". It is **not a pointer** — it is the 16-bit
> lifetime countdown 0x1e78 (low=0x78 @+0x1b, high=0x1e @+0x1c).

```
839f  BIT 7,(IX+0x00) / JR NZ,0x83d8
83a5  CALL 0x43c0                          ; prng_next → HL
83a8  LD A,L / AND 0x7f / ADD A,0x10 / LD (IX+0x01),A  ; Y = 0x10..0x8f
83b0  LD A,H / AND 0x7f / ADD A,0x40 / LD (IX+0x02),A  ; X = 0x40..0xbf
83b8  LD (IX+0x04),0x86 / LD (IX+0x03),0x20 ; colour, pattern 8
83c0  LD (IX+0x0c),0x03 / LD (IX+0x19),0x05 ; bflags Y+X, 5 HP
83c8  LD (IX+0x17),0x03
83cc  LD (IX+0x1b),0x78 / LD (IX+0x1c),0x1e ; lifetime = 0x1e78
83d4  SET 7,(IX+0x00)
; active (0x83d8):
83d8  XOR (IX+0x03) with 0x34 ; XOR (IX+0x04) with 0x0c  ; sprite + colour morph
83e8  DEC (IX+0x1b) / JP Z,0x83f7           ; 16-bit lifetime tick (low byte)
83ee  BIT 0,(IX+0x05) / JP Z,0x48b8         ; phase-gated entity_post
83f7  … (low byte hit 0) decrements +0x1c, sets phase bits, expires
```

## Related

[[prng_next]] (0x43c0), [[entity_jump_table]] (67).
