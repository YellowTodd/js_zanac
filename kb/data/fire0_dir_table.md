---
address: 0x7321
end: 0x7329
kind: data
name: fire0_dir_table
confidence: confirmed
sprint: "0048"
tags: [fire, weapon, direction, table]
---

# fire0_dir_table

> **Ownership correction (2026-07-30): this is fire 7's direction table, not
> fire 0's.** The init handlers load different tables into HL before the
> shared aim path at 0x72D4 (`E = table[IX+0x1A]`, the steering selector):
>
> - fire 0 (0x72B3): `LD HL,0x7758` — [[xvel_table]], so fire 0 launches along
>   the ship's steering direction.
> - fire 7 (0x728F): `LD HL,0x7321` — **this table**, nine entries
>   `0B 0B 0B 0C 0C 0C 0D 0D 0D` = up-left / up / up-right in
>   [[vel_dir_table]] terms: an angled upward shot picked by steering.
>
> [[fire-weapon-dispatch]]'s note "fire 0's init … using fire0_dir_table for
> spread directions" repeats the same mix-up. The name is kept pending a
> `rename_symbol` pass (`fire7_dir_table` would be right).

## Summary

9-byte direction-spread table used by fire-weapon 0's spawn path (init handler
0x72b3 → common setup 0x72bc): `LD E,(IX+0x1a); ADD HL,DE; LD E,(HL); CALL 0x4cf7`
indexes this table by the sub-shot counter (IX+0x1a) and feeds the value to
[[set_velocity_from_dir]] as the direction. Three sub-shots per direction group.

```
0x7321: 0b 0b 0b 0c 0c 0c 0d 0d 0d   ; dirs 11,11,11, 12,12,12, 13,13,13
```

Directions 0x0b–0x0d are the upward-ish fan ([[vel_dir_table]]: 11=−118/−48,
12=−128/0, 13=−118/+48), i.e. a forward spread.

## Status

Bytes ROM-exact; consumed via the confirmed [[set_velocity_from_dir]] path. Not
individually executed per fire-0 shot.
