---
address: 0x7548
end: 0x7593
kind: routine
name: fire_select
confidence: confirmed
inputs:  { A: "new fire_num 0-7" }
outputs: { "(E14B)": "fire_num", "(E14C)": "0x3c timer reload", "(E14D/E14E)": "from fire_init_table" }
clobbers: [AF, BC, DE, HL]
calls: [0x97bc, 0x7594]
called_by: [0x7544, 0x75ff, 0x731e, 0x74a1, 0x74cd, 0x750b, 0x749c]
sprint: "0048"
tags: [fire, weapon, select, switch]
---

# fire_select

## Summary

Switches the active fire weapon to `A` (0-7). Stores the old `fire_num` (E14B)
in D, writes the new one, loads the weapon's counters from [[fire_init_table]]
(0x751f) into **E14D**/**E14E**, primes the life-timer reload **E14C = 0x3c**,
and refreshes the HUD via [[update_fire_display]] (0x7594). Entered from
[[fire_reset]] (0x7544) with A=0 to drop back to the bare weapon.

## Analysis (0x7548–0x7593)

```
LD E,A; LD HL,0xe14b; LD D,(HL); LD (HL),A   ; E=new, D=old, store fire_num
ADD A,A; LD C,A; LD B,0; LD HL,0x751f; ADD HL,BC   ; -> fire_init_table[A*2]
LD A,0x3c; LD (0xe14c),A                      ; timer reload
LD A,(HL); LD (0xe14d),A; INC HL; LD A,(HL); LD (0xe14e),A
; --- the fire slot is re-typed here (0x7564-0x7573) ---
LD A,E; CP 2; JR NZ,0x756c
  INC A                      ; A = 3, and always - no old/new comparison
  JR 0x7571
0x756c: CP D; JR Z,0x7574    ; same weapon as before -> leave the slot alone
  LD A,0x28                  ; different weapon -> despawn what is in there
0x7571: LD (0xe380),A
; --- fire 2 also summons a wave ---
A==2 ? read E10B, HL=0x752f + E10B*3 (+3 if E701>=5), CALL 0x97bc  ; fire2_special_table
fall through to update_fire_display (0x7594)
```

`E380` is the fire-control entity slot byte (see [[player_ship_update]], which
sets E380=3 when the fire key spawns the weapon). The A==2 branch reads
[[fire2_special_table]] (0x752f).

**The 0x7564 tail is what disposes of the outgoing weapon**, and it is easy to
read as nothing but a fire-2 special case. Three distinct outcomes:

- **new == 2**: `E380 := 3` unconditionally. The following shield arms itself
  the moment the weapon is picked up, without the fire key - and re-selecting
  fire 2 re-arms it, because the `CP D` test sits on the *other* branch.
- **new != 2 and new != old**: `E380 := 0x28`, the no-animation despawn
  (handler 0x852C = `JP entity_clear`). This is the only thing that retires
  the previous weapon's entity.
- **new == old**: the slot is untouched, so a refresh does not restart a
  running weapon.

Missing the middle case wedges the slot permanently, because
[[spawn_fire_weapon]] (0x76E9) only spawns into a **free** slot - see
correction 75 in [[port-corrections]].

## Confirmed (sprint 0048)

For each `fire_num` 0-7, calling 0x7548 set E14B=n, E14C=0x3c, and E14D/E14E to
`fire_init_table[n]` exactly (e.g. fire 3 → E14D=0xc8 E14E=0x01).
`tools/sprint0048_verify.py`.
