---
address: 0x852f
end: 0x85cb
kind: routine
name: handler_type41_pair_fragment
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x4cf7, 0x4898, 0x44a6]
called_by: [0x445f]
tags: [entity, enemy, fragment]
sprint: "0051"
---

# handler_type41_pair_fragment

**Type 41** — curving fragment. Inits like a burst fragment (pattern 7, bflags
Y+X) but holds **two directions** in +0x1a (low nibble) and +0x1b (nibble ±4),
and oscillates between them on a +0x15 timer so the path curves. Spawned in pairs
by the type-8 umber.

```
852f  BIT 7,(IX+0x00) / JR NZ,0x857f
8535  LD (IX+0x03),0x1c / LD (IX+0x04),0x8f / LD (IX+0x17),0x02 / LD (IX+0x0c),0x03
8545  LD A,(IX+0x1a) / AND 0x0f / LD E,A          ; dir 0 = param & 0x0F
854b  BIT 4,(IX+0x1a) / JR Z / ADD A,0xfc | ADD A,0x04 / AND 0x0f / LD (IX+0x1b),A  ; dir 1 = dir0 ±4
855c  CALL 0x4cf7                                  ; set initial velocity (dir 0)
855f  (LDIR copy +0x08..0x0b velocity snapshot → +0x1c..)
8572  SET 7,(IX+0x00) / LD (IX+0x15),0x02 / LD (IX+0x17),0x04
; active (0x857f): DEC (IX+0x15); on 0 reload 2 and swap to the other dir → curve
```

## Related

[[handler_type38_burst_fragment]], [[set_velocity_from_dir]],
[[umber_burst_param_table]], [[entity_jump_table]] (41).
