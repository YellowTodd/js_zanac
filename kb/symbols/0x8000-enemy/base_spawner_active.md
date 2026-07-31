---
address: 0x7a67
end: 0x7ad3
kind: routine
name: base_spawner_active
confidence: confirmed
inputs:  { IX: "entity slot (type 69)" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x71c5, 0x4496, 0x8ddb, 0x48d0]
called_by: [0x445f, 0x7ad4]
tags: [entity, enemy, spawner, base]
sprint: "0049"
---

# base_spawner_active

Active/running state of the base projectile spawner — **type 69** (0x45),
entered by `handler_type11_base_spawner` (0x7ad4) via `JP 0x7a67` after type 11
remaps itself to type 69. This is the `LAB_7A67` target of open sprint **0039**.

## Init (first call, BIT 7 clear)

Type 11 has already written: +0x01 = enemy_type, +0x02 = count (from
`base_spawner_spawn_table` 0x7af7, selected by `data_e130 >> 3 & 0x0e`),
+0x03 = 0x28 (fire-interval reload).

```
7a6d  LD A,(IX+0x01) / LD (IX+0x18),A    ; +0x18 = enemy type to emit
7a73  LD A,(IX+0x02) / LD (IX+0x19),A    ; +0x19 = remaining count (ammo)
7a79  LD A,(IX+0x03) / LD (IX+0x1c),A / LD (IX+0x1b),A  ; +0x1b/1c = fire interval + reload
7a82  CALL 0x71c5                        ; random_x_pos → +0x02
7a85  LD A,(IX+0x02) / CP 0x78           ; spawned left or right of centre?
7a8a  LD DE,0x0203 / JR C,0x7a92 / LD DE,0xfe05  ; left→(+2,3)  right→(−2,5)
7a92  LD (IX+0x0a),D / LD (IX+0x1a),E     ; +0x0a = X drift velocity; +0x1a = spawn param
7a98  SET 7,(IX+0x00)
```

## Active (BIT 7 set, 0x7a9c)

```
7a9c  LD A,(0xe12d) / BIT 3,A / RET NZ   ; gated: skip while game-state E12D bit3 set
7aa2  DEC (IX+0x1b) / RET NZ             ; fire-interval countdown
7aa6  LD A,(IX+0x1c) / LD (IX+0x1b),A     ; reload interval
7aac  CALL 0x4496 / RET C                 ; find_free_slot (abort if pool full)
7ab0  LD C,(IX+0x1a) / LD A,(IX+0x18)      ; A = enemy type, C = spawn param
7ab6  CALL 0x8ddb                          ; spawn_entity (child = +0x18 type)
7ab9  DEC (IX+0x19) / JP Z,0x48d0          ; count-- ; 0 → entity_clear (retire base)
7abf  LD A,(IX+0x02) / ADD A,(IX+0x0a) / LD (IX+0x02),A  ; walk X by drift
7ac8  CP 0xc0 / RET C                      ; past right edge?
7acb  LD A,(IX+0x0a) / CPL / INC A / LD (IX+0x0a),A / RET  ; negate drift (bounce)
```

So a base, once opened, emits **`count` copies of `enemy_type`** one per fire
interval, walking back and forth horizontally and bouncing at X≥0xC0, then
self-destructs (`entity_clear`). The (type,count) menu is
[[base_spawner_spawn_table]].

## Related

[[handler_type11_base_spawner]] (0x7ad4, the init that selects the table entry),
[[base_spawner_spawn_table]] (0x7af7), [[spawn_entity]] (0x8ddb),
[[random_x_pos]] (0x71c5). Closes sprint 0039 part 1.
