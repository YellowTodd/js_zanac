---
address: 0x8e3a
end: 0x8eae
kind: routine
name: handler_type83_black_shadow
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x4898, 0x44b0, 0x48d0, 0xbfc8, 0x7548]
called_by: [0x445f]
tags: [entity, enemy, base, shadow]
sprint: "0052"
---

# handler_type83_black_shadow

**Type 83** — black shadow base entity. Rises slowly (vy≈-0.12), flickers between
a solid tile (pattern 0x24, colour 0x81 black) and an invisible/coloured frame
on a 4-frame cycle, with its accent colour drawn from
[[large_descender_color_table]] (0x8eaf) by +0x1c. **On destruction it
reinitialises the player slot** (0xe300 type 0x81 + invincibility), deducts 5
from a counter (0xe148), clears itself, signals the encounter (0xbfc8), and jumps
into the fire-weapon switcher (0x7548) with A = +0x1c — i.e. it is tied to the
player respawn / base-clear path.

```
8e3a  BIT 7 / JR NZ,0x8e5d
8e40  LD (IX+0x0c),0x01 / (IX+0x09),0xff / (IX+0x08),0xe0  ; rise
8e4c  LD (IX+0x00),0xd3                                     ; type_flags = 0x80|83
8e50  +0x1d = large_descender_color_table[+0x1c]
; active (0x8e5d): +0x1b++ & 3 → frame 0 = pattern 0x24/col 0x81, else pattern 0x04/col +0x1d
8e79  CALL 0x4898 / BIT 7 / RET Z / CALL 0x44b0 / BIT 7 / RET NZ
; destroyed:
8e89  IY=0xe300; (IY+0)=0x81; (IY+0x1b)=0; e148 -= 5 (floor 0); SET 7,(IY+5) (invincible)
8ea3  CALL 0x48d0 (clear) / CALL 0xbfc8 / LD A,(IX+0x1c) / JP 0x7548
```

## Item role — fire-weapon upgrade

This is the **floating fire-weapon upgrade** of subsystem [[H-items-and-pickups]]:
the `JP 0x7548` on death calls [[fire_select]] with `A = +0x1c`, switching the
player's fire weapon to that number (0–7). `+0x1c` is set at spawn and doubles as
the colour-table index ([[large_descender_color_table]]) and the granted weapon.
Confirmed live (sprint 0054): driving the 0x8ea9 tail with `+0x1c=5` enters
`fire_select` with `A=5`.

## Related

[[large_descender_color_table]] (0x8eaf), [[handler_type72_base_core]],
[[fire_select]] (0x7548), [[H-items-and-pickups]], [[entity_jump_table]] (83).
