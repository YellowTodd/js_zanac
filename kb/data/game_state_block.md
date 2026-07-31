---
address: 0xE100
kind: data
name: game_state_block
confidence: confirmed
sprint: "0045"
tags: [gamestate, spawn, scroll, entity]
---

# game_state_block

## Summary

80-byte game-state block at 0xE100–0xE14F. Accessed via `IX = 0xE100` by
`ground_struct_spawn_ctrl` (0xBF2C), `scroll_velocity_ctrl` (0x9480),
`handler_type35_base_eye` (0x8446), and other main-loop routines. Distinct from
the entity table (0xE300–0xE63F) and the scroll_state block (0xE700–0xE721).

## Field layout

| Offset | Address | Name | Confidence | Notes |
|--------|---------|------|------------|-------|
| +0x00 | 0xE100 | input_state | confirmed | Joystick+keyboard bitmask overwritten every frame by `sub_4343`; bits 0–3=directions, 4=shot/fire, 5=fire-weapon. 0xBF = no buttons. **Not** a phase byte. |
| +0x02 | 0xE102 | status_flags | confirmed | Central game-state flag byte read by the main loop every frame. Bit 0 `player_hit`, bit 1 `game_over`, bit 2 scroll flag, bit 3 `end_credits`, bit 4 `display_timer`, bit 5 `level_complete`, bit 6 `respawn`, bit 7 `go_to_title`. Full map in `input-state-machine.md`. |
| +0x03 | 0xE103 | score_lo | confirmed | Score BCD low byte |
| +0x04 | 0xE104 | score_mid | confirmed | Score BCD mid byte |
| +0x05 | 0xE105 | score_hi | confirmed | Score BCD high byte |
| +0x06 | 0xE106 | topscore_lo | confirmed | Top-score BCD low byte |
| +0x07 | 0xE107 | topscore_mid | confirmed | Top-score BCD mid byte |
| +0x08 | 0xE108 | topscore_hi | confirmed | Top-score BCD high byte |
| +0x0A | 0xE10A | lives | confirmed | Lives remaining (0–3) |
| +0x0B | 0xE10B | shot_level | confirmed | Shot upgrade level (0–5) |
| +0x0C | 0xE10C | player_x_vel | confirmed | Player X velocity derived each frame from direction keys; base 4, ±3 for left/right, ±1 for up/down |
| +0x0D | 0xE10D | shot_max_simultaneous | confirmed | Max simultaneous shots on screen |
| +0x0E | 0xE10E | shot_vy_raw | confirmed | Shot Y velocity parameter |
| +0x0F | 0xE10F | shot_sat_name | confirmed | Shot sprite name (SAT pattern index) |
| +0x10 | 0xE110 | shot_state | likely | **Not the round.** Set to 1 by the shot handler at 0x7684 when the fire button (E100 bit 4) is held, else decremented; stays 0x01 across all rounds (warp r1/r3/r8). The round number lives in **`E701`** (scroll-state block) — see `round-progression.md`. |
| +0x12 | 0xE112 | sprite_limit | hypothesis | Initialized to 0x20=32 at game start (0x421B); likely max sprites written to shadow buffer per VBlank |
| +0x14 | 0xE114 | score_milestone_flags | likely | Bit 6: first score milestone passed (set at 0x4A14); bit 7: second milestone (after 64 increments past bit-6). Compared against topscore for display trigger. |
| +0x17 | 0xE117 | spawn_init_param | guess | Initialized to 0x02 at game start (0x41F5); purpose unclear |
| +0x1F | 0xE11F | sprite_buf_ptr_lo_prev | likely | Copy of E122 low byte written by entity dispatch loop end (0x4492: `LD A,(E122); LD (E11F),A`); used by vblank_isr to count sprites for OUTI loop |
| +0x22 | 0xE122 | sprite_buf_ptr_lo | likely | Low byte of 16-bit sprite shadow buffer write pointer (pair with E123); each entity writes {Y_adj,X,0x3C,0x81} and advances by 4 |
| +0x23 | 0xE123 | sprite_buf_ptr_hi | likely | High byte of sprite shadow buffer write pointer; stable at 0xE0 (buffer lives in 0xE000–0xE0FF page) |
| +0x24 | 0xE124 | ground_spawn_countdown | confirmed | Counts down from 6 (init), then from 0x10; when it reaches 0 sets spawn_trigger(E125)=1 and reloads to 0x10. Written at 0x84BF by entity handler. |
| +0x25 | 0xE125 | spawn_trigger | confirmed | Bit 0: set by stream engine to request immediate type-44 spawn; cleared by BFA4 |
| +0x26 | 0xE126 | stream_slot_ctr | confirmed | Mod-16 counter; every 16th fires type-0x3D (61) entity |
| +0x27 | 0xE127 | sprite_overflow_ctr | likely | Incremented each VBlank frame when sprite_buf_ptr_lo_prev (E11F) has bit 6 set, i.e. ≥16 sprites drawn (≥64 pointer advance) |
| +0x29 | 0xE129 | player_y_snap | confirmed | Snapshot of player Y position (entity slot 0, byte +0x01); written by `player_pos_snapshot` at 0x4C94 |
| +0x2A | 0xE12A | player_x_snap | confirmed | Snapshot of player X position (entity slot 0, byte +0x02); written by `player_pos_snapshot` at 0x4C9A |
| +0x2B | 0xE12B | prng_lo | likely | Low byte of 16-bit PRNG state; updated each call with R register + bit mixing (`LD HL,(E12B); ADD A,H; ...; LD (E12B),HL` at 0x43CE) |
| +0x2C | 0xE12C | prng_hi | likely | High byte of PRNG state (written simultaneously with E12B by `LD (E12B),HL`) |
| +0x2D | 0xE12D | spawn_ctrl | confirmed | Bit 0: call 0xBE27 (scroll-pos update); bit 1: stream active; bit 3: stream block; bit 0 also set by `base_encounter_ctrl` at 0xBFBC |
| +0x2E | 0xE12E | spawn_pos_hi | likely | High byte of 16-bit spawn-position accumulator; also incremented by type-35 base eye via `base_encounter_ctrl` |
| +0x2F | 0xE12F | spawn_pos_lo | confirmed | += 8 per entity spawned (by ground_struct_spawn_ctrl); += 16 per frame by type-35 base eye; carry propagates to spawn_pos_hi |
| +0x30 | 0xE130 | base_health_ctr | confirmed | Read by handler_type11_base_spawner to pick projectile spawn Y/X position |
| +0x31 | 0xE131 | level_seg_ctr | hypothesis | Accumulator incremented at each level-segment boundary (0x8488); simultaneously resets spawn_event_ctr(E142) to 0; wraps freely |
| +0x32 | 0xE132 | scroll_offset | hypothesis | Added to spawn_pos in 0xBE27; possibly horizontal scroll phase |
| +0x33 | 0xE133 | spawn_table_ptr | confirmed | 16-bit LE pointer into ROM level entity-type sequence (e.g. 0xBECF during gameplay) |
| +0x35 | 0xE135 | spawn_subtable_ctr | likely | Sub-table index counter; reset to 0 when it reaches spawn_subtable_max(E136) |
| +0x36 | 0xE136 | spawn_subtable_max | confirmed | Max value for spawn_subtable_ctr; loaded from table at 0xBE7C by scroll engine `SUB_ram_be27`; changes per level segment |
| +0x37 | 0xE137 | spawn_timer | confirmed | Countdown; when 0 fires entity spawn, reloaded from +0x38 |
| +0x38 | 0xE138 | spawn_timer_reload | confirmed | Reload value copied from ROM level data table at 0xBE76 |
| +0x3F | 0xE13F | alc_fire_cadence | confirmed | **ALC input.** Frames between consecutive shots: ++ every frame by the shot handler (0x7677, saturates 0xFF), **reset to 0 each shot** (0x76B9). Indexes [[shot_rate_table]] → spawn-schedule advance. Small (rapid/erratic fire) → big advance. See [[alc-adaptive-difficulty]]. |
| +0x40 | 0xE140 | alc_shots_fired | confirmed | **ALC counter.** ++ per shot spawned (0x76E8). Used `& 0x3F` vs `score_lo` as a timing gate at 0x8374 ([[handler_type61_large_descender]]). |
| +0x41 | 0xE141 | alc_fire_events | confirmed | **ALC counter.** ++ per shot/fire event (0x76BF, saturating); consumed and reset to 0 by the base path (0x8473/0x8490) where *fewer* events → bigger spawn advance. |
| +0x42 | 0xE142 | spawn_event_ctr | confirmed | Incremented per entity spawned; saturates at 0xFF. **ALC base path**: indexes [[shot_rate_table]] (E142+1) to advance `level_seg_ctr` during base encounters (0x8457), then reset to 0 (0x848D). See [[alc-adaptive-difficulty]]. |
| +0x47 | 0xE147 | fire_debounce | confirmed | Bit 0: one-frame memory for fire-button edge detection in `sub_46bc`; prevents auto-repeat on title/gameplay transitions |
| +0x49 | 0xE149 | spawn_variant_ctr | confirmed | Incremented per entity-of-type spawn; low 3 bits (& 0x07) used as variant index stored in new entity slot +0x1D; cycles 8 variants |
| +0x4B | 0xE14B | fire_type | confirmed | Current fire weapon type (0–7); read by type-3 and type-19 entity handlers |
| +0x4C | 0xE14C | fire_limit_1 | likely | Fire weapon limit display value (first counter) |
| +0x4D | 0xE14D | fire_counter | confirmed | Fire weapon usage counter |
| +0x4E | 0xE14E | fire_limit_3 | likely | Fire weapon limit display value (third counter); bit 0 checked by sub_44D4 (post-dispatch) |

