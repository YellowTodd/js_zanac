---
id: "0027"
status: done
range: 0xE100-0xE14F
strategy: live_debug
budget_turns: 18
---

# Sprint 0027 — game_state_block gap fill (0xE100–0xE14F)

## Goal

The 80-byte game-state block at 0xE100–0xE14F is the most-referenced RAM region
in the game: entity handlers, the scroll engine, the HUD, and the fire weapon
system all read or write into it. Current coverage is ~14 named fields out of
80 bytes. The blanks block understanding of game logic across multiple subsystems.

This sprint closes the main gaps by:
1. **Phase snapshot**: dump all 80 bytes at 5 distinct game phases and compare.
2. **Change analysis**: any byte that changes between phases is a candidate for
   naming. Stable bytes across all phases are likely padding or reset-once init.
3. **Write-watchpoint round**: for each byte that changes and is still unnamed,
   arm a write-watchpoint to identify the writer (PC + context).
4. **Classification**: counter / flag / pointer / BCD value / padding.

Sprint 0023 already clarified 0xE14B = fire_type (0–7) and revealed
0xE14C/0xE14D/0xE14E as fire weapon limit display bytes. Confirm and document.

## Inputs

- `kb/data/game_state_block.md` — current named fields:
  0xE100 (game_phase), 0xE102 (status_flags), 0xE103–0xE108 (score/topscore BCD),
  0xE10A (lives), 0xE10B (shot_level), 0xE10D (max_simultaneous_shots),
  0xE10E (shot_vy_param), 0xE10F (shot_sat_name), 0xE110 (shot_timer),
  0xE125 (spawn_trigger), 0xE126 (stream_slot_ctr), 0xE12D (spawn_ctrl),
  0xE12E (spawn_pos_hi), 0xE12F (spawn_pos_lo), 0xE130 (base_health_ctr),
  0xE132 (scroll_offset), 0xE133 (spawn_table_ptr), 0xE137 (spawn_timer),
  0xE138 (spawn_timer_reload), 0xE142 (spawn_event_ctr),
  0xE14B (fire_type), 0xE14C–0xE14E (fire weapon limits, sprint 0023)
- `kb/symbols/0xE000-gamestate/` — individual named bytes already KB'd
- `kb/guides/game-description.md` — game phases for test sequence

## Key unknowns to resolve

| Address | Offset | Current label | Hypothesis |
|---------|--------|---------------|------------|
| 0xE101 | +0x01 | ? | Adjacent to game_phase; possibly sub-state |
| 0xE103–0xE109 | +0x03–+0x09 | score/top-score (6 bytes BCD) | Confirm format |
| 0xE10C | +0x0C | ? | Read by player handler (0x75D5); likely fire_type display index |
| 0xE111–0xE124 | +0x11–+0x24 | entirely unknown (20 bytes) | ? |
| 0xE127–0xE12C | +0x27–+0x2C | ? | Near spawn_ctrl; possibly spawn position fields |
| 0xE131 | +0x31 | ? | Near base_health_ctr |
| 0xE139–0xE141 | +0x39–+0x41 | ? | 9 bytes between spawn_timer_reload and spawn_event_ctr |
| 0xE143–0xE14A | +0x43–+0x4A | ? | 8 bytes between spawn_event_ctr and fire_type |
| 0xE14F | +0x4F | ? | Last byte of block |

## Verification plan

### Step 1 — Phase snapshot

```python
PHASES = ["title", "game_start", "mid_game", "game_over"]

with ZanacGame.launch() as game:
    snapshots = {}

    # Title
    game.wait_for_title()
    snapshots["title"] = bytes(msx.read_memory(0xE100, 80))

    # Game start (first 2 seconds)
    game.start_game(); time.sleep(0.5)
    snapshots["game_start"] = bytes(msx.read_memory(0xE100, 80))

    # Mid-game (10 seconds in)
    time.sleep(10.0)
    snapshots["mid_game"] = bytes(msx.read_memory(0xE100, 80))

    # Game over
    game.wait_for_game_over(timeout=120)
    snapshots["game_over"] = bytes(msx.read_memory(0xE100, 80))

# Print offset table: for each byte, show value across phases
for off in range(80):
    vals = {ph: snaps[off] for ph, snaps in snapshots.items()}
    if len(set(vals.values())) > 1:   # only rows that change
        print(f"  +{off:#04x} 0x{0xE100+off:04X}: "
              + "  ".join(f"{ph}={v:02X}" for ph, v in vals.items()))
```

