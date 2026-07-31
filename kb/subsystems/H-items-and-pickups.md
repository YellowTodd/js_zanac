---
letter: H
title: Items & Pickups
coverage: done
status: done
---

# H — Items & Pickups

## Role

The collectible economy: shootable floating **boxes** (drop nothing / three
bullets / a power chip), **power chips** that raise the normal-shot level (0→5),
and the floating **fire-weapon upgrades** dropped by special ground constructions
that switch the `fire` weapon (0–7). Items are ordinary entities — they ride the
[[C-entity-framework]] dispatch/collision/motion machinery and are spawned by
[[G-enemy-and-spawn-system]]; their effects land in
[[F-player-ship-and-weapons]]. There is no separate "item subsystem" in code —
H is the *semantic* slice across those handlers.

## The box → drop pipeline

```
proto_box (type 68) ── proto_box_type_table[round/rng] ──▶ 3 boxes of type 4/5/6
        │                                                          │
        │ box floats (handler_type4_box), countdown reveals tile   │ shot enough times
        ▼                                                          ▼
   collision saves box type → +0x18         death branch (0x7878) reads +0x18:
                                              4 → three bullets (3× type 38)
                                              5 → nothing
                                              6 → power chip (type 63)
```

- **Drop is fixed by box type**, chosen at spawn by [[proto_box_type_table]]
  (values 4/5/6, RNG/round-indexed) — so that table *is* the drop-odds table.
- [[handler_type4_box]] (types 4–6) — box float/reveal/hit + the drop branch.
- [[handler_type68_proto_box]] (type 68) — spawns the 3-box cluster.

## Power chip

- [[handler_type63_power_chip]] (type 63, 0x78af) — floats; on player contact:
  `shot_level` (E10B) += 1 (cap 6) → [[load_shot_params]] → HUD; also briefly
  flags the player slot and bumps the encounter/pickup counter E130 (via 0xbfc8).
  When already maxed it runs a bonus counter (E148/E14F) that restarts the
  current fire weapon every 5th chip.
- Shot-level → params lives in [[shot_power_table]] (levels 0–5).

## Fire-weapon upgrade

- [[handler_type83_black_shadow]] (type 83) — a floating ground construction;
  destroying it calls [[fire_select]] (0x7548) with `A = +0x1c`, switching the
  player's fire weapon to that number (0–7). `+0x1c` is set at spawn and doubles
  as the construction's colour index. Collecting the *same* number restarts that
  weapon's limit; a *different* number switches weapon (see
  [[F-player-ship-and-weapons]] / fire engine).
- Picking up Fire 2 (Field Shutter) is the documented ALC bump
  ([[I-alc-adaptive-difficulty]]).

## State

`shot_level` (E10B), `shot_max_simultaneous`/`shot_vy_raw`/`shot_sat_name`
(E10D/E/F), `fire_num` (E14B), pickup/encounter counter (E130, E148, E14F).

## Verification

`tools/sprint0054_verify.py` — 7/7 micro-exec checks: jump-table[63]=0x78AF; box
drop for +0x18 ∈ {4,5,6} → {type 38, unchanged, type 63}; power-chip apply
(shot_level 3→4 + params reload); black-shadow death → `fire_select(+0x1c)`.

## Sprints

Done: 0054 (item economy: box drop table, power chip, fire-weapon grant —
all live-confirmed).

## Gaps / open questions

- The exact meaning of the maxed-chip bonus counters E148/E14F (score vs extend
  vs difficulty) is not separated out; E130 increments on pickup and feeds the
  base-encounter/difficulty readout.
