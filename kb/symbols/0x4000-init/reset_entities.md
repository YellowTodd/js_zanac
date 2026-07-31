---
address: 0x40BA
end: 0x40D9
kind: routine
name: reset_entities
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, B, DE, IX]
calls: []
called_by: [0x40DA]
tags: [entity, level-transition, fade-out]
sprint: "0034"
---

# reset_entities  (SUB_40BA)

## Summary
Marks all non-player entities for fade-out at the start of a level transition,
and clears the encounter/scroll-mode flags `E150` and `E132`.

## Analysis
Source lines 105–120.
```
LD IX,0xE3A0           ; slot **5** (0xE300 + 5*0x20); slots 0-4 skipped
LD B,0x15              ; 21 slots
LD DE,0x0020           ; 32-byte stride
loop (LAB_40C3):
    LD A,(IX+0) ; AND 0x7F           ; active flag (high bit = facing/dir)
    JR Z,LAB_40CE                    ; empty slot -> skip
    LD (IX+0),0x28                   ; -> entity type 0x28 (fade-out)
LAB_40CE:
    ADD IX,DE ; DJNZ loop
SUB A
LD (0xE150),A          ; clear base_encounter_flags
LD (0xE132),A          ; clear scroll-mode / spawn-pos-hi
RET
```

## Entity type 0x28
Live non-player entities are re-typed to **0x28** rather than zeroed, so their
handler can run a despawn/fade for one or more frames before the slot frees.
`explode_enemies` (0x8A26) explicitly **excludes** type 0x28 when converting
enemies to explosions (type 0x23), confirming 0x28 is a transient
"leaving / fade-out" type. (Handler not yet traced → `hypothesis` on the exact
animation.)

## Slot range corrected (2026-07-30)

`LD IX,0xE3A0` is `0xE300 + 5 x 0x20` = **slot 5**, and `B = 0x15` covers 21
slots, so the sweep is **slots 5-25**. It deliberately spares slots **0-4**:
the player ship, its three shot slots and the fire-weapon slot. An earlier note
here called 0xE3A0 "slot 1"; a port following that would wipe the player's
live shots on every round transition.

Type **0x28** is also not a fade. Its jump-table entry (`entity_jump_table`,
confirmed) is 0x852C = `JP entity_clear`, so the slot is zeroed on the very
next `entity_dispatch` pass - which is exactly why
[[level_complete_handler]] calls `entity_dispatch` explicitly at 0x40F2.
