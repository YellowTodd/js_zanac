---
address: 0x7761
end: 0x7770
kind: data
name: shot_rate_table
confidence: confirmed
sprint: "0048"
tags: [alc, difficulty, spawn, shot-rate-table, table]
---

# shot_rate_table

## Summary

**This is the ALC (adaptive-difficulty) spawn-advance table, not auto-fire
spacing.** 16-byte table mapping a *firing-cadence* counter to a *spawn-schedule
advance amount*. Read by two paths:

- [[player_ship_update]] 0x76a1, indexed by **E13F − 2** (fire cadence; frames
  between shots).
- [[handler_type35_projectile]] 0x8466, indexed by **E142 + 1** (spawn-event count)
  during base encounters.

The looked-up value is **added to `spawn_pos` (E12F) and `level_seg_ctr` (E131)** —
it advances the enemy spawn schedule, it does **not** set shot timing. (Shot
spacing is the fixed 20-frame E110 period.) Small index (rapid/erratic fire) →
large advance (0x20) → many more enemies; large index (steady fire) → +1. Full
mechanism: [[alc-adaptive-difficulty]].

## Layout

```
0x7761: 20 10 0a 08 06 05 04 04 03 03 02 02 02 02 02 02
```

The callers clamp the index: `player_ship_update` uses a fixed 1 when E13F ≥ 0x12
(0x7694 `CP 0x12; JR C`); `handler_type35` uses 1 when E142 ≥ 0x11 (0x845A).

## Confirmed (sprint 0055)

Deterministic micro-exec of the player path (0x7691–0x76b9): controlled E13F →
advance applied to E12F/E131 matched the table exactly across E13F = 2,3,4,8,0x11,
0x12,0x20 (7/7). `tools/alc_confirm.py`. (Originally reached live in 0048 as the
held-fire path, but mislabelled "auto-fire spacing".)
