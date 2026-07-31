---
address: 0xE300
end: 0xE63F
kind: data
name: entity_table
confidence: confirmed
sprint: "0021"
tags: [entity, sprite, gamestate]
---

# entity_table

## Summary
Array of 26 active entity slots (enemies, pickups, projectiles), each 32 bytes
wide. Processed each frame by `entity_dispatch` (0x445F). Handler selected via
`entity_jump_table` (0x70B7) indexed by type ID.

## Slot layout (32 bytes)

Values shown: type-1 (player) / type-39 (col-marker) / type-44 (ground struct) / type-82 (wide struct).
Observed values from live captures (sprints 0005, 0010, 0021).

| Offset | Name | T1 | T39 | T44 | T82 | Notes |
|--------|------|----|-----|-----|-----|-------|
| 0x00 | type_flags | 0x81 | 0x27 | 0xAC | 0xD2 | Bits 0–6 = type; bit 7 = active flag |
| 0x01 | y | 184 | 0 | varies | 176 | Sprite bottom-edge row; 0 = no sprite |
| 0x02 | x | 103 | 0 | varies | 192 | X pixel column |
| 0x03 | sat_name | 0x38 | 0x44 | 0x40 | 0x24 | SAT pattern byte; pattern = sat_name>>2 |
| 0x04 | sat_color | 0x8F | 0x81 | 0x83 | 0x00 | SAT color byte; T1: 0x81=invincible, 0x8F=normal |
| 0x05 | flags | 0x80 | 0 | 0 | 0 | T1 bit 7 = invincibility active (set at spawn; cleared when +0x1B hits 0) |
| 0x06 | y_frac | 0 | 0 | varies | 0 | Y sub-pixel fractional (fixed-point low byte) |
| 0x07 | x_frac | 0x98 | 0 | varies | 0 | X sub-pixel fractional |
| 0x08 | vy_frac | 0 | 0 | varies | 0 | Y velocity fractional |
| 0x09 | vy | 0 | 0 | 0 | 0 | Y velocity integer (signed; negative = upward) |
| 0x0A | vx_frac | 0x80 | 0 | varies | 0 | X velocity fractional |
| 0x0B | vx | 0x02 | 0 | 0 | 0 | X velocity integer (signed; negative = leftward) |
| 0x0C | behavior_flags | 0 | 0 | 0x03 | 0 | `entity_update` dispatch: **bit0=Y-motion, bit1=X-motion**, bit2=animate, bit3=Y-homing, bit4=X-homing |
| 0x0D | anim_tick | varies | 0 | 0 | 0 | Animation tick countdown; decrements each frame, reloads from +0x0E (used when bit2 set) |
| 0x0E | anim_rate | varies | 0 | 0 | 0 | Animation tick reload value (frames per sprite step) |
| 0x0F | anim_frame | varies | 0 | 0 | 0 | Current animation frame index (0..+0x10−1) |
| 0x10 | anim_max | varies | 0 | 0 | 0 | Max animation frames (loop point) |
| 0x11 | anim_ptr_lo | varies | 0 | 0 | 0 | Low byte of 16-bit LE pointer to animation table (sat_name/sat_color pairs) |
| 0x12 | anim_ptr_hi | varies | 0 | 0 | 0 | High byte of animation table pointer |
| 0x13 | target_y | 0 | 0 | 0 | 0 | Y-homing target coordinate (used when bit3 set) |
| 0x14 | target_x | 0 | 0 | 0 | 0 | X-homing target coordinate (used when bit4 set) |
| 0x15 | y_accel | 0 | 0 | 0 | 0 | Y-homing acceleration step per iteration |
| 0x16 | x_accel | 0 | 0 | 0 | 0 | X-homing acceleration step per iteration |
| 0x17 | homing_iters | 0x05 | 0 | rand1–4 | 0 | Homing iterations per frame (bit3/bit4); also used handler-specifically (T44: random 1–4 at spawn; T1: 5) |
| 0x18 | col_type | 0 | 0x01 | 0x2C | 0 | **Persistent (not cleared by entity_clear).** Set by collision routine (0x4560) to entity's own type bits 0–6. T39 special: despawn countdown, refreshed to **2** every frame by the parent — see below |
| 0x19 | ? | 0 | 0 | 0 | 0x04 | Persistent. T82: purpose unknown |
| 0x1A | ? | 0 | 0 | 0 | 0 | Persistent |
| 0x1B | child_ptr_lo / invinc_timer | 0x40* | fwd_lo | ptr_lo | 0 | **Persistent.** T1: invincibility timer (init 0x40, decrements/frame, color flashes until 0); T44/T39: 16-bit LE ptr to linked col-marker slot |
| 0x1C | child_ptr_hi | 0 | fwd_hi | ptr_hi | 0x01 | **Persistent.** T44 → T39 slot; T39 → next |
| 0x1D | col_width | 0 | 0 | 0x06 | 0x07 | **Persistent.** Incremented by place_tile_group |
| 0x1E | ? | 0 | 0 | 0 | 0 | Persistent |
| 0x1F | ? | 0 | 0x20 | 0 | 0 | Persistent |

