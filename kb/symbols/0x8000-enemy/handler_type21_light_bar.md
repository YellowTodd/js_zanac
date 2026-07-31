---
address: 0x8635
end: 0x8667
kind: routine
name: handler_type21_light_bar
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x4cf7, 0x4898, 0x44ba, 0x5189]
called_by: [0x445f]
tags: [entity, enemy, light-bar]
sprint: "0050"
---

# handler_type21_light_bar

**Type 21** — `light_bar`. Fires off in a fixed direction (from its `+0x1a`
spawn param) and flickers colour every frame. Pattern 0x18 (pat 6).

```
8635  BIT 7,(IX+0x00) / JR NZ,0x8659         ; active → flicker + update
863b  LD (IX+0x17),0x04
863f  LD (IX+0x03),0x18                         ; pattern 6
8643  LD A,(IX+0x1a) / AND 0x0f / LD E,A         ; direction = spawn param & 0x0F
8649  CALL 0x4cf7                                 ; set_velocity_from_dir(E)
864c  LD (IX+0x0c),0x03                            ; bflags = Y + X motion
8650  SET 7,(IX+0x00)
8654  LD A,0x16 / JP 0x5189                         ; play SFX #0x16 (tail-call)
; active (0x8659):
8659  LD A,R / AND 0x0f / OR 0x80 / LD (IX+0x04),A  ; colour = random (flicker)
8662  CALL 0x4898 / JP 0x44ba
```

Direction comes from `+0x1a`, the same per-spawn param used by
[[umber_burst_param_table]] / [[handler_type38_burst_fragment]] — light_bar is
one of the things bases/fragments emit.

## Related

[[set_velocity_from_dir]], [[entity_jump_table]].
