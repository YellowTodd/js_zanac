---
address: 0x819d
end: 0x81d0
kind: routine
name: handler_type56_sig_single
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71c5, 0x4cf7, 0x4898, 0x44ba]
called_by: [0x445f, 0x8269]
tags: [entity, enemy, sig]
sprint: "0051"
---

# handler_type56_sig_single

**Type 56** (`sig_single`) and **type 59** (`sideways`) — a small projectile that
flies in a set direction and flickers colour (XOR 0x09 → 0x8f↔0x86). Pattern 0x70
(pat 28). Type 59 reuses the same init/active code with its direction taken from
the `+0x1a` spawn param instead of the fixed value 4.

```
; type 56 (0x819d):
819d  BIT 7,(IX+0x00) / JR NZ,0x81c3
81a3  CALL 0x71c5                       ; random_x_pos
81a6  LD E,0x04                          ; direction = 4
81a8  LD (IX+0x03),0x70                   ; pattern 28   (shared entry for type 59)
81ac  LD (IX+0x17),0x05 / CALL 0x4cf7      ; set_velocity_from_dir(E)
81b3  LD (IX+0x0c),0x03 / LD (IX+0x04),0x8f ; bflags Y+X, colour
81bb  LD (IX+0x1f),0x20 / SET 7,(IX+0x00)
; active (0x81c3) — shared by 56/57/58/59:
81c3  LD A,(IX+0x04) / XOR 0x09 / LD (IX+0x04),A  ; colour flicker
81cb  CALL 0x4898 / JP 0x44ba
; type 59 (0x8269): dir = (+0x1a)&0x0F, then JP 0x81a8
```

## Related

[[handler_type57_paired_descender]] (shares 0x81ac init tail + 0x81c3 active),
[[set_velocity_from_dir]], [[entity_jump_table]] (56, 59).