## Stable unknown bytes (always 0x00 in all sampled phases)

These bytes were 0x00 across title / game_start / mid_game / base_encounter / post_base in round 5.
They are likely padding, or fields activated only by conditions not yet sampled (player death,
specific rounds, co-op, etc.).

`0xE101, 0xE109, 0xE111, 0xE113–0xE116, 0xE118–0xE11E, 0xE120–0xE121,
0xE128, 0xE139–0xE13E, 0xE143–0xE146, 0xE148, 0xE14A, 0xE14F`

(0xE140/0xE141 were previously in this list — they are the ALC counters
`alc_shots_fired` / `alc_fire_events`, 0x00 only because the idle sample never fired.)

## Related data at 0xE150+

| Address | Name | Notes |
|---------|------|-------|
| 0xE150 | base_encounter_flags | Bit 0: base active; bit 1: gates base-ctrl increment |
| 0xE151 | base_attack_count | Number of attack-list entries written by `place_tile_group` |
| 0xE152 | base_attack_count_snapshot | Value of E151 at base activation |

## Notes

- **0xE100 correction**: previously labelled "game_phase" — it is actually the
  input_state byte written every frame by `sub_4343` (0x4343). The 0xBF value
  seen at title/game is just "no buttons pressed" (all bits active-high).
