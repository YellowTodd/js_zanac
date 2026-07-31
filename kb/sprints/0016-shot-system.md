---
id: "0016"
status: done
range: 0x778F-0x77A0
strategy: forward_from_caller
budget_turns: 20
---

# Sprint 0016 — Player shot system

## Goal

Map the player shot system: identify how each shot level (0–5) determines the
sprite pattern, velocity, and simultaneous-shot count for type-2 entities.
Trace the param-load routine that translates `shot_level` (0xE10B) into the
live values used by the type-2 handler.

## Inputs

- `kb/features/entity-sprite-mapping.md` — type 2 confirmed as player shot
- `kb/data/entity_jump_table.md` — type 2 handler 0x7221
- source/zanac.asm lines 2741–2757 (type-2 handler init)
- source/zanac.asm lines 3340–3357 (param-load routine)
- source/zanac.asm lines 3524–3542 (power chip pickup / level cap)

## Verification plan

- Static: table at 0x778F decoded directly from ROM via openMSX memory read.
- Static: cap code confirms max level = 5 (`INC A; CP 0x06; JR C`).
- Live: `capture_bullet_slots` in `tools/sprint0016_debug.py` intended for
  live weapon-level confirmation (title screen timing prevented in-session
  live capture; static analysis complete).

## Summary

### Shot param table (0x778F — 6 entries × 3 bytes)

| Level | vy_raw | Max shots | SAT_NAME | Sprite | Description |
|-------|--------|-----------|----------|--------|-------------|
| 0 | 0x04 | 2 | 0x28 | shot_single (pat10) | single, slow |
| 1 | 0x06 | 3 | 0x28 | shot_single (pat10) | single fast (3 simultaneous) |
| 2 | 0x08 | 2 | 0x2C | shot_double (pat11) | double |
| 3 | 0x09 | 3 | 0x2C | shot_double (pat11) | double fast (3 simultaneous) |
| 4 | 0x0A | 2 | 0x30 | shot_triple (pat12) | triple |
| 5 | 0x0E | 3 | 0x30 | shot_triple (pat12) | triple fast (3 simultaneous) |

Table ends at 0x77A0; address 0x77A1 is the start of the type-68 handler (`CALL 0x43C0`).

### Velocity encoding

The type-2 handler stores `CPL(vy_raw)` into IX+0x09 (Y velocity integer). With
IX+0x08 = 0 (no Y fraction), the shot moves upward at `~vy_raw` pixels/frame
(negative = upward in the coordinate system):

| Level | vy_raw | ~vy_raw | Upward speed |
|-------|--------|---------|--------------|
| 0 | 0x04 | 0xFB | 5 px/frame |
| 1 | 0x06 | 0xF9 | 7 px/frame |
| 2 | 0x08 | 0xF7 | 9 px/frame |
| 3 | 0x09 | 0xF6 | 10 px/frame |
| 4 | 0x0A | 0xF5 | 11 px/frame |
| 5 | 0x0E | 0xF1 | 15 px/frame |

### Max-simultaneous-shots mechanism

`max_simultaneous` (0xE10D, value 2 or 3) is used by the shot-spawn routine at
~0x76C9: it scans entity slots 1–B (where B = 0xE10D) for the first inactive
slot (type=0). If found, initialises type=2 at that slot. If all B slots are
occupied the spawn is skipped.

### Power chip pickup and level upgrade

Handler (type-56-ish entity) at ~0x78E7 increments 0xE10B. When level would
exceed 5 (`CP 0x06; JR NC`), instead increments over-cap counter 0xE14F. After
5 over-cap chips, passes `fire_type` (0xE14B) to `0x7548` (fire weapon upgrader).

### New / updated KB files

- `kb/symbols/0xE000-gamestate/level.md` → renamed `shot_level`, full level table
- `kb/symbols/0xE000-gamestate/fire_num.md` → renamed `fire_type` (0-7)
- `kb/data/entity_jump_table.md` — type 2 role corrected; type 3 role confirmed
- `kb/features/entity-sprite-mapping.md` — stale notes removed; terminology fixed
- `kb/data/player_bullet_table.md` → renamed `player_projectile_table`; marked
  needs-investigation with 5-slot cap interpretation
- Several files: "bullet" → "shot"/"projectile" terminology sweep

### Still uncertain

- 0xE10A: read by `update_status_bar` immediately after 0xE10B; likely related
  to fire weapon display but not yet confirmed.
- `player_projectile_table` at 0xE20C: 5-slot 27-byte structure; relationship
  to entity dispatch slots 1–4 not resolved.
- Live confirmation of all 6 shot levels not completed (title screen timing
  issue during session; static ROM data confirmed).

### Next sprint candidates

- **0017 — Spawn table source**: what writes 0xE133 to advance the level sequence.
- **0018 — Fire weapon projectile system**: trace type-3 handler at 0x7253; map
  fire weapon types 1–7 to their entity types, sprites, and behavior.