*T1 +0x1B = 0x40 at spawn; decrements to 0 over ~64 frames, then clears +0x05 bit7 and restores color.

## Type 39's +0x18 is a keepalive, refreshed to 2 (corrected 2026-07-30)

The table row above used to say the parent "sets to 1". The parent's per-frame
complement-sprite push (0x71F6) ends with:

```
721A  LD DE,0x0014
721D  ADD HL,DE        ; HL was child+0x04, so this is child+0x18
721E  LD (HL),0x02     ; two, not one
7220  RET
```

The value matters because it makes this a **keepalive rather than a
one-shot**. The parent rewrites 2 on every frame it draws its complement
sprite; type 39's own handler (0x8525) decrements +0x18 each dispatch and calls
`entity_clear` when it reaches 0. So the marker survives exactly as long as its
parent keeps refreshing it, and disposes of itself two frames after the parent
stops — no explicit teardown anywhere. With 1 the marker would be racing its own
handler every frame.

## entity_update (0x4898) — behavior_flags dispatch

Decoded from ROM machine code (sprint 0021). Bit tests on IX+0x0C drive 5 conditional calls, then always does the SAT push:

| Bit | Call | Function |
|-----|------|----------|
| 3 | 0x4942 | **Y-homing**: adds/subtracts +0x15 to vy (+0x08/+0x09), toward target +0x13; runs +0x17 iterations |
| 4 | 0x496B | **X-homing**: adds/subtracts +0x16 to vx (+0x0A/+0x0B), toward target +0x14; runs +0x17 iterations |
| 0 | 0x48DE | **Y-motion**: (Y:y_frac) += (vy:vy_frac); clamp Y; if Y ≥ 208 → entity_clear (off-screen despawn) |
| 1 | 0x48F8 | **X-motion**: (X:x_frac) += (vx:vx_frac); clamp X; if X ≥ 209 → entity_clear |
| 2 | 0x4912 | **Animate**: decrement +0x0D; on 0, advance +0x0F, read sat_name/sat_color from table at +0x11:+0x12, wrap at +0x10 |
| — | always | **SAT push**: write (Y−17, X, sat_name, sat_color) to sprite buffer at 0xE122 |

**Note:** The original field description had bit0=update-X and bit1=update-Y reversed. Corrected in sprint 0021.

## entity_clear (0x48D0) — partial zero

```
PUSH IX / POP HL      ; HL = entity slot
LD (HL), 0            ; zero type_flags
LD E, L / LD D, H
LD BC, 0x17 / INC DE
LDIR                  ; propagate zero to IX+0x01..IX+0x17
RET
```

Only bytes **+0x00 through +0x17 (24 bytes)** are zeroed. Bytes **+0x18 through +0x1F are persistent** and survive despawn. They retain the previous occupant's values until overwritten by the new entity's init code or the collision routine.

## Type-specific init summary (sprint 0021)

**Type 1 (player, 0x75D5):** +0x01=0xA0, +0x02=0x78, +0x03=0x38, +0x04=0x8F, +0x0C=0x00 (manual motion), +0x05.bit7=1 (invincible), +0x17=5, +0x1B=0x40 (invincibility timer). Motion driven by keyboard, not entity_update.