- **0xE110 correction (sprint 0045)**: previously labelled "round (1–8)" — wrong.
  Live warp tests show `E110` stays `0x01` regardless of round; the round
  selector is **`E701`** (scroll-state block). See `round-progression.md`.
- **0xE102** is the game-state flag byte sequenced by the main loop; the full
  bit map and per-state input handling are in `input-state-machine.md`.
- E122:E123 is a 16-bit write pointer into the sprite shadow buffer at 0xE000–0xE0FF.
  Each entity handler that draws a sprite calls code at ~0x772F that writes
  {Y_adjusted, X, 0x3C, 0x81} and advances E122 by 4.
- E11F is a copy of E122 (low byte) taken by the entity dispatch loop (0x4492)
  after all entities are processed; the vblank ISR uses it to know how many
  sprite entries to OUTI to the VDP.
- The PRNG at E12B:E12C uses the Z80 R register (incremented each instruction
  fetch) for entropy; called frequently making it effectively random.
- `spawn_pos_hi/lo` (0xE12E/0xE12F) serve dual purpose: ground_struct_spawn_ctrl
  updates them per-entity-spawn; handler_type35_base_eye also updates them per
  frame (driving the base health HUD display via `base_encounter_ctrl`).
- The spawn table pointer at 0xE133 points into ROM or decompressed RAM at
  addresses like 0xBECF. The table format is: one entity type byte per slot,
  terminated by 0x00.
- The block likely continues beyond +0x4F (sprite shadow buffer described
  elsewhere starts at 0xE180).