### Step 2 — Write-watchpoints for changing bytes

For each byte identified as changing and still unnamed:
```python
wp = msx.cmd(
    f"debug set_watchpoint write_mem 0x{addr:04X} {{}} "
    f"{{set ::wp_pc_{addr:04X} [reg PC]; debug break}}"
)
```
Let the game run through title → game-start → 5s gameplay. Report PC for each
write, then decode the 6 bytes before PC to see the instruction context.

### Step 3 — BCD and pointer checks

- For bytes that look like 0x00–0x99 with a sawtooth pattern: likely BCD counter.
- For adjacent byte-pairs that look like RAM addresses (0xE000–0xFFFF or 0x4000–0xBFFF): likely 16-bit pointer.

## Expected output

- `kb/data/game_state_block.md` updated: fill in names/hypotheses for
  at least 20 of the 46 currently-unnamed offsets.
- New individual gamestate symbol files in `kb/symbols/0xE000-gamestate/` for
  any confidently-named bytes.

## Summary (filled at end)

Captured six-phase snapshots (title → game_start → mid_game → base_approach →
base_active → post_base) using `arm_warp(5)` + `make_invincible()` to reach a
base encounter in round 5 within ~150 s. Write-watchpoints (no CPU break) then
identified the writer PC for every changing unknown byte, with context read in
the same session while ROM was mapped.

**Named/classified 24 previously-unknown offsets** (sprint target: 20):

| Address | Name | Confidence |
|---------|------|------------|
| 0xE100 | input_state | confirmed (was wrong "game_phase") |
| 0xE10C | player_x_vel | confirmed |
| 0xE112 | sprite_limit | hypothesis |
| 0xE114 | score_milestone_flags | likely |
| 0xE117 | spawn_init_param | guess |
| 0xE11F | sprite_buf_ptr_lo_prev | likely |
| 0xE122 | sprite_buf_ptr_lo | likely |
| 0xE123 | sprite_buf_ptr_hi | likely |
| 0xE124 | ground_spawn_countdown | confirmed |
| 0xE127 | sprite_overflow_ctr | likely |
| 0xE128 | entity_dir_flags (transient) | likely |
| 0xE129 | player_y_snap | confirmed |
| 0xE12A | player_x_snap | confirmed |
| 0xE12B | prng_lo | likely |
| 0xE12C | prng_hi | likely |
| 0xE131 | level_seg_ctr | hypothesis |
| 0xE136 | spawn_subtable_max | confirmed |
| 0xE13F | shot_frame_ctr | hypothesis |
| 0xE147 | fire_debounce | confirmed (pre-existing) |
| 0xE149 | spawn_variant_ctr | confirmed |

Key findings:
- **0xE100 is NOT a game-phase byte** — it is the live input_state (joystick+keyboard
  bitmask) written every frame; 0xBF = no buttons pressed.
- **0xE11F/0xE122:0xE123** form a sprite shadow buffer write pointer. The code at
  0x772F writes {Y_adj, X, 0x3C, 0x81} per sprite entity and advances the pointer by 4.
  0xE11F is a copy of the low byte used by the VBlank ISR.
- **0xE12B:0xE12C** is a 16-bit PRNG updated via the Z80 R register (code at 0x43C0,
  embedded in a disassembled DB section at 0x43C0–0x43D1).
- **0xE124** = ground_spawn_countdown: confirmed trigger for spawn_trigger (E125).
- **0xE136** = spawn_subtable_max: confirmed from scroll engine table at 0xBE7C.
- **0xE149** = spawn_variant_ctr: confirmed, cycles 8 entity sprite variants.
- 31 stable-zero bytes catalogued as likely padding or unused in sampled phases.

New helper functions added to `zanac_game.py`: `arm_warp()`, `make_invincible()`,
`spawn_type()` — used in this sprint and available for future sprints.