**Type 2 (player shot, 0x7221):** +0x0C=0x01 (bit0: Y-motion only), vy = CPL(0xE10E). All +0x0D..+0x1F = 0. **Despawns when Y wraps ≥ 208** (off-screen), not by lifetime countdown.

**Type 39 (col-marker, 0x8525):** +0x0C=0x00, +0x18=countdown (set by parent type-44 to 1 via spawn_col_marker). On every dispatch: decrements +0x18; when 0, calls entity_clear. Does NOT call entity_post, so collision routine never sets +0x18.

**Type 44 (ground struct, 0x82D0):** spawn_col_marker (0x71DA) allocates type-39 child slot, links via +0x1B/+0x1C. +0x0C=0x03 (bit0: Y-motion, bit1: X-motion). +0x17 = R & 0x03 + 1 (random 1–4 at spawn). Running code: entity_update → 0x71F6 → entity_post.

## Entity type roles (sprint 0010)

| Type (bits 0–6) | Role | Slots |
|---|---|---|
| 1 | Player ship (always slot 0) | 0 |
| 2 | Player shot | 1–3 (see note) |
| 3 | Fire weapon projectile (all fire types) | 4 |
| 39 (0x27) | Column-occupancy marker — invisible (y=0, x=0) | 5–25 |
| 44 (0x2C) | Main ground structure with sprite | 5–25 |
| 82 (0x52) | Wide ground structure | 5–25 |

Slots 0–4 appear reserved for player and player-controlled entities (shots and fire weapon projectiles), below the ground-structure range.
Slots 5–25 are the ground-structure pool also scanned by `check_col_clear`.

## Shot slots are 1–3, not 1–4 (corrected 2026-07-30)

The type-roles table above previously gave player shots slots 1–4.
`collision_dispatch`'s shot pass (0x44F9) tests exactly three slots — 0xE320,
0xE340, 0xE360 (`CP 0x82` at 0x4500/0x450F/0x451E) — and slot 4 (0xE380) is the
fire-weapon slot, tested separately at 0x44DB (`CP 0x83`) behind the 0xE14E
bit-0 gate. A fourth shot written into slot 4 would overwrite the fire entity
and never be collision-tested as a shot. The three shot slots are consistent
with [[shot_power_table]]'s on-screen caps of 2–3.

## Motion update (confirmed, source lines 2500–2505)

Fixed-point: `(slot[1] * 256 + slot[6]) += (slot[9] * 256 + slot[8])`, then
`slot[1]` clamped to [30, 184]. Same for X (slots 2, 7, 11, 10 clamped to [40, 200]).
SAT Y = slot[1] − 17 (sprite bottom-edge encoding; see `sprite_shadow_push`).

## Analysis
Source lines 342–351 (init: `LD B, 0x20; LD HL, 0xE300`; clears 32 entries × 32
bytes), lines 493–523 (`entity_dispatch` iterates 26 slots, `IX += 0x20`).
Type-1 handler at 0x75D5 (source lines ~3544) decoded: +0x0C=0, +0x17=5, +0x1B=0x40.

`cold_start` lines 53–57 zero 0xE000–0xE7FE with LDIR; lines 342–351 then
redundantly clear 32 slots, confirming 0xE300 as array base.

**Corrected in sprint 0010**: 26 slots × 32 bytes = 832 bytes → 0xE300–0xE63F.
The sprint 0005 `end: 0xE51F` was wrong. Live debug confirmed slot 25 at 0xE620
and slot 24 at 0xE600 are active ground-structure entities.

Init clears 32 slots (0xE300–0xE6FF, 1024 bytes) but dispatch iterates exactly 26.

**Type byte semantics (sprint 0010):** bit 7 is a state flag (set when active/in-flight).
Bits 0–6 are the entity type dispatched via `ADD A,A` into the jump table at 0x70B7.
The `ADD A,A` overflow naturally masks bit 7, so types 0x01 and 0x81 dispatch identically.

**Ground structure slots (5–25):** type bytes also serve as tile-occupancy markers
scanned by `check_col_clear` (0x9B22). Types 0x27 (col-marker) and ≥0x46 (wide structure)
cause `check_col_clear` to return carry set (blocked).
