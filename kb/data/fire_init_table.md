---
address: 0x751f
end: 0x752e
kind: data
name: fire_init_table
confidence: confirmed
sprint: "0048"
tags: [fire, weapon, ammo, table]
---

# fire_init_table

## Summary

8-entry table (2 bytes each, indexed by `fire_num` 0-7) read by [[fire_select]]
(0x7548) when a fire weapon is chosen. Byte 0 → **E14D** (the weapon's
ammo/time/durability counter shown by [[update_fire_display]]); byte 1 → **E14E**
(per-weapon mode/secondary count).

## Layout

| fire_num | E14D (0x751f+2n) | E14E |
|----------|------|------|
| 0 | 0x00 | 0x02 |
| 1 | 0x64 (100) | 0x03 |
| 2 | 0x64 (100) | 0x01 |
| 3 | 0xc8 (200) | 0x01 |
| 4 | 0x1e (30) | 0x01 |
| 5 | 0x64 (100) | 0x03 |
| 6 | 0x0f (15) | 0x03 |
| 7 | 0xfa (250) | 0x03 |

Followed immediately by [[fire2_special_table]] (0x752f).

## Confirmed (sprint 0048)

`fire_select(fire_num=n)` set E14D/E14E to `fire_init_table[n]` for all 8 values
(and E14C=0x3c, E14B=n). `tools/sprint0048_verify.py`.
