---
address: 0x8f5e
end: 0x8f99
kind: routine
name: base_tick
confidence: confirmed
inputs:  { IX: "0xE100 (game_state_block)" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x5211, 0x5189, 0x516c, 0x93e4, 0x909c, 0x9ae4, 0x8a26, 0x9393, 0x4a74, 0x49b5, 0xbfab, 0xbfb3, 0xbfbf, 0xbfc8, 0x4c74, 0x4163]
called_by: [0x4077, 0x40ac]
tags: [base, boss, gamestate, scroll]
sprint: "port"
---

# base_tick

*(the disassembly labels it `SUB_ram_8f5e`. The `end` above covers only the
entry body; the phases it branches to are spread over 0x8FA3-0x9402, in and
around [[scroll_speed_ramp_table]], [[base_clear_award_index_table]],
[[gameplay_frame_loop]] and [[ending_setup]], which have their own entries.)*

The **base (boss) encounter driver**, called every frame from the main loop
(0x4077 and 0x40AC). `IX = 0xE100`, so every `(IX+0x5n)` in the listing is
`0xE15n`. It is a four-phase state machine over `0xE150`:

| 0xE150 | phase | what runs |
|--------|-------|-----------|
| bit 0 | **approach** | 0xE156 counts down; each step caps the scroll speed lower through [[scroll_speed_ramp_table]], and 0 stops the scroll and opens the base |
| bit 1 | **active** | the "TIME" countdown at (0xE154) runs, 0xE152 tracks living segments, and reaching 0 clears the base |
| bit 2 | **closing** | after a time-out the segments retreat; the encounter ends when they are all gone |
| bit 3 | enrage | set once 0xE152 drops to 0xE153; [[handler_type73_base_segment]] reads it at 0x8B02 to advance with the scroll |
| 0 | idle | — |

**This is the scroll stall players see at a base.** Two separate mechanisms:
the approach ramp writes 0xE710 (current speed) down to 0, and
[[scroll_velocity_ctrl]] then refuses to run its ramp at all while
`(0xE150) & 3` is non-zero (0x9491), so the speed stays at 0 until the
encounter is over.

## Setup: map command 0xB (0x9742)

Four script bytes land in 0xE155..0xE158, `(0xE154) = 0` starts the countdown
at "0xE155 : 00" (BCD, 0x59 wraps a unit), and 0xE153 comes from
`cmd11_index_table` (0x976C) indexed by `(0xE157) & 0x1F`.

| byte | addr | role |
|------|------|------|
| 0 | 0xE155 | countdown units (BCD); also seeds 0xE159 |
| 1 | 0xE156 | approach steps (9..1 decelerate, 0 opens) |
| 2 | 0xE157 | **scenario**: low 5 bits index the award/ending tables, bit4 disables the timer, bit5 selects the alternate fanfare + BGM stop, bit6 suppresses the BONUS text, bit7 suppresses the flash |
| 3 | 0xE158 | options: bit0 gates the 0xE12D release, bit1 suppresses the 0xE12D block + 0xE159 seed |

Round 1 (script index 7 @0xA751) fires this **five** times, at rows 300, 1000,
2120, 2500 and 2950.

## Placement: `place_tile_group` bit 7 (0x95F8)

A tile-group descriptor with **bit 7** turns the batch into a base: 0x95FC
resets the attack-list cursor (0xE71E) to 0xE780 and zeroes 0xE151, each placed
entity appends its pointer to that list (0x9626, 4-byte records) and bumps
0xE151, and the batch end (0x9665) copies the count into 0xE152 and sets
`(0xE150) = 1`.

The 0xE780 records are 4 bytes because the **same table** carries the segment's
VRAM address in bytes 2-3 — [[handler_type73_base_segment]] writes it at 0x8AA6
via `0xE782 + (IX+0x1C)*4`.

## Opening (0x8FA3)

`0xE710 = 0` (stop), 0xE15A = 0x00C0 (the intro delay before alarm event 0x19),
`0xE150 = 2`, and then 0x8FDE hands each of the 0xE151 segments the next of the
eight [[base_attack_patterns]] pointers round-robin (cursor in 0xE717), zeroes
its rate accumulator (+0x0E) and numbers it in +0x1C. Unless bit 4 of the
scenario is set it also prints "TIME" at VRAM 0x3AB9.

## Clearing (0x90A6) — the victory ceremony

Blocking; it drives `gameplay_frame_loop` (0x9393) directly:

1. ALC discount: `0xE12E -= 0xE12E>>2`, `0xE132 -= 8` (floored), `dec_encounter_a`, release 0xE12D bit 3, `0xE150 = 0`
2. leftover structure types 0x52/0x54-0x56 become explosions (0x50)
3. **two passes** of: backdrop to white (WRTVDP 7,0x0F), 3 frames, rewrite the base's tiles in the 0xE800 ring into rubble (pass 1 folds 0xA0.. to 0xE7 with 0xA7-0xAA lifted to 0xE3-0xE6; pass 2 folds 0xE3-0xE7 down to the 0x3A-0x3E crater tiles), then `explode_enemies` and 4 more frames
4. fanfare event 0x1A or 0x1B by scenario bit 5 (skipped entirely for scenarios 0x10/0x11)
5. "BONUS" at VRAM 0x3966, the award index from [[base_clear_award_index_table]] rendered and `add_score`d
6. scenario ≥ 0x10 raises 0xE102 bit 2; scenario **0x0F** sets `0xE722 = 0xB7A5` + 0xE102 bit 5 (a warp); above 0x10 goes to `ending_setup`

## Timing out (0x9325)

The clock reaching 0 is *not* a loss: release 0xE12D bit3, `dec_encounter_b`,
`0xE12E += 0x10`, `inc_encounter_a`, erase the "TIME" text, `0xE150 = 0x0E`.
The closing sweep (0x934D) then waits for every segment to reach phase 3, drops
to 0x0C, and waits for them to vanish before returning to 0.

## Related

[[handler_type73_base_segment]] (the parts), [[base_segment_table]] (0x8DF1),
[[base_attack_patterns]] (0x93AB), [[base_clear_award_index_table]] (0x9302),
[[scroll_velocity_ctrl]] (the stall), [[level_script_format]] (command 0xB).
