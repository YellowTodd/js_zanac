---
address: 0x81d1
end: 0x8268
kind: routine
name: handler_type57_paired_descender
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71da, 0x71c5, 0x5189, 0x4c91, 0x4898, 0x44ba]
called_by: [0x445f]
tags: [entity, enemy, descender, paired]
sprint: "0051"
---

# handler_type57_paired_descender

**Types 57 and 58** — descending projectiles that track one (57) or two (58)
column-marker children. Both join the [[handler_type56_sig_single]] init tail
(0x81ac) and have their own active body at 0x81e6. After a countdown (+0x1f) they
fire: play SFX 0x15, snapshot the player, and convert into type 0x3b (=59,
sideways) while seeding child slots.

| Type | Entry | Sprite | Children |
|------|-------|--------|----------|
| 57 | 0x81d1 | 0x6c (pat 27) | 1 col-marker |
| 58 | 0x8247 | 0x68 (pat 26) | 2 col-markers (+0x1d/1e = second) |

```
; type 57 (0x81d1):
81d1  BIT 7,(IX+0x00) / JR NZ,0x81e6
81d7  CALL 0x71da / CALL 0x71c5         ; col-marker + random X
81dd  LD (IX+0x03),0x6c / LD E,0x04 / JP 0x81ac  ; → sig init tail
; type 58 (0x8247): two 0x71da calls (second marker → +0x1d/1e), sprite 0x68, JP 0x81ac
; active (0x81e6):
81e6  (set both children's +0x18 = 0x02)
8202  DEC (IX+0x1f) / JR NZ,0x81c3      ; countdown → plain flicker/update
8207  LD A,0x15 / CALL 0x5189            ; fire SFX
820c  CALL 0x4c91                         ; player snapshot → E = aim
8210  LD (IX+0x00),0x3b                    ; convert self to type 59 (sideways)
8215  LD (IX+0x1a),E-1                      ; store aim dir for the type-59 run
8218  … write type 0x3b + Y/X into child slots (+0x1b/1c and, for 58, +0x1d/1e)
```

## Related

[[handler_type56_sig_single]] (shared init tail / active / the type-59 it becomes),
[[player_pos_snapshot]], [[spawn_col_marker]], [[entity_jump_table]] (57, 58).
