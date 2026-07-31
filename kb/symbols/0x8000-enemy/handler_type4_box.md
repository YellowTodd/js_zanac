---
address: 0x7826
end: 0x78ae
kind: routine
name: handler_type4_box
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x71da, 0x4898, 0x71f6, 0x44ba, 0x7904, 0x4496, 0x8ddb]
called_by: [0x445f]
tags: [entity, enemy, box]
sprint: "0049"
---

# handler_type4_box

## Summary

Shared handler for **types 4, 5, 6** — the *box enemy*. The box descends slowly
disguised, runs a countdown stored in its sat_name field (+0x03), and when the
countdown hits zero it reveals its real sprite (pattern 0xD4) and spawns a
column marker. On destruction it spawns child fragments. Type 68 (`proto-box`,
0x77a1) converts itself into a type-4 box during init.

Handler entry is `BIT 7,(IX+0x00)` (`DD CB 00 7E`) at 0x7826; the bytes
immediately before are [[proto_box_sat_table]] (0x7808–0x7825), now a labelled
`DB` block in source (sprint 0053).

## Decode (0x7826)

```
7826  BIT 7,(IX+0x00)        ; initialised?
782a  JR NZ, 0x784d          ; yes → active path
; --- init: countdown not yet expired ---
782c  DEC (IX+0x03)          ; sat_name doubles as countdown
782f  RET NZ                 ; still counting → stay disguised
7830  CALL 0x71da            ; spawn_col_marker
7833  LD (HL), 0xd8          ; col-marker sat_name = 0xD8 (pat 54 = box complement)
7835  LD (IX+0x19), 0x05     ; hit-points / health = 5
7839  LD (IX+0x03), 0xd4     ; reveal real pattern 0xD4
783d  LD (IX+0x04), 0x8f     ; color = white
7841  LD (IX+0x08), 0xc0     ; vy_frac = 0xC0 (slow descent)
7845  LD (IX+0x0c), 0x01     ; bflags = Y-motion only
7849  SET 7,(IX+0x00)        ; activate
; --- active path (also entered directly while disguised) ---
784d  CALL 0x4898            ; entity_update (motion/anim)
7850  CALL 0x71f6            ; spawn-child / column helper
7853  BIT 7,(IX+0x00)
7857  RET Z                  ; despawned mid-update
7858  CALL 0x44ba            ; entity_post (SAT push + collision)
785b  CALL 0x7904            ; hit/health sub (returns Z if killed)
785e  JR Z, 0x7878           ; killed → death/fragment branch
; survived a hit: tint by remaining health (+0x19) at 0x7860–0x7877
7878  …                      ; death branch: at +0x18==5 RET; ==4 convert to type 0x26
                             ; else set pattern 0x04 + type 0xBF (explosion remap)
```

The death branch (0x7878–0x78ad) is the **item-drop table** (subsystem
[[H-items-and-pickups]]). `+0x18` holds the box's own type (saved by
`collision_response` on the first hit), so the box *type* selects the drop:

| box type | +0x18 | death branch | drop |
|----------|-------|--------------|------|
| 5 | 5 | RET (0x787d) | **nothing** |
| 4 | 4 | type→0x26 + 2 more (0x788f) | **three bullets** (type 38) |
| 6 | 6 | type→0xBF, pattern 0x04 (0x788a) | **power chip** ([[handler_type63_power_chip]] type 63) |

Confirmed live (sprint 0054): driving 0x7878 with +0x18 ∈ {4,5,6} yields entity
type {0x26, 0x84-unchanged, 0xBF}. The box-type distribution (hence drop odds) is
set at spawn by [[proto_box_type_table]] / [[handler_type68_proto_box]].

## Sub at 0x7904 (hit / health countdown)

```
7904  BIT 7,(IX+0x00) / POP HL / RET NZ   ; (pops return addr — tail-adjusts caller)
790b  DEC (IX+0x19)        ; health--
790e  RET Z                ; reached 0 → killed (Z)
790f  LD A,0x14 / CALL 0x5189   ; play hit SFX #0x14
7914  LD A,(IX+0x18) / OR 0x80 / LD (IX+0x00),A  ; remap type via +0x18
```

## Fields

| Field | Value | Meaning |
|-------|-------|---------|
| +0x03 sat_name | countdown → 0xD4 | disguised countdown; reveals pattern 0xD4 (box) |
| +0x04 color | 0x8F | white |
| +0x08 vy_frac | 0xC0 | slow descent |
| +0x0c bflags | 0x01 | Y-motion only |
| +0x19 | 0x05 | health (hits to kill) |
| +0x18 | type seed | feeds death-remap (`OR 0x80`) and fragment spawn |

Types 4/5/6 differ only in the initial countdown value (set by their spawner /
proto-box init): short / medium / long disguise — confirmed in
[[entity_jump_table]].

## Source note

[[proto_box_sat_table]] (0x7808–0x7825) sits before this handler. Its decode
formerly absorbed the leading `DD` of 0x7826 (mis-rendering this entry); sprint
0053 converted the table to a `DB` block via `redisasm data` and restored the
`BIT 7,(IX+0x00)` entry. ROM byte-identical. See [[db-sections-with-code]].

## Related

[[spawn_col_marker]] (0x71da), [[entity_update]] (0x4898), [[entity_post]]
(0x44ba), [[handler_type7_umber]], [[entity_jump_table]].
