---
address: 0x85ee
end: 0x8634
kind: routine
name: handler_type45_light_bar_var
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x850b, 0x4898, 0x44a6]
called_by: [0x445f]
tags: [entity, enemy, light-bar]
sprint: "0051"
---

# handler_type45_light_bar_var

**Type 45** — light_bar variant. Inits via the burst-fragment init sub (0x850b:
bflags Y+X + dir from `+0x1a` via 0x4cf7), with a random homing-iteration count,
3 hit points, and a periodic re-aim timer (+0x1c = 0x28). On each timeout it
re-derives a direction from `+0x1a` plus a random bit. The active body manages
the sprite (observed sat=0x20 / colour 0x8f live).

```
85ee  BIT 7,(IX+0x00) / JR NZ,0x8608
85f4  LD A,R / AND 0x01 / ADD A,0x02 / LD (IX+0x17),A  ; homing iters 2 or 3
85fd  CALL 0x850b                                       ; burst-fragment init body
8600  LD (IX+0x19),0x03                                  ; 3 HP
8604  LD (IX+0x1c),0x28                                   ; re-aim timer = 40
; active (0x8608):
8608  DEC (IX+0x1c) / JR NZ,0x8625
860d  LD A,R / BIT 0,A / JR Z,reload                      ; reload timer
8613  AND 0x08 / ADD A,(IX+0x1a) …                         ; new direction from +0x1a + random
```

## Related

[[handler_type38_burst_fragment]] (0x850b init), [[handler_type21_light_bar]],
[[set_velocity_from_dir]], [[entity_jump_table]] (45).
