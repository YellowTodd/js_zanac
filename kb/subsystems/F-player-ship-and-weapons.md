---
letter: F
title: Player Ship & Weapons
coverage: done
status: done
---

# F — Player Ship & Weapons

## Role

The player-controlled ship and its two weapon systems: the normal `shot`
(levels 0–5, upgraded by power chips) and the `fire` weapon (types 0–7, each
with distinct behaviour and ammo/time/durability limits). Covers ship movement,
shot spawning, fire-weapon selection/limits, and the player-hit/death path.
Input arrives via [[read_player_input]] / [[K-game-flow-state-machine]]; weapons
spawn entities through [[C-entity-framework]]; ammo/limits are shown by
[[N-hud-and-status-display]] via the F-owned [[update_fire_display]].

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x4343 | [[read_player_input]] | confirmed | poll joystick+keyboard → E100, X-vel selector E10C |
| 0x46BC | `fire_edge_detect` | confirmed | rising-edge of fire keys |
| 0x4649 | `player_hit_handler` | confirmed | ship-destroyed path (lives/respawn/game-over) |
| 0x46A8 | `wait_fire_or_timeout` | confirmed | run N frames / early-out on fire |
| 0x4C8B | `player_pos_snapshot` | confirmed | snapshot player X/Y for collision |
| 0x4CF7 | [[set_velocity_from_dir]] | confirmed | dir(0-15)+speed → IX velocity, via [[vel_dir_table]] |
| 0x5C2E | [[dispatch_inline_table]] | confirmed | inline word-table computed jump (fire dispatch) |
| 0x7221 | [[shot_handler]] | confirmed | normal-shot entity (type 2): sprite/SFX/upward velocity |
| 0x7253 | [[fire_weapon_handler]] | confirmed | fire entity (type 3): init/update dispatch on fire_num |
| 0x730B | [[fire_life_timer]] | confirmed | E14C/E14D countdown → expiry to fire_reset |
| 0x732A | [[fire_dec_ammo]] | confirmed | dec E14D + redraw |
| 0x7544 | [[fire_reset]] | confirmed | reset weapon to 0 → fire_select |
| 0x7548 | [[fire_select]] | confirmed | switch weapon; load [[fire_init_table]] |
| 0x7594 | [[update_fire_display]] | confirmed | FIRE label + num + ammo to VRAM 0x3a59/0x3a7a |
| 0x75D5 | [[player_ship_handler]] | confirmed | ship entity (slot 0) spawn/respawn |
| 0x7612 | [[player_ship_update]] | confirmed | per-frame move / shoot / fire / sprite write |
| 0x7771 | [[load_shot_params]] | confirmed | shot_level → E10E/E10D/E10F via [[shot_power_table]] |

## Data

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x4D65 | [[vel_dir_table]] | confirmed | 16 unit-velocity vectors (mag 128) |
| 0x7269/727F/74AE | [[fire-weapon-dispatch]] | confirmed | 3-phase × 8-weapon dispatch tables |
| 0x7321 | [[fire0_dir_table]] | likely | fire-0 spread directions |
| 0x751F | [[fire_init_table]] | confirmed | fire_num → E14D/E14E |
| 0x752F | [[fire2_special_table]] | likely | fire-2 per-level/late-round params |
| 0x7758 | [[xvel_table]] | confirmed | E10C selector → ship dir index |
| 0x7761 | [[shot_rate_table]] | confirmed | auto-fire cadence |
| 0x778F | [[shot_power_table]] | confirmed | shot_level → vy/cap/sprite |

`dir8_delta_table` (0x7748, 8 signed-word deltas) is decoded + labelled in source
but currently **unreferenced** by any code path — left as data, not wired in.

## State

| Addr | Name | Notes |
|------|------|-------|
| 0xE100 | input byte | active-low joystick∧keyboard merge |
| 0xE10B | `shot_level` | shot power (0–5), index into shot_power_table |
| 0xE10C | `player_x_vel` | horizontal selector (0–8; 4 = centre) |
| 0xE10D | `shot_max_simultaneous` | on-screen shot cap |
| 0xE10E | `shot_vy_raw` | shot vertical speed |
| 0xE10F | `shot_sat_name` | shot sprite pattern |
| 0xE110 | shot cooldown | reload 0x14 frames |
| 0xE13F | fire-held counter | indexes shot_rate_table |
| 0xE14B | `fire_num` | active fire weapon 0–7 |
| 0xE14C | fire frame counter | 0x3c reload (fire_life_timer) |
| 0xE14D | `fire_counter` | remaining ammo/time/durability |
| 0xE14E | fire mode | per-weapon secondary count |
| 0xE380 | fire-control slot | type-3 fire entity control byte |

## Gaps / open questions

- The eight fire weapons' **individual gameplay identities** (which is the
  field / shield / wave / homing weapon) are not named — the dispatch and each
  handler's address/structure are confirmed ([[fire-weapon-dispatch]]), but the
  per-weapon flavour is described from code, not matched to manual names.
- `dir8_delta_table` (0x7748) has no caller found.

## Sprints

Done: 0016 (shot system), 0023 (fire weapon system), **0048 (subsystem F
completion — fire engine, ship handler, velocity setter, tables; all confirmed)**.
0048 also closes the 0x730B item from **0038**.
