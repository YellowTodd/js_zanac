---
address: 0x7b07
end: 0x7b7a
kind: routine
name: handler_type12_teruzo
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71da, 0x4cf7]
called_by: [0x445f]
tags: [entity, enemy, teruzo, motion-script]
sprint: "0049"
---

# handler_type12_teruzo

## Summary

Shared handler for **types 12–15**, the *teruzo*. Each type spawns at one of the
four screen corners and follows a **direction-script** — a list of 16-direction
indices fed one-per-8-frames to [[set_velocity_from_dir]] (0x4cf7) — giving a
curving flight path. Pattern 0x60 (pat 24). The script + spawn point come from
[[teruzo_motion_tables]].

## Decode (init, 0x7b07)

```
7b07  BIT 7,(IX+0x00) / JR NZ,0x7b55       ; active → script step
7b0d  LD DE,0x7b63                         ; teruzo_motion_tables virtual base
7b10  LD A,(IX+0x00) / AND 0xfe            ; type (12/13→12, 14/15→14)
7b15  LD L,A / LD A,R / AND 0x01 / ADD A,L ; + random bit (pick 1 of 2 scripts)
7b1b  ADD A,A / LD L,A / LD H,0 / ADD HL,DE; HL = &table[(type&fe)+rnd]
7b20  LD E,(HL) / INC HL / LD D,(HL)       ; DE = script block pointer
7b23  CALL 0x71da / LD (HL),0x64           ; spawn_col_marker, complement 0x64
7b28  LD A,(DE) / INC DE / LD (IX+0x01),A  ; +0x01 = spawn Y   (block byte 0)
7b2d  LD A,(DE) / INC DE / LD (IX+0x02),A  ; +0x02 = spawn X   (block byte 1)
7b32  LD A,(DE) / INC DE / LD (IX+0x04),A  ; +0x04 = colour    (block byte 2)
7b37  LD (IX+0x0c),0x03                    ; bflags = Y + X motion
7b3b  LD (IX+0x1d),E / LD (IX+0x1e),D      ; +0x1d/1e = script cursor (→ dir bytes)
7b41  LD (IX+0x1f),0x01                    ; +0x1f = step tick (fires next frame)
7b45  LD (IX+0x18),0x00                    ; +0x18 = script index
7b49  LD (IX+0x17),0x04
7b4d  LD (IX+0x03),0x60                    ; pattern 24
7b51  SET 7,(IX+0x00)
```

## Decode (script step, 0x7b55)

```
7b55  DEC (IX+0x1f) / JP NZ,0x79ae         ; 8-frame cadence
7b5b  LD (IX+0x1f),0x08                     ; reload
7b5f  LD L,(IX+0x1d) / LD H,(IX+0x1e)       ; HL = script base
7b65  LD E,(IX+0x18) / LD D,0 / ADD HL,DE   ; + index
7b6b  LD E,(HL)                             ; E = direction byte
7b6c  BIT 7,E / RES 7,E                     ; bit7 = "final / hold" marker
7b70  JR NZ,0x7b75 / INC (IX+0x18)          ; advance index only if not final
7b75  CALL 0x4cf7                           ; set_velocity_from_dir(E)
7b78  JP 0x79ae                             ; entity_update + entity_post
```

Direction bytes are 0..15 (the 16-direction index used everywhere via 0x4cf7).
A byte with bit 7 set is the **terminal** direction: the index stops advancing
and the teruzo holds that heading for the rest of its life.

## Variants

`type & 0xFE` collapses 12↔13 and 14↔15; a per-spawn random bit then picks one
of two scripts within the pair, so the four blocks cover all four corners with a
left/right script choice. See [[teruzo_motion_tables]] for the four blocks.

## Source note

The pointer table + script blocks (0x7b7b–0x7bea, [[teruzo_motion_tables]]) and
the preceding [[base_spawner_spawn_table]] (0x7af7–0x7b06) are now labelled `DB`
blocks (sprint 0053). The base_spawner table had absorbed this handler's leading
`DD`; `redisasm data` restored the `BIT 7,(IX+0x00)` entry at 0x7b07.

## Related

[[set_velocity_from_dir]] (0x4cf7), [[teruzo_motion_tables]], [[spawn_col_marker]],
[[entity_jump_table]] (types 12–15).
